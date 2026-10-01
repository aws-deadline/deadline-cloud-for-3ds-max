# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for the 3ds Max submitter's pre-GUI hook integration.

``show_job_bundle_submitter`` calls deadline-cloud's ``run_pre_gui_hooks`` (env-only, since
3ds Max has no on-disk bundle) and then delegates the mapping to deadline-cloud's generic
``apply_pre_gui_output``. The full submitter needs a running 3ds Max, so it is exercised in the
integration suite; here we verify the DCC-owned pieces headless:

* ``apply_pre_gui_output`` routes hook output correctly against 3ds Max's own
  ``RenderSubmitterUISettings`` — which has no ``.parameters`` list, so every hook parameter must
  land in the shared parameter values. This guards against a regression where
  ``RenderSubmitterUISettings`` gains a ``parameters`` attribute that would misroute hook params.
* ``_pre_gui_hook_confirm_callback`` honours the ``settings.auto_accept`` setting.
* Declining the hook confirmation (``DeadlineOperationCanceled``) aborts the open silently
  rather than surfacing an uncaught traceback.
* A failing pre-GUI hook (``DeadlineOperationError``) blocks the submitter with a clear error
  dialog rather than opening with un-applied values; hook-supplied values that only fail when the
  dialog is built block the same way; and genuine local bugs (other exceptions) still propagate.

