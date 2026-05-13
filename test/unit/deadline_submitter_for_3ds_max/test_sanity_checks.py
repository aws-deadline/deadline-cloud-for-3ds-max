# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import logging
import random
import string

from unittest.mock import patch, Mock
from pytest import fixture, raises

from deadline.max_shared.utilities.max_utils import BatchRenderView
from deadline.max_submitter.sanity_checks import (
    check_sanity,
    check_sanity_batch_render,
    check_sanity_specific_state_set,
    JOB_PARAMETER_MAX_STRING_LENGTH,
    STEP_NAME_MAX_STRING_LENGTH,
    ALL_CAMERAS_STR,
    ALL_STATE_SETS_STR,
    ALLOWED_RENDERERS,
)
from deadline.max_submitter.data_classes import (
    BatchRenderSettings,
    RenderSubmitterUISettings,
    SubmissionMode,
)


@fixture(scope="function", autouse=True)
def mock_max_utils():
    with patch("deadline.max_submitter.sanity_checks.max_utils") as mock_max_utils:
        mock_max_utils.get_camera_names.return_value = [
            create_random_string(JOB_PARAMETER_MAX_STRING_LENGTH)
        ]
        mock_max_utils.get_state_set_names.return_value = [
            [
                create_random_string(STEP_NAME_MAX_STRING_LENGTH),
                create_random_string(STEP_NAME_MAX_STRING_LENGTH),
            ]
        ]
        mock_max_utils.is_correct_frame_range.return_value = True
        mock_max_utils.get_duplicate_frames.return_value = False
        yield mock_max_utils


@fixture(scope="function", autouse=True)
def mock_pymx_runtime():
    with patch("deadline.max_submitter.sanity_checks.rt") as mock_pymx_runtime:
        mock_pymx_runtime.renderers.current = ALLOWED_RENDERERS[0]
        mock_pymx_runtime.maxFileName = "test_scene.max"
        mock_pymx_runtime.rendOutputFilename = "test_output.png"
        mock_pymx_runtime.rendTimeType = 1  # Single frame
        mock_pymx_runtime.checkForSave.return_value = None
        mock_pymx_runtime.execute.return_value = None
        yield mock_pymx_runtime


@fixture(scope="function")
def default_settings() -> RenderSubmitterUISettings:
    settings: RenderSubmitterUISettings = RenderSubmitterUISettings()
    settings.name = "test_job_name"
    settings.project_path = create_random_string(JOB_PARAMETER_MAX_STRING_LENGTH)
    settings.output_path = create_random_string(JOB_PARAMETER_MAX_STRING_LENGTH)
    settings.output_name = create_random_string(JOB_PARAMETER_MAX_STRING_LENGTH)
    settings.camera_selection = ALL_CAMERAS_STR
    settings.state_set = ALL_STATE_SETS_STR
    settings.override_frame_range = True
    settings.frame_list = create_frame_range(JOB_PARAMETER_MAX_STRING_LENGTH)

    return settings


def create_random_string(length: int) -> str:
    return "".join(random.choice(string.ascii_letters) for _ in range(length))


def create_frame_range(length: int) -> str:
    frame_range: str = ""
    iteration: int = 0
    while len(frame_range) <= length:
        frame_range += f"{str(iteration)},"

    frame_range = frame_range[:-1]

    if len(frame_range) > length:
        frame_range = frame_range[: frame_range.rfind(",")]

    return frame_range


