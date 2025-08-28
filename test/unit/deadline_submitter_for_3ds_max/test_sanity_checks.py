# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import random
import string

from unittest.mock import patch, Mock
from pytest import fixture, raises

from deadline.max_submitter.sanity_checks import (
    check_sanity,
    check_sanity_specific_state_set,
    JOB_PARAMETER_MAX_STRING_LENGTH,
    STEP_NAME_MAX_STRING_LENGTH,
    ALL_CAMERAS_STR,
    ALL_STATE_SETS_STR,
    ALLOWED_RENDERERS,
)
from deadline.max_submitter.data_classes import RenderSubmitterUISettings


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

    def test_check_sanity_specific_state_set_vray_6_update_renderer(
        self,
        mock_pymx_runtime: Mock,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        """Test that V_Ray_6__update_2_1 renderer is accepted (splits by __ to V_Ray_6)"""
        mock_pymx_runtime.renderers.current = "V_Ray_6__update_2_1:V-Ray 6, update 2.1"
        mock_pymx_runtime.rendOutputFilename = ""

        # Should not raise an exception
        check_sanity_specific_state_set(default_settings, "test_state_set")

    def test_check_sanity_specific_state_set_vray_gpu_7_hotfix_renderer(
        self,
        mock_pymx_runtime: Mock,
        default_settings: RenderSubmitterUISettings,
    ) -> None:
        """Test that V_Ray_GPU_7_Hotfix_2 renderer is accepted (splits by _ to V_Ray_GPU_7)"""
        mock_pymx_runtime.renderers.current = "V_Ray_GPU_7_Hotfix_2:V-Ray GPU 7, Hotfix 2"
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