The pymxs / Qt modules are stubbed by ``test/unit/conftest.py`` so imports resolve.
"""

import sys
from typing import Optional
from unittest.mock import patch

import pytest

from deadline.client.exceptions import DeadlineOperationCanceled, DeadlineOperationError
from deadline.client.ui.pre_gui_hooks import apply_pre_gui_output
from deadline.max_submitter import max_render_submitter
from deadline.max_submitter.data_classes import RenderSubmitterUISettings


def _settings() -> RenderSubmitterUISettings:
    s = RenderSubmitterUISettings()
    s.name = "Original"
    s.description = ""
    return s


def test_settings_has_no_parameters_list():
    """The DCC contract apply_pre_gui_output depends on: RenderSubmitterUISettings exposes no
    ``.parameters`` list, so hook parameters are treated as shared values, not template params."""
    assert getattr(RenderSubmitterUISettings(), "parameters", None) is None


def test_name_and_description_applied_to_settings():
    """A hook's name/description overwrite the settings fields (3ds Max has no .parameters list,
    so these land directly on the dataclass)."""
    settings = _settings()
    shared = {"CondaPackages": "3dsmax=2026.* 3dsmax-openjd=0.1.*"}

    apply_pre_gui_output({"name": "PREGUI RAN", "description": "from pipeline"}, settings, shared)

    assert settings.name == "PREGUI RAN"
    assert settings.description == "from pipeline"


def test_hook_parameters_merged_into_shared_values():
    """With no template-parameter list, every hook parameter (queue params, deadline: properties)
    is merged into the shared values the dialog is seeded with, overriding defaults on collision."""
    settings = _settings()
    shared = {"CondaPackages": "3dsmax=2026.* 3dsmax-openjd=0.1.*"}

    apply_pre_gui_output(
        {
            "parameters": {
                "deadline:priority": 88,
                "CondaPackages": "3dsmax=2026.* custom_pkg",  # overrides the default
            }
        },
        settings,
        shared,
    )

    assert shared["deadline:priority"] == 88
    assert shared["CondaPackages"] == "3dsmax=2026.* custom_pkg"


def test_empty_output_is_a_noop():
    """No pre-GUI hook output leaves the settings and shared values unchanged."""
    settings = _settings()
    shared = {"CondaPackages": "pkg"}

    apply_pre_gui_output({}, settings, shared)

    assert settings.name == "Original"
    assert settings.description == ""
    assert shared == {"CondaPackages": "pkg"}


def test_partial_output_only_touches_present_keys():
    """Only the keys present in the output are applied; others keep their prior values."""
    settings = _settings()
    settings.description = "keep me"
    shared: dict = {}

    apply_pre_gui_output({"name": "NewName"}, settings, shared)

    assert settings.name == "NewName"
    assert settings.description == "keep me"  # not overwritten
    assert shared == {}  # no parameters in output


@patch.object(max_render_submitter, "get_setting", return_value="true")
def test_confirm_callback_none_when_auto_accept_enabled(mock_get_setting):
    """With settings.auto_accept enabled, hooks run without a confirmation prompt."""
    assert max_render_submitter._pre_gui_hook_confirm_callback(parent=None) is None
    mock_get_setting.assert_called_once_with("settings.auto_accept")


@patch.object(sys.modules["qtpy.QtWidgets"], "QMessageBox")
@patch.object(max_render_submitter, "get_setting", return_value="false")
def test_confirmation_dialog_fires_when_auto_accept_disabled(mock_get_setting, mock_msgbox):
    """With settings.auto_accept disabled, invoking the returned callback actually shows the
    confirmation dialog (QMessageBox.question), parented to the passed-in window.

    This exercises the real ``qt_hook_confirmation`` callback rather than mocking it out, so it
    verifies the prompt fires — not merely that a non-None callback was selected. ``run_pre_gui_hooks``
    invokes ``confirm_callback(sources)`` with the hook sources; an empty list is enough to reach
    the dialog. The user's answer is mapped from the QMessageBox reply.
    """
    mock_msgbox.question.return_value = mock_msgbox.Yes

    callback = max_render_submitter._pre_gui_hook_confirm_callback(parent="mainwin")
    assert callback is not None

    result = callback([])  # no hook sources needed to reach the dialog

    assert mock_msgbox.question.call_count == 1
    # The dialog is parented to the window passed into the submitter.
    assert mock_msgbox.question.call_args[0][0] == "mainwin"
    # "Yes" reply → proceed.
    assert result is True


def test_falsy_output_is_a_noop():
    """The submitter passes ``pre_gui_output or {}`` into apply_pre_gui_output, so the values
    run_pre_gui_hooks can actually produce for the no-hooks path — ``{}`` today, or ``None`` if
    the contract ever changed — must both be safe no-ops that leave settings/shared untouched."""
    falsy_values: list[Optional[dict]] = [{}, None]
    for falsy in falsy_values:
        settings = _settings()
        shared = {"CondaPackages": "3dsmax=2026.* 3dsmax-openjd=0.1.*"}

        # Mirror the submitter call site: `pre_gui_output or {}`.
        apply_pre_gui_output(falsy or {}, settings, shared)

        assert settings.name == "Original"
        assert settings.description == ""
        assert shared == {"CondaPackages": "3dsmax=2026.* 3dsmax-openjd=0.1.*"}


@patch.object(max_render_submitter, "SubmitMaxJobToDeadlineDialog")
@patch.object(max_render_submitter, "run_pre_gui_hooks")
@patch.object(max_render_submitter, "_pre_gui_hook_confirm_callback", return_value=None)
@patch.object(max_render_submitter, "get_render_elements_output_directories", return_value=set())
@patch.object(max_render_submitter, "rt")
@patch.object(max_render_submitter, "qtmax")
@patch.object(max_render_submitter, "max_utils")
def test_declining_hook_confirmation_aborts_without_error(
    mock_max_utils,
    mock_qtmax,
    mock_rt,
    mock_render_elements,
    mock_confirm_cb,
    mock_run_hooks,
    mock_dialog,
):
    """Declining the hook prompt (DeadlineOperationCanceled) returns None and never builds the
    dialog. 3ds Max opens the submitter without a surrounding gui_error_handler, so an uncaught
    cancellation would otherwise propagate as a raw traceback."""
    # Scene-setup helpers must return plausible/unpackable values so execution reaches the hook.
    mock_max_utils.get_render_output_info.return_value = ("/out", "name", ".jpg")
    mock_max_utils.get_scene_name.return_value = "scene"
    mock_max_utils.get_frames.return_value = "1-10"
    mock_max_utils.get_scene_path.return_value = "/scene.max"
    mock_max_utils.get_state_set_names.return_value = []
    mock_max_utils.get_referenced_files.return_value = []
    mock_rt.execute.return_value = "C:/tmp"
    mock_rt.maxVersion.return_value = [26000]
    mock_rt.renderers.current = "Arnold:Arnold"
    mock_rt.maxFilePath = "/scene/"
    # The user clicks "No" on the confirmation prompt.
    mock_run_hooks.side_effect = DeadlineOperationCanceled("user declined")

    result = max_render_submitter.show_job_bundle_submitter()

    assert result is None
    mock_run_hooks.assert_called_once()
    mock_dialog.assert_not_called()  # dialog must not be built on cancellation
    # Hooks run before the state-set discovery loop, which mutates the scene's active state set. On
    # cancellation we must abort before that loop so a declined submission never touches the scene.
    mock_max_utils.get_state_set_names.assert_not_called()


def _scene_mocks(mock_max_utils, mock_rt):
    """Make the scene-setup helpers return plausible/unpackable values so execution reaches the
    pre-GUI hook block."""
    mock_max_utils.get_render_output_info.return_value = ("/out", "name", ".jpg")
    mock_max_utils.get_scene_name.return_value = "scene"
    mock_max_utils.get_frames.return_value = "1-10"
    mock_max_utils.get_scene_path.return_value = "/scene.max"
    mock_max_utils.get_state_set_names.return_value = []
    mock_max_utils.get_referenced_files.return_value = []
    mock_rt.execute.return_value = "C:/tmp"
    mock_rt.maxVersion.return_value = [26000]
    mock_rt.renderers.current = "Arnold:Arnold"
    mock_rt.maxFilePath = "/scene/"


@patch.object(max_render_submitter, "QMessageBox")
@patch.object(max_render_submitter, "apply_pre_gui_output")
@patch.object(max_render_submitter, "SubmitMaxJobToDeadlineDialog")
@patch.object(max_render_submitter, "run_pre_gui_hooks")
@patch.object(max_render_submitter, "_pre_gui_hook_confirm_callback", return_value=None)
@patch.object(max_render_submitter, "get_render_elements_output_directories", return_value=set())
@patch.object(max_render_submitter, "rt")
@patch.object(max_render_submitter, "qtmax")
@patch.object(max_render_submitter, "max_utils")
def test_hook_failure_blocks_submitter(
    mock_max_utils,
    mock_qtmax,
    mock_rt,
    mock_render_elements,
    mock_confirm_cb,
    mock_run_hooks,
    mock_dialog,
    mock_apply,
    mock_msgbox,
):
    """A failing pre-GUI hook (``DeadlineOperationError`` — non-zero exit, timeout, invalid JSON,
    disallowed output) blocks the submitter: a clear error dialog is shown, the function returns
    ``None``, and the submitter dialog is never built (matching deadline-cloud's block-on-failure
    contract), rather than opening with un-applied values."""
    _scene_mocks(mock_max_utils, mock_rt)
    mock_run_hooks.side_effect = DeadlineOperationError("pre-GUI hook exited with code 1")

    result = max_render_submitter.show_job_bundle_submitter()

    assert result is None
    mock_run_hooks.assert_called_once()
    mock_apply.assert_not_called()  # output never applied when the hook failed
    mock_dialog.assert_not_called()  # submitter is not opened
    mock_msgbox.critical.assert_called_once()  # user is told, not just the log
    # Hooks run before the state-set discovery loop that mutates the scene's active state set, so a
    # hook failure blocks before that loop and never touches the scene.
    mock_max_utils.get_state_set_names.assert_not_called()


@patch.object(max_render_submitter, "QMessageBox")
@patch.object(max_render_submitter, "apply_pre_gui_output")
@patch.object(max_render_submitter, "SubmitMaxJobToDeadlineDialog")
@patch.object(max_render_submitter, "run_pre_gui_hooks")
@patch.object(max_render_submitter, "_pre_gui_hook_confirm_callback", return_value=None)
@patch.object(max_render_submitter, "get_render_elements_output_directories", return_value=set())
@patch.object(max_render_submitter, "rt")
@patch.object(max_render_submitter, "qtmax")
@patch.object(max_render_submitter, "max_utils")
def test_unexpected_hook_error_propagates(
    mock_max_utils,
    mock_qtmax,
    mock_rt,
    mock_render_elements,
    mock_confirm_cb,
    mock_run_hooks,
    mock_dialog,
    mock_apply,
    mock_msgbox,
):
    """Only ``DeadlineOperationError`` is treated as a hook failure. A different exception is a
    genuine local bug and must propagate (surface as a traceback) rather than be silently converted
    into a "hook failed" dialog — so real defects stay visible."""
    _scene_mocks(mock_max_utils, mock_rt)
    mock_run_hooks.side_effect = RuntimeError("genuine bug, not a hook failure")

    with pytest.raises(RuntimeError):
        max_render_submitter.show_job_bundle_submitter()

    mock_dialog.assert_not_called()
    mock_msgbox.critical.assert_not_called()


@patch.object(max_render_submitter, "QMessageBox")
@patch.object(max_render_submitter, "apply_pre_gui_output")
@patch.object(
    max_render_submitter, "SubmitMaxJobToDeadlineDialog", side_effect=KeyError("deadline:prioriy")
)
@patch.object(
    max_render_submitter,
    "run_pre_gui_hooks",
    return_value={"parameters": {"deadline:priority": "not-an-int"}},
)
@patch.object(max_render_submitter, "_pre_gui_hook_confirm_callback", return_value=None)
@patch.object(max_render_submitter, "get_render_elements_output_directories", return_value=set())
@patch.object(max_render_submitter, "rt")
@patch.object(max_render_submitter, "qtmax")
@patch.object(max_render_submitter, "max_utils")
def test_bad_hook_params_block_at_dialog_construction(
    mock_max_utils,
    mock_qtmax,
    mock_rt,
    mock_render_elements,
    mock_confirm_cb,
    mock_run_hooks,
    mock_dialog,
    mock_apply,
    mock_msgbox,
):
    """A hook can inject a deadline: *parameter* (unknown key, or wrong value type) that only fails
    when the shared-settings widget replays it during dialog construction — after the hook
    try/except. When hook parameters were applied, that construction failure blocks cleanly (error
    dialog + ``None``) instead of escaping as a raw traceback. The hook output here carries a
    ``parameters`` map (not just name/description), because only parameters are replayed through the
    widget and can arm the construction guard."""
    _scene_mocks(mock_max_utils, mock_rt)

    result = max_render_submitter.show_job_bundle_submitter()

    assert result is None
    mock_dialog.assert_called_once()  # construction was attempted...
    mock_msgbox.critical.assert_called_once()  # ...failed, and the user was told


@patch.object(max_render_submitter, "QMessageBox")
@patch.object(max_render_submitter, "apply_pre_gui_output")
@patch.object(
    max_render_submitter, "SubmitMaxJobToDeadlineDialog", side_effect=AttributeError("widget bug")
)
@patch.object(max_render_submitter, "run_pre_gui_hooks", return_value={"name": "SHOT_010"})
@patch.object(max_render_submitter, "_pre_gui_hook_confirm_callback", return_value=None)
@patch.object(max_render_submitter, "get_render_elements_output_directories", return_value=set())
@patch.object(max_render_submitter, "rt")
@patch.object(max_render_submitter, "qtmax")
@patch.object(max_render_submitter, "max_utils")
def test_name_only_hook_output_does_not_mask_construction_bug(
    mock_max_utils,
    mock_qtmax,
    mock_rt,
    mock_render_elements,
    mock_confirm_cb,
    mock_run_hooks,
    mock_dialog,
    mock_apply,
    mock_msgbox,
):
    """The construction guard arms only when hook *deadline:* parameters were applied. A hook that
    returns only ``{"name": "SHOT_010"}`` (the canonical job-name-prefix hook, no parameters) must
    NOT arm it: name/description land on the settings dataclass and are already type-validated, so
    they cannot break dialog construction. An unrelated construction failure (e.g. an
    ``AttributeError`` regression in the widget) must therefore still propagate as a traceback
    rather than be masked as "a pre-GUI hook supplied a bad value" — otherwise submitter bugs would
    be misattributed to the studio's hook in every studio whose hook always returns a name."""
    _scene_mocks(mock_max_utils, mock_rt)

    with pytest.raises(AttributeError):
        max_render_submitter.show_job_bundle_submitter()

    mock_dialog.assert_called_once()
    mock_msgbox.critical.assert_not_called()  # not masked as a hook failure


