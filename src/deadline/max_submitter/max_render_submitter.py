# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Create UI
"""

import logging
import os
from os.path import abspath, join, normpath
from pathlib import Path
from typing import Any, Optional

import pymxs  # noqa
import qtmax
import yaml
from create_job_bundle import (
    get_job_template,
    get_parameters_values,
)
from data_classes import BatchRenderView, RenderSubmitterUISettings, StateSetData, SubmissionMode
from data_const import (
    ALL_STATE_SETS_STR,
    ALL_STEREO_CAMERAS_STR,
    TEMP_BACKUP_FILENAME,
    UI_GROUP_LABEL,
)
from deadline.client.config import get_setting, str2bool
from deadline.client.dataclasses import SubmitterInfo
from deadline.client.exceptions import DeadlineOperationCanceled, DeadlineOperationError
from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.ui.dialogs._types import JobBundlePurpose
from deadline.client.ui.pre_gui_hooks import (
    PreGuiHookContext,
    apply_pre_gui_output,
    qt_hook_confirmation,
    run_pre_gui_hooks,
)
from pymxs import runtime as rt
from qtpy.QtCore import Qt  # type: ignore
from qtpy.QtWidgets import QMessageBox  # type: ignore
from sanity_checks import check_sanity
from ui.scene_settings_tab import SceneSettingsWidget
from ui.submit_dialog import SubmitMaxJobToDeadlineDialog
from utilities import max_utils, submission_utils
from deadline.max_shared.utilities.max_utils import (
    get_batch_render_views,
    get_max_version_year,
    get_render_elements_output_directories,
)

from _version import version
from _version import version_tuple as adaptor_version_tuple

_logger = logging.getLogger(__name__)


def on_create_job_bundle_callback(
    widget: SubmitMaxJobToDeadlineDialog,
    job_bundle_dir: str,
    settings: RenderSubmitterUISettings,
    queue_parameters: list[dict[str, Any]],
    asset_references: AssetReferences,
    output_directories: set[str],
    host_requirements: Optional[dict[str, Any]] = None,
    purpose: JobBundlePurpose = JobBundlePurpose.SUBMISSION,
) -> None:
    """
    Function that collects all data from the UI and creates a job bundle from that data.

    :param widget: the 3dsMax Submitter dialog
    :param job_bundle_dir: the directory where the job bundle needs to be saved
    :param settings: a RenderSubmitterUISettings object containing the latest UI settings
    :param queue_parameters: the settings from the shared job settings tab
    :param asset_references: an AssetReferences object containing the filepaths from the job attachments tab
    :param host_requirements: a list of OpenJD parameter definition dicts with values filled from the widget
    :param purpose: a value indicating which button was pressed.
        JobBundlePurpose.EXPORT when 'Export Bundle' was pressed
        JobBundlePurpose.SUBMISSION when 'Submit' was pressed
    """
    # Run all sanity checks
    warnings = check_sanity(settings)

    # Show confirmation dialog if there are non-blocking warnings
    if warnings:
        warning_text = "\n".join(f"• {w}" for w in warnings)
        result = QMessageBox.warning(
            widget,
            "Submission Warnings",
            f"The following warnings were found:\n\n{warning_text}\n\n"
            "Do you want to continue anyway?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            raise Exception("Submission cancelled by user.")

    _logger.debug("Start on_create_job_bundle_callback")
    settings.backup_file = rt.execute("GetDir #temp") + "\\" + TEMP_BACKUP_FILENAME
    _logger.debug(f"backup file: {settings.backup_file}")

    # Load default template
    with open(Path(__file__).parent / "default_max_job_template.yaml") as fh:
        default_job_template = yaml.safe_load(fh)

    # Reset in case Max remembered these settings
    submission_utils.backup_saved = False
    submission_utils.clear_mat = False
    submission_utils.unlock_mat = False
    submission_utils.custom_mat = False

    state_sets_to_submit: list[StateSetData] = []

    if settings.submission_mode == SubmissionMode.DEFAULT.value:
        # DEFAULT mode: build StateSetData from the selected state sets
        state_sets = max_utils.get_state_set_names()
        # if all state sets were chosen for submission, make a StateSetData object for each state set
        if settings.state_set == ALL_STATE_SETS_STR:
            for state_set in state_sets:
                # Set the current state set
                rt.execute(
                    f"stateSetsDotNetObject = dotNetObject "
                    f'"Autodesk.Max.StateSets.Plugin" \n'
                    f"stateSets = stateSetsDotNetObject.Instance \n"
                    f"masterState = stateSets.EntityManager.RootEntity."
                    f"MasterStateSet \n"
                    f"needState = masterState.Children.Item[{state_set[1]}] \n"
                    f"masterState.CurrentState = #(needState)"
                )
                output_dir = settings.output_path
                output_file_name = settings.output_filename_pattern
                output_file_format = settings.output_ext
                image_resolution = (rt.renderWidth, rt.renderHeight)

                state_sets_to_submit.append(
                    StateSetData(
                        state_set=state_set[0],
                        renderer=str(rt.renderers.current).split(":")[0],
                        frame_range=max_utils.get_frames(),
                        output_directories=output_directories,
                        output_file_dir=output_dir,
                        output_file_name=output_file_name,
                        output_file_format=output_file_format,
                        image_resolution=image_resolution,
                        ui_group_label=state_set[0] + " Settings",
                    )
                )
        # Otherwise only create it for the selected state set
        else:
            need_state = settings.state_set_index
            # Set the current state set
            rt.execute(
                f"stateSetsDotNetObject = dotNetObject "
                f'"Autodesk.Max.StateSets.Plugin" \n'
                f"stateSets = stateSetsDotNetObject.Instance \n"
                f"masterState = stateSets.EntityManager.RootEntity."
                f"MasterStateSet \n"
                f"needState = masterState.Children.Item[{need_state}]\n"
                f"masterState.CurrentState = #(needState)"
            )
            output_dir = settings.output_path
            output_file_name = settings.output_filename_pattern
            output_file_format = settings.output_ext
            image_resolution = (rt.renderWidth, rt.renderHeight)

            state_sets_to_submit.append(
                StateSetData(
                    state_set=settings.state_set,
                    renderer=str(rt.renderers.current).split(":")[0],
                    frame_range=max_utils.get_frames(),
                    output_directories=output_directories,
                    output_file_dir=output_dir,
                    output_file_name=output_file_name,
                    output_file_format=output_file_format,
                    image_resolution=image_resolution,
                    ui_group_label=UI_GROUP_LABEL,
                )
            )

        # Use override from UI if the checkbox is checked
        if settings.override_frame_range:
            for state_set in state_sets_to_submit:
                state_set.frame_range = settings.frame_list

        # Add render element output directories to output_directories set
        if settings.render_elements and not settings.ignore_render_elements_by_name:
            try:
                render_element_dirs = get_render_elements_output_directories()
                output_directories.update(render_element_dirs)
                _logger.debug(f"Added render element output directories: {render_element_dirs}")

                # Update state sets with render element directories
                for state_set in state_sets_to_submit:
                    state_set.output_directories.update(render_element_dirs)

            except Exception as e:
                _logger.warning(f"Failed to get render element output directories: {e}")

    # BATCH_RENDER mode: no state sets needed — job bundle functions read scene
    # defaults directly from the pymxs API and submitter UI settings

    # Only do these actions when we want to submit a scene
    if purpose == JobBundlePurpose.SUBMISSION:
        # Make a backup of the current state of the scene
        if os.path.exists(settings.backup_file):
            os.remove(settings.backup_file)
        submission_utils.save_max_backup_file(settings.backup_file, True)
        _logger.debug("Saving backup")
        submission_utils.backup_saved = True
        submission_utils.backup_file = settings.backup_file

        # Make files absolute before submission
        submission_utils.make_paths_absolute()

        # Go over all the 'scene tweaks' check boxes
        if settings.merge_xref_obj or settings.merge_xref_scn:
            asset_references = submission_utils.merge_xrefs(settings, asset_references)

        if settings.clear_mat:
            submission_utils.cleared_materials = submission_utils.clear_material_editor()
            submission_utils.clear_mat = True

        if settings.unlock_mat:
            submission_utils.unlock_material_editor_renderer()
            submission_utils.unlock_mat = True

        if settings.custom_mat_chck:
            submission_utils.overridden_materials = submission_utils.apply_custom_material(
                settings.custom_mat
            )
            submission_utils.custom_mat = True

        # Save the scene so that absolute paths and any scene tweaks applied become sticky.
        # When the ui closes after submission the scene gets reverted back to the original state
        submission_utils.save_scene()

    job_bundle_path = Path(job_bundle_dir)

    # Decide what 'all cameras' is based on the camera selection in the ui
    cameras_in_scene = settings.all_cameras
    if settings.camera_selection == ALL_STEREO_CAMERAS_STR:
        cameras_in_scene = settings.all_stereo_cameras

    job_template = get_job_template(
        default_job_template, settings, state_sets_to_submit, cameras_in_scene
    )

    parameter_values = get_parameters_values(settings, state_sets_to_submit, queue_parameters)

    # Collect preset files from batch render views if batch render mode is selected
    if (
        settings.submission_mode == SubmissionMode.BATCH_RENDER.value
        and settings.batch_render.enabled_views
    ):
        all_batch_views = get_batch_render_views()
        # Filter to only enabled items
        enabled_batch_views = [item for item in all_batch_views if item.enabled]

        # Collect preset files and add them to asset references
        preset_files = _collect_batch_render_attachments(enabled_batch_views)
        if preset_files:
            _logger.info(f"Adding {len(preset_files)} preset file(s) to job attachments")
            # Add preset files to input filenames in asset_references
            for preset_file in preset_files:
                asset_references.input_filenames.add(preset_file)

    # If "HostRequirements" is provided, inject it into each of the "Step"
    if host_requirements:
        # for each step in the template, append the same host requirements.
        for step in job_template["steps"]:
            step["hostRequirements"] = host_requirements

    # write template, parameter_values and asset_references file
    with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(job_template, f, indent=1)

    with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump({"parameterValues": parameter_values}, f, indent=1)
    with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

    attachments: AssetReferences = widget.job_attachments.attachments
    settings.input_filenames = sorted(attachments.input_filenames)
    settings.input_directories = sorted(attachments.input_directories)
    settings.input_filenames = sorted(attachments.input_filenames)

    # Save sticky settings
    settings.save_sticky_settings()


def _pre_gui_hook_confirm_callback(parent):
    """Choose the confirmation callback for pre-GUI hooks based on the auto_accept setting.

    Returns ``None`` (run hooks without prompting) when ``settings.auto_accept`` is enabled,
    otherwise the standard Qt confirmation dialog from ``qt_hook_confirmation``. Kept as a small
    helper so the auto_accept branch can be unit-tested headlessly.
    """
    if str2bool(get_setting("settings.auto_accept")):
        return None
    return qt_hook_confirmation(parent)


def show_job_bundle_submitter():
    """
    Main function that shows the UI.
    """
    _logger.info("Opening Deadline Cloud 3dsMax Submitter interface")
    # Get main max window
    main_window = qtmax.GetQMaxMainWindow()

    render_settings = RenderSubmitterUISettings()

    # Set settings dependent on scene. Capture the scene name in a local before
    # load_sticky_settings() (below) can overwrite render_settings.name with a previously persisted
    # value: pre-GUI hooks receive this pre-sticky scene name as job_name (see the hook block), so a
    # read-modify-write hook (e.g. a "STUDIO_" + jobName prefix) stays idempotent across runs instead
    # of compounding through the sticky settings file.
    scene_name = max_utils.get_scene_name()
    render_settings.name = scene_name
    render_settings.frame_list = max_utils.get_frames()
    render_settings.project_path = max_utils.get_scene_path()

    # set output settings from renderer
    output_path, output_name, output_ext = max_utils.get_render_output_info()
    render_settings.output_path = output_path
    render_settings.output_name = output_name
    # Build default pattern from render settings
    render_settings.output_filename_pattern = f"<camera>_<stateset>_{output_name}"
    if output_ext:
        render_settings.output_ext = output_ext

    render_settings.backup_file = rt.execute("GetDir #temp") + "\\" + TEMP_BACKUP_FILENAME
    render_settings.renderer = str(rt.renderers.current).split(":")[0]

    render_settings.load_sticky_settings()

    # Compute the shared parameter values the dialog is seeded with. These are also handed to the
    # pre-GUI hooks below (as the PreGuiHookContext parameters), so build them before the hook runs.
    max_version = get_max_version_year()
    adaptor_version = ".".join(str(v) for v in adaptor_version_tuple[:2])
    conda_packages = f"3dsmax={max_version}.* 3dsmax-openjd={adaptor_version}.*"

    shared_parameter_values = {
        "CondaPackages": conda_packages,
    }

    # Run pre-GUI hooks so studios can pre-populate dialog fields before it opens. 3ds Max has no
    # on-disk job bundle at this point, so hooks are sourced from DEADLINE_HOOKS_DIR only
    # (bundle_dir=None), gated by settings.allow_environment_hooks. The confirmation prompt is
    # skipped when auto_accept is set; otherwise the standard dialog is shown.
    #
    # This runs BEFORE the state-set discovery loop and asset scanning below. That loop sets the
    # scene's active state set (masterState.CurrentState) as it walks each state set, mutating the
    # scene; running the hooks first means declining the confirmation prompt or a hook failure
    # aborts (return None) without having touched the scene, and the prompt also appears promptly
    # instead of after all the scanning work.
    hook_deadline_params_applied = False
    try:
        # Build the confirmation callback (reads settings.auto_accept), run the hooks, and apply
        # their output, all inside this try so hook failures are handled by the except clauses below
        # instead of escaping as a raw traceback (3ds Max opens the submitter without a surrounding
        # gui_error_handler).
        confirm_callback = _pre_gui_hook_confirm_callback(main_window)
        pre_gui_output = run_pre_gui_hooks(
            PreGuiHookContext(
                bundle_dir=None,
                # Pre-sticky scene name (not render_settings.name, which load_sticky_settings may
                # have replaced with a prior hook's output) so read-modify-write hooks stay
                # idempotent and don't compound through the sticky settings file.
                job_name=scene_name,
                submitter_name=render_settings.submitter_name,
                priority=render_settings.priority,
                parameters=dict(shared_parameter_values),
            ),
            confirm_callback=confirm_callback,
        )
        # deadline-cloud's generic helper maps the merged output onto our settings + shared values.
        # RenderSubmitterUISettings has no .parameters list, so every hook parameter (CondaPackages,
        # deadline: job properties, etc.) flows into shared_parameter_values, which seeds the dialog.
        # Guard with `or {}` defensively: run_pre_gui_hooks returns {} when no hooks run, but this
        # keeps the call safe if a future release returns None instead.
        apply_pre_gui_output(pre_gui_output or {}, render_settings, shared_parameter_values)
        # Track only whether hook deadline: parameters were applied. The dialog's shared-settings
        # widget replays only deadline: keys synchronously during construction (via
        # set_parameter_value in SharedJobSettingsWidget.__init__), so those are the sole hook output
        # that can make SubmitMaxJobToDeadlineDialog(...) raise below, and thus the only thing the
        # construction guard should arm on. name/description land on the type-validated
        # RenderSubmitterUISettings dataclass, and non-deadline: queue parameters are applied
        # asynchronously (see the construction-guard comment) — neither can fail construction here.
        hook_deadline_params_applied = any(
            name.startswith("deadline:")
            for name in ((pre_gui_output or {}).get("parameters") or {})
        )
    except DeadlineOperationCanceled:
        # The user declined the hook confirmation prompt — a normal cancellation, not a failure — so
        # abort opening the submitter silently. Mirrors the check_and_show_update_dialog() early
        # return. (DeadlineOperationCanceled subclasses DeadlineOperationError, so this handler must
        # come first.)
        return None
    except DeadlineOperationError:
        # A pre-GUI hook failed: non-zero exit, timeout, invalid JSON, or disallowed output —
        # deadline-cloud raises DeadlineOperationError for all of these. Its documented contract is
        # that a failing pre-GUI hook *blocks* the dialog, so surface a clear error and abort rather
        # than opening with un-applied values (which would silently bypass any pipeline policy the
        # hook enforces). Only DeadlineOperationError is caught, so genuine local bugs still surface
        # as tracebacks instead of being mistaken for hook failures.
        _logger.exception("A pre-GUI submission hook failed; the submitter will not open.")
        QMessageBox.critical(
            main_window,
            "AWS Deadline Cloud",
            "A pre-GUI submission hook failed, so the submitter was not opened. "
            "See the 3ds Max scripting listener/log for details.",
        )
        return None

    output_directories: set[str] = set()

    # Add output dir from state set settings if one is set. NOTE: this loop sets
    # masterState.CurrentState for each state set to read its output path, changing the scene's
    # active state set; the submitter dialog re-applies a state set when it opens, so the visible
    # end state is dialog-driven. The pre-GUI hook block above deliberately runs before this so its
    # abort paths don't leave the scene mutated with no dialog open.
    state_sets = max_utils.get_state_set_names()
    for state_set in state_sets:
        rt.execute(
            f"stateSetsDotNetObject = dotNetObject "
            f'"Autodesk.Max.StateSets.Plugin" \n'
            f"stateSets = stateSetsDotNetObject.Instance \n"
            f"masterState = stateSets.EntityManager.RootEntity."
            f"MasterStateSet \n"
            f"needState = masterState.Children.Item[{state_set[1]}] \n"
            f"masterState.CurrentState = #(needState)"
        )
        if rt.rendOutputFilename:
            output_dir, _, _ = max_utils.get_render_output_info()
            output_directories.update([output_dir])
    output_directories.update([render_settings.output_path])

    # Add render element output directories if render elements are enabled
    try:
        render_element_dirs = get_render_elements_output_directories()
        if render_element_dirs:
            output_directories.update(render_element_dirs)
            _logger.debug(
                f"Added render element output directories to initial setup: {render_element_dirs}"
            )
    except Exception as e:
        _logger.debug(f"Could not get render element output directories during initialization: {e}")

    render_settings.output_directories = output_directories

    # Fill in the auto-detected input files
    auto_detected_attachments = AssetReferences()
    relative_dir_base = rt.maxFilePath
    input_files: set[str] = {
        abspath(normpath(join(relative_dir_base, path)))
        for path in max_utils.get_referenced_files()
    }
    auto_detected_attachments.input_filenames = input_files

    attachments = AssetReferences(
        input_filenames=set(render_settings.input_filenames),
        input_directories=set(render_settings.input_directories),
        output_directories=set(render_settings.output_directories),
    )

    submitter_info = SubmitterInfo(
        submitter_name="3dsMax",
        submitter_package_name="deadline-cloud-for-3ds-max",
        submitter_package_version=version,
        host_application_name="3ds Max",
        host_application_version=str(max_version),
    )

    # Instantiate and show the Submitter UI. A pre-GUI hook can inject a deadline: parameter the
    # shared-settings widget doesn't accept (an unknown key, or a value of the wrong type). Only
    # deadline: keys are replayed synchronously here, during construction (SharedJobSettingsWidget
    # replays them via set_parameter_value in __init__), so that is the failure this guard catches:
    # per the block-on-failure contract, treat it as a hook failure and abort with a clear error
    # rather than a raw traceback, but only when the hook actually supplied a deadline: parameter. A
    # construction failure with no hook deadline: parameter applied is a genuine submitter bug and
    # is left to propagate as a traceback.
    #
    # Non-deadline: (queue) parameters such as CondaPackages are NOT replayed here — the widget
    # applies them asynchronously once the queue's parameter definitions have loaded, after this
    # try/except has returned. So this guard cannot catch them: a bad queue-parameter *value*
    # surfaces later in the Qt event loop, and a queue-parameter *name* the target queue doesn't
    # define is silently dropped. Validating those against the loaded queue parameters belongs in
    # deadline-cloud's shared widget, not here.
    try:
        window = SubmitMaxJobToDeadlineDialog(
            job_setup_widget_type=SceneSettingsWidget,
            initial_job_settings=render_settings,
            initial_shared_parameter_values=shared_parameter_values,
            auto_detected_attachments=auto_detected_attachments,
            attachments=attachments,
            on_create_job_bundle_callback=on_create_job_bundle_callback,
            parent=main_window,
            f=Qt.Tool,
            show_host_requirements_tab=True,
            submitter_info=submitter_info,
        )
    except Exception:
        if not hook_deadline_params_applied:
            raise
        _logger.exception(
            "A pre-GUI hook supplied a value the submitter could not use; the submitter will not open."
        )
        QMessageBox.critical(
            main_window,
            "AWS Deadline Cloud",
            "A pre-GUI submission hook supplied a value the submitter could not use, so the "
            "submitter was not opened. See the 3ds Max scripting listener/log for details.",
        )
        return None
    window.show()
    return window


def _collect_batch_render_attachments(batch_views: list[BatchRenderView]) -> list[str]:
    """
    Collect preset files from batch render views as job attachments.

    Queries batch render views for preset files, validates they exist,
    deduplicates them, and returns a list of absolute paths to include
    in the job bundle.

    :param batch_views: list of BatchRenderView instances from get_batch_render_views()
    :return: list of absolute paths to preset files that should be attached to the job
    """
    preset_files: set[str] = set()

    for item in batch_views:
        preset_file = item.preset_file

        # Skip if no preset file is specified
        if not preset_file:
            continue

        # Convert to absolute path if relative
        if not os.path.isabs(preset_file):
            # Resolve relative to scene file directory
            scene_dir = max_utils.get_scene_path()
            if scene_dir:
                scene_dir = os.path.dirname(scene_dir)
                preset_file = os.path.abspath(os.path.join(scene_dir, preset_file))
            else:
                # If no scene file, try to resolve relative to current directory
                preset_file = os.path.abspath(preset_file)

        # Validate preset file exists
        if not os.path.exists(preset_file):
            _logger.warning(
                f"Preset file '{preset_file}' referenced by batch item '{item.name}' "
                f"does not exist and will not be included in job bundle"
            )
            continue

        # Validate it's a file (not a directory)
        if not os.path.isfile(preset_file):
            _logger.warning(
                f"Preset path '{preset_file}' referenced by batch item '{item.name}' "
                f"is not a file and will not be included in job bundle"
            )
            continue

        # Add to set (automatically deduplicates)
        preset_files.add(preset_file)
        _logger.debug(f"Added preset file to attachments: {preset_file}")

    # Convert set to sorted list for consistent ordering
    return sorted(list(preset_files))