class TestSanityChecks:

    def test_check_sanity_project_path_length(
        self,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        check_sanity(default_settings)

        default_settings.project_path = create_random_string(JOB_PARAMETER_MAX_STRING_LENGTH + 1)

        with raises(Exception):
            check_sanity(default_settings)

    def test_check_sanity_output_path_length(
        self,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        check_sanity(default_settings)

        default_settings.output_path = create_random_string(JOB_PARAMETER_MAX_STRING_LENGTH + 1)

        with raises(Exception):
            check_sanity(default_settings)

    def test_check_sanity_output_file_name_length(
        self,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        check_sanity(default_settings)

        default_settings.output_name = create_random_string(JOB_PARAMETER_MAX_STRING_LENGTH + 1)

        with raises(Exception):
            check_sanity(default_settings)

    def test_check_sanity_state_set_name_length(
        self,
        mock_max_utils: Mock,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        check_sanity(default_settings)

        mock_max_utils.get_state_set_names.return_value = [
            [
                create_random_string(STEP_NAME_MAX_STRING_LENGTH + 1),
                create_random_string(STEP_NAME_MAX_STRING_LENGTH + 1),
            ]
        ]

        with raises(Exception):
            check_sanity(default_settings)

    def test_check_sanity_camera_name_length(
        self,
        default_settings: RenderSubmitterUISettings,
        mock_max_utils: Mock,
    ) -> None:
        check_sanity(default_settings)

        mock_max_utils.get_camera_names.return_value = [
            create_random_string(JOB_PARAMETER_MAX_STRING_LENGTH + 1)
        ]

        with raises(Exception):
            check_sanity(default_settings)

    def test_check_frame_range_length(
        self,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        check_sanity(default_settings)

        default_settings.frame_list = create_frame_range(JOB_PARAMETER_MAX_STRING_LENGTH + 1)

        with raises(Exception):
            check_sanity(default_settings)

    def test_check_sanity_specific_state_set_vray_5_update_renderer(
        self,
        mock_pymx_runtime: Mock,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        """Test that V_Ray_5__update_2_3 renderer is accepted (starts with V_Ray_5)"""
        mock_pymx_runtime.renderers.current = "V_Ray_5__update_2_3:V-Ray 5, update 2.3"
        mock_pymx_runtime.rendOutputFilename = ""

        # Should not raise an exception
        check_sanity_specific_state_set(default_settings, "test_state_set")

    def test_check_sanity_specific_state_set_vray_6_update_renderer(
        self,
        mock_pymx_runtime: Mock,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        """Test that V_Ray_6__update_2_1 renderer is accepted (starts with V_Ray_6)"""
        mock_pymx_runtime.renderers.current = "V_Ray_6__update_2_1:V-Ray 6, update 2.1"
        mock_pymx_runtime.rendOutputFilename = ""

        # Should not raise an exception
        check_sanity_specific_state_set(default_settings, "test_state_set")

    def test_check_sanity_specific_state_set_vray_gpu_7_hotfix_renderer(
        self,
        mock_pymx_runtime: Mock,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        """Test that V_Ray_GPU_7_Hotfix_2 renderer is accepted (starts with V_Ray_GPU_7)"""
        mock_pymx_runtime.renderers.current = "V_Ray_GPU_7_Hotfix_2:V-Ray GPU 7, Hotfix 2"
        mock_pymx_runtime.rendOutputFilename = ""

        # Should not raise an exception
        check_sanity_specific_state_set(default_settings, "test_state_set")

    def test_check_sanity_specific_state_set_vray_7_hotfix_renderer(
        self,
        mock_pymx_runtime: Mock,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        """Test that V_Ray_7_Hotfix_2 renderer is accepted (starts with V_Ray_7)"""
        mock_pymx_runtime.renderers.current = "V_Ray_7_Hotfix_2:V-Ray 7, Hotfix 2"
        mock_pymx_runtime.rendOutputFilename = ""

        # Should not raise an exception
        check_sanity_specific_state_set(default_settings, "test_state_set")

    def test_check_sanity_specific_state_set_unsupported_renderer(
        self,
        mock_pymx_runtime: Mock,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        """Test that an unsupported renderer raises an exception"""
        mock_pymx_runtime.renderers.current = "Unsupported_Renderer:Some Unsupported Renderer"
        mock_pymx_runtime.rendOutputFilename = ""

        with raises(Exception, match="has an unsupported renderer set"):
            check_sanity_specific_state_set(default_settings, "test_state_set")

    def test_allowed_renderers_no_substring_conflicts(self) -> None:
        """Test that none of the allowed renderers is a substring of another.

        This prevents issues where renderer version checking might incorrectly match
        a shorter renderer name that is a substring of a longer one.
        For example, if 'V_Ray' and 'V_Ray_6' were both in the list,
        'V_Ray_6_update_1' would match 'V_Ray' first instead of 'V_Ray_6'.
        """
        for i, renderer_a in enumerate(ALLOWED_RENDERERS):
            for j, renderer_b in enumerate(ALLOWED_RENDERERS):
                if i != j:  # Don't compare renderer with itself
                    assert renderer_a not in renderer_b, (
                        f"Renderer '{renderer_a}' is a substring of '{renderer_b}'. "
                        f"This could cause incorrect renderer detection. "
                        f"Consider using more specific renderer names or reordering the list."
                    )
                    assert renderer_b not in renderer_a, (
                        f"Renderer '{renderer_b}' is a substring of '{renderer_a}'. "
                        f"This could cause incorrect renderer detection. "
                        f"Consider using more specific renderer names or reordering the list."
                    )


class TestCheckSanityBatchRender:
    """Tests for check_sanity_batch_render function."""

    @fixture
    def batch_settings(self) -> RenderSubmitterUISettings:
        """Create settings with batch rendering enabled."""
        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.submission_mode = SubmissionMode.BATCH_RENDER.value
        settings.batch_render = BatchRenderSettings(enabled_views=["Item1", "view2"])
        return settings

    @patch("deadline.max_submitter.sanity_checks.get_batch_render_views")
    def test_skips_checks_when_batch_disabled(
        self, mock_get_batch_views, default_settings: RenderSubmitterUISettings
    ):
        """Verify no checks are performed when batch rendering is disabled."""
        default_settings.submission_mode = SubmissionMode.DEFAULT.value

        # Should not raise and should not call get_batch_render_views
        check_sanity_batch_render(default_settings)
        mock_get_batch_views.assert_not_called()

    @patch("deadline.max_submitter.sanity_checks.get_batch_render_views")
    def test_raises_when_no_enabled_views(
        self, mock_get_batch_views, batch_settings: RenderSubmitterUISettings
    ):
        """Verify exception is raised when no batch views are enabled."""
        # Return items but none are enabled
        mock_get_batch_views.return_value = [
            BatchRenderView(name="view1", enabled=False),
            BatchRenderView(name="Item3", enabled=False),
        ]

        with raises(
            Exception,
            match="No enabled batch views found. Please enable at least one view in the Batch Render Manager.",
        ):
            check_sanity_batch_render(batch_settings)

    @patch("deadline.max_submitter.sanity_checks.get_batch_render_views")
    def test_passes_with_enabled_views(
        self, mock_get_batch_views, batch_settings: RenderSubmitterUISettings
    ):
        """Verify no exception when enabled batch views exist."""
        mock_get_batch_views.return_value = [
            BatchRenderView(name="view1", enabled=True, output_filename="C:/output/render.png"),
            BatchRenderView(name="view2", enabled=True, output_filename="C:/output/render2.png"),
        ]

        # Should not raise
        check_sanity_batch_render(batch_settings)

    @patch("deadline.max_submitter.sanity_checks.max_utils.get_camera_names")
    @patch("deadline.max_submitter.sanity_checks.get_batch_render_views")
    def test_raises_on_missing_output_filename(
        self,
        mock_get_batch_views,
        mock_get_camera_names,
        batch_settings: RenderSubmitterUISettings,
    ):
        """Verify exception lists all batch views missing output filenames."""
        mock_get_camera_names.return_value = ["Camera001"]
        mock_get_batch_views.return_value = [
            BatchRenderView(name="view1", enabled=True, output_filename=""),
            BatchRenderView(name="view2", enabled=True, output_filename=""),
            BatchRenderView(name="view3", enabled=True, output_filename="C:/output/render.png"),
        ]

        with raises(
            Exception,
            match=r"(?s)- view1.*- view2",
        ):
            check_sanity_batch_render(batch_settings)

    @patch("deadline.max_submitter.sanity_checks.max_utils.get_camera_names")
    @patch("deadline.max_submitter.sanity_checks.get_batch_render_views")
    def test_warns_on_conflicting_output_paths(
        self,
        mock_get_batch_views,
        mock_get_camera_names,
        batch_settings: RenderSubmitterUISettings,
        caplog,
    ):
        """Verify warning is logged when multiple items write to same output."""
        mock_get_camera_names.return_value = ["Camera001"]
        mock_get_batch_views.return_value = [
            BatchRenderView(name="view1", enabled=True, output_filename="C:/output/render.png"),
            BatchRenderView(
                name="view2", enabled=True, output_filename="C:/output/render.png"
            ),  # Same
        ]

        with caplog.at_level(logging.WARNING):
            check_sanity_batch_render(batch_settings)

        assert "Multiple batch views write to the same output path" in caplog.text

    @patch("deadline.max_submitter.sanity_checks.max_utils.get_camera_names")
    @patch("deadline.max_submitter.sanity_checks.get_batch_render_views")
    def test_warns_on_missing_camera(
        self,
        mock_get_batch_views,
        mock_get_camera_names,
        batch_settings: RenderSubmitterUISettings,
        caplog,
    ):
        """Verify warning is logged when batch view references non-existent camera."""

        mock_get_camera_names.return_value = ["Camera001", "Camera002"]
        mock_get_batch_views.return_value = [
            BatchRenderView(
                name="Item1",
                enabled=True,
                camera="NonExistentCamera",
                output_filename="C:/output/render.png",
            ),
        ]

        with caplog.at_level(logging.WARNING):
            check_sanity_batch_render(batch_settings)

        assert "does not exist in scene" in caplog.text