@patch.object(max_render_submitter, "QMessageBox")
@patch.object(max_render_submitter, "apply_pre_gui_output")
@patch.object(
    max_render_submitter, "SubmitMaxJobToDeadlineDialog", side_effect=RuntimeError("widget bug")
)
@patch.object(
    max_render_submitter,
    "run_pre_gui_hooks",
    return_value={"parameters": {"CondaPackages": "3dsmax=2026.* custom_pkg"}},
)
@patch.object(max_render_submitter, "_pre_gui_hook_confirm_callback", return_value=None)
@patch.object(max_render_submitter, "get_render_elements_output_directories", return_value=set())
@patch.object(max_render_submitter, "rt")
@patch.object(max_render_submitter, "qtmax")
@patch.object(max_render_submitter, "max_utils")
def test_queue_only_hook_params_do_not_mask_construction_bug(
    mock_max_utils,
    mock_qtmax,
    mock_rt,
    mock_render_elements,
    mock_confirm_cb,
    mock_run_hooks,
    mock_dialog,
    mock_apply,
    mock_msgbox,
):
    """Only ``deadline:`` parameters arm the construction guard, because only they are replayed
    synchronously during ``SubmitMaxJobToDeadlineDialog`` construction. A hook that supplies only a
    non-``deadline:`` queue parameter (e.g. ``CondaPackages``) cannot break construction: those are
    applied asynchronously by the shared-settings widget after the queue's parameter definitions
    load, well after construction returns. So a construction failure here is a genuine submitter bug
    and must propagate as a traceback, not be masked as a hook failure."""
    _scene_mocks(mock_max_utils, mock_rt)

    with pytest.raises(RuntimeError):
        max_render_submitter.show_job_bundle_submitter()

    mock_dialog.assert_called_once()
    mock_msgbox.critical.assert_not_called()  # queue-only params don't arm the guard


@patch.object(max_render_submitter, "QMessageBox")
@patch.object(max_render_submitter, "apply_pre_gui_output")
@patch.object(
    max_render_submitter, "SubmitMaxJobToDeadlineDialog", side_effect=RuntimeError("dialog bug")
)
@patch.object(max_render_submitter, "run_pre_gui_hooks", return_value={})
@patch.object(max_render_submitter, "_pre_gui_hook_confirm_callback", return_value=None)
@patch.object(max_render_submitter, "get_render_elements_output_directories", return_value=set())
@patch.object(max_render_submitter, "rt")
@patch.object(max_render_submitter, "qtmax")
@patch.object(max_render_submitter, "max_utils")
def test_dialog_construction_bug_propagates_without_hook_output(
    mock_max_utils,
    mock_qtmax,
    mock_rt,
    mock_render_elements,
    mock_confirm_cb,
    mock_run_hooks,
    mock_dialog,
    mock_apply,
    mock_msgbox,
):
    """When no hook output was applied, a dialog-construction failure is a genuine bug and must
    propagate — the hook-attribution guard must not mask it as a "hook supplied a bad value" block.
    """
    _scene_mocks(mock_max_utils, mock_rt)

    with pytest.raises(RuntimeError):
        max_render_submitter.show_job_bundle_submitter()

    mock_msgbox.critical.assert_not_called()


@patch.object(max_render_submitter, "SubmitMaxJobToDeadlineDialog")
@patch.object(max_render_submitter, "run_pre_gui_hooks", return_value={})
@patch.object(max_render_submitter, "_pre_gui_hook_confirm_callback", return_value=None)
@patch.object(max_render_submitter, "get_render_elements_output_directories", return_value=set())
@patch.object(max_render_submitter, "rt")
@patch.object(max_render_submitter, "qtmax")
@patch.object(max_render_submitter, "max_utils")
def test_hook_receives_pre_sticky_scene_name(
    mock_max_utils,
    mock_qtmax,
    mock_rt,
    mock_render_elements,
    mock_confirm_cb,
    mock_run_hooks,
    mock_dialog,
):
    """Pre-GUI hooks receive the pre-sticky *scene* name as ``job_name``, not the sticky
    ``render_settings.name`` that ``load_sticky_settings`` may have replaced with a prior hook's
    output. Guards the sticky-settings feedback loop: a read-modify-write hook (e.g. a
    ``"STUDIO_" + jobName`` prefix) must stay idempotent across runs instead of compounding
    (``STUDIO_myscene`` -> ``STUDIO_STUDIO_myscene`` -> ...) through the persisted sticky file."""
    mock_max_utils.get_render_output_info.return_value = ("/out", "name", ".jpg")
    mock_max_utils.get_scene_name.return_value = "myscene"
    mock_max_utils.get_frames.return_value = "1-10"
    mock_max_utils.get_scene_path.return_value = "/scene.max"
    mock_max_utils.get_state_set_names.return_value = []
    mock_max_utils.get_referenced_files.return_value = []
    mock_rt.execute.return_value = "C:/tmp"
    mock_rt.maxVersion.return_value = [26000]
    mock_rt.renderers.current = "Arnold:Arnold"
    mock_rt.maxFilePath = "/scene/"

    # Simulate a prior run's hook output persisted to the sticky file: load_sticky_settings
    # overwrites render_settings.name with the previously prefixed value.
    def _sticky(self):
        self.name = "STUDIO_myscene"

    with patch.object(
        RenderSubmitterUISettings, "load_sticky_settings", autospec=True, side_effect=_sticky
    ):
        max_render_submitter.show_job_bundle_submitter()

    ctx = mock_run_hooks.call_args.args[0]
    # Pre-sticky scene name, not the persisted "STUDIO_myscene".
    assert ctx.job_name == "myscene"
