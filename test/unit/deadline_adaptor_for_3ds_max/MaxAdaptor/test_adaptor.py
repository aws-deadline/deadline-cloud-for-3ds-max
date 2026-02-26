# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

import jsonschema  # type: ignore
import pytest
from openjd.adaptor_runtime.adaptors import SemanticVersion
from deadline.max_adaptor.MaxAdaptor import MaxAdaptor
from deadline.max_adaptor.MaxAdaptor.adaptor import _FIRST_MAX_ACTIONS, MaxNotRunningError

# Test data that exercises ALL properties in init_data schema
# If the schema changes (properties added/removed/modified), this test data
# must be updated AND the integration_data_interface_version must be bumped
EXPECTED_INIT_DATA_PROPERTIES = {
    "camera": "Camera001",
    "output_file_path": "/path/to/output",
    "output_file_name": "output_###",
    "output_file_format": ".jpg",
    "state_set": "State01",
    "scene_state": "MySceneState",
    "preset_file": "/path/to/preset.rps",
    "pixel_aspect": "1.0",
    "renderer": "Default_Scanline_Renderer",
    "scene_file": "/path/to/scene.max",
    "strict_error_checking": True,
    "enabled_modify_render_elements": "false",
    "render_elements": "false",
    "render_elements_update_paths": "false",
    "render_elements_include_name_in_path": "false",
    "render_elements_include_type_in_path": "false",
    "render_elements_include_name_in_filename": "false",
    "render_elements_include_type_in_filename": "false",
    "vray_render_elements_vfb_control": "false",
    "vray_split_buffer_support": "false",
    "ignore_render_elements_by_name": "element1,element2",
}

# Required fields for init_data schema
EXPECTED_INIT_DATA_REQUIRED = ["renderer", "scene_file"]

# Test data that exercises ALL properties in run_data schema
# If the schema changes (properties added/removed/modified), this test data
# must be updated AND the integration_data_interface_version must be bumped
EXPECTED_RUN_DATA_PROPERTIES = {
    "frame": 1,
    "camera": "Camera001",
}

# Required fields for run_data schema
EXPECTED_RUN_DATA_REQUIRED = ["frame"]

# Expected version - must be bumped when schemas change
EXPECTED_SCHEMA_VERSION_MAJOR = 0
EXPECTED_SCHEMA_VERSION_MINOR = 3


@pytest.fixture
def init_data() -> dict:
    """
    Pytest Fixture to return an init_data dictionary that passes validation

    Returns:
        dict: An init_data dictionary
    """
    return {
        # "animation": True,
        "renderer": "Default_Scanline_Renderer",
        "state_set": "State01",
        "strict_error_checking": True,
        # "version": 2022,
        "output_file_path": "C:/workspace/deadline-cloud-for-3ds-max/test_projects/adaptor/output",
        "scene_file": "C:/workspace/deadline-cloud-for-3ds-max/test_projects/adaptor/teapot_blank.max",
        "camera": "Camera001",
        "output_file_name": "output_###",
    }


@pytest.fixture
def run_data() -> dict:
    """
    Pytest Fixture to return a run_data dictionary that passes validation

    Returns:
        dict: A run_data dictionary
    """
    return {"frame": 42}


class TestMaxAdaptor_semantic_version:
    def test_semantic_version(self, init_data: dict) -> None:
        """Tests that the adaptor semantic version is in the expected format"""
        adaptor = MaxAdaptor(init_data)
        assert adaptor.integration_data_interface_version == SemanticVersion(major=0, minor=3)

    def test_if_init_data_and_run_data_schema_are_changed_schema_version_is_bumped(
        self, init_data: dict
    ) -> None:
        """
        Test to validate that if the init data or run data schema are changed, we also bump the
        integration_data_interface_version. We load the schema files and validate expected test data
        that we define as EXPECTED_INIT_DATA_PROPERTIES and EXPECTED_RUN_DATA_PROPERTIES
        """
        adaptor = MaxAdaptor(init_data)
        semantic_version = adaptor.integration_data_interface_version

        root_directory_path = Path(__file__).parent.parent.parent.parent.parent
        schema_path = root_directory_path.joinpath(
            "src", "deadline", "max_adaptor", "MaxAdaptor", "schemas"
        )
        init_data_path = schema_path.joinpath("init_data.schema.json")
        run_data_path = schema_path.joinpath("run_data.schema.json")

        # Load actual schemas
        with init_data_path.open() as init_data_schema_file:
            init_data_schema = json.load(init_data_schema_file)

        with run_data_path.open() as run_data_schema_file:
            run_data_schema = json.load(run_data_schema_file)

        # Validate that our test data covers all schema properties
        init_schema_properties = set(init_data_schema.get("properties", {}).keys())
        expected_init_properties = set(EXPECTED_INIT_DATA_PROPERTIES.keys())

        run_schema_properties = set(run_data_schema.get("properties", {}).keys())
        expected_run_properties = set(EXPECTED_RUN_DATA_PROPERTIES.keys())

        # Check init_data schema properties
        assert init_schema_properties == expected_init_properties, (
            f"If the init_data.schema.json is changed, the integration_data_interface_version must be bumped. "
            f"Schema properties have changed - "
            f"Missing in test: {init_schema_properties - expected_init_properties}. "
            f"Extra in test: {expected_init_properties - init_schema_properties}. "
        )

        # Check run_data schema properties
        assert run_schema_properties == expected_run_properties, (
            f"If the run_data.schema.json is changed, the integration_data_interface_version must be bumped. "
            f"Schema properties have changed - "
            f"Missing in test: {run_schema_properties - expected_run_properties}. "
            f"Extra in test: {expected_run_properties - run_schema_properties}. "
        )

        # Check init_data required fields
        init_schema_required = set(init_data_schema.get("required", []))
        expected_init_required = set(EXPECTED_INIT_DATA_REQUIRED)
        assert init_schema_required == expected_init_required, (
            f"If the init_data.schema.json is changed, the integration_data_interface_version must be bumped. "
            f"Schema required fields have changed - "
            f"Missing in test: {init_schema_required - expected_init_required}. "
            f"Extra in test: {expected_init_required - init_schema_required}. "
        )

        # Check run_data required fields
        run_schema_required = set(run_data_schema.get("required", []))
        expected_run_required = set(EXPECTED_RUN_DATA_REQUIRED)
        assert run_schema_required == expected_run_required, (
            f"If the run_data.schema.json is changed, the integration_data_interface_version must be bumped. "
            f"Schema required fields have changed - "
            f"Missing in test: {run_schema_required - expected_run_required}. "
            f"Extra in test: {expected_run_required - run_schema_required}. "
        )

        # Validate test data against schemas using jsonschema
        try:
            jsonschema.validate(EXPECTED_INIT_DATA_PROPERTIES, init_data_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(
                f"If the init_data.schema.json is changed, the integration_data_interface_version must be bumped. "
                f"Schema validation failed: {e.message}. "
            )

        try:
            jsonschema.validate(EXPECTED_RUN_DATA_PROPERTIES, run_data_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(
                f"If the run_data.schema.json is changed, the integration_data_interface_version must be bumped. "
                f"Schema validation failed: {e.message}. "
            )

        # Verify version matches expected version
        assert semantic_version.major == EXPECTED_SCHEMA_VERSION_MAJOR, (
            f"If the init_data.schema.json or run_data.schema.json is changed, "
            f"the integration_data_interface_version must be bumped. "
            f"Expected major version {EXPECTED_SCHEMA_VERSION_MAJOR}, got {semantic_version.major}. "
        )
        assert semantic_version.minor == EXPECTED_SCHEMA_VERSION_MINOR, (
            f"If the init_data.schema.json or run_data.schema.json is changed, "
            f"the integration_data_interface_version must be bumped. "
            f"Expected minor version {EXPECTED_SCHEMA_VERSION_MINOR}, got {semantic_version.minor}. "
        )


class TestMaxAdaptor_on_start:
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_no_error(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        init_data: dict,
    ) -> None:
        """Tests that on_start completes without error"""
        adaptor = MaxAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        adaptor.on_start()

    @patch("time.sleep")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test__wait_for_socket(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
    ) -> None:
        """Tests that the _wait_for_socket method sleeps until a server path is available"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)
        server_mock = PropertyMock(
            side_effect=[None, None, None, "/tmp/9999", "/tmp/9999", "/tmp/9999"]
        )
        type(mock_server.return_value).server_path = server_mock

        # WHEN
        adaptor.on_start()

        # THEN
        assert mock_sleep.call_count == 3

    @patch("threading.Thread")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_server_init_fail(self, mock_server: Mock, mock_thread: Mock, init_data: dict) -> None:
        """Tests that an error is raised if no server path becomes available"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)

        with (
            patch.object(adaptor, "_SERVER_START_TIMEOUT_SECONDS", 0.01),
            pytest.raises(RuntimeError) as exc_info,
        ):
            # WHEN
            adaptor.on_start()

        # THEN
        assert (
            str(exc_info.value)
            == "Could not find a server path because the server did not finish initializing"
        )

    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=1)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_max_init_timeout(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        init_data: dict,
    ) -> None:
        """
        Tests that a TimeoutError is raised if the max client does not complete initialization
        tasks within a given time frame
        """
        # GIVEN
        adaptor = MaxAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        new_timeout = 0.01

        with (
            patch.object(adaptor, "_MAX_START_TIMEOUT_SECONDS", new_timeout),
            pytest.raises(TimeoutError) as exc_info,
        ):
            # WHEN
            adaptor.on_start()

        # THEN
        error_msg = (
            f"Max did not complete initialization actions in {new_timeout} seconds and "
            "failed to start."
        )
        assert str(exc_info.value) == error_msg

    @patch.object(MaxAdaptor, "_max_is_running", False)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=1)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_max_init_fail(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        init_data: dict,
    ) -> None:
        """
        Tests that an RuntimeError is raised if the max client encounters an exception
        """
        # GIVEN
        adaptor = MaxAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"

        with pytest.raises(RuntimeError) as exc_info:
            # WHEN
            adaptor.on_start()

        # THEN
        error_msg = "Max encountered an error and was not able to complete initialization actions."
        assert str(exc_info.value) == error_msg

    @patch.object(MaxAdaptor, "_action_queue")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_populate_action_queue_required_keys(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
    ) -> None:
        """Tests that on_start completes without error"""
        mock_actions_queue.__len__.return_value = 0

        adaptor = MaxAdaptor(
            {
                "renderer": "Default_Scanline_Renderer",
                "scene_file": "/path/to/file",
                # "animation": True,
                # "version": 2022,
                "state_set": "State01",
            }
        )

        mock_server.return_value.server_path = "/tmp/9999"

        adaptor.on_start()

        calls = mock_actions_queue.enqueue_action.call_args_list
        assert calls[0].args[0].name == "renderer"
        for call, action_name in zip(calls[1 : len(_FIRST_MAX_ACTIONS) + 2], _FIRST_MAX_ACTIONS):
            assert call.args[0].name == action_name

    @patch.object(MaxAdaptor, "_max_is_running", False)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=1)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_init_data_wrong_schema(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
    ) -> None:
        """
        Tests that an RuntimeError is raised if the max client encounters an exception
        """
        # GIVEN
        init_data = {"doesNot": "conform", "thisData": "isBad"}
        adaptor = MaxAdaptor(init_data)

        with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
            # WHEN
            adaptor.on_start()

        # THEN
        error_msg = " is a required property"
        assert error_msg in exc_info.value.message


class TestMaxAdaptor_on_run:
    @patch("time.sleep")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_on_run(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run completes without error, and waits"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        # First side_effect value consumed by setter
        is_rendering_mock = PropertyMock(side_effect=[None, True, False])
        MaxAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()

        # WHEN
        adaptor.on_run(run_data)

        # THEN
        mock_sleep.assert_called_once_with(0.1)

    @patch("time.sleep")
    @patch(
        "deadline.max_adaptor.MaxAdaptor.adaptor.MaxAdaptor._is_rendering",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.max_adaptor.MaxAdaptor.adaptor.MaxAdaptor._max_is_running",
        new_callable=PropertyMock,
    )
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_on_run_render_fail(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_max_is_running: Mock,
        mock_is_rendering: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run raises an error if the render fails"""
        # GIVEN
        mock_is_rendering.side_effect = [None, True, False]
        mock_max_is_running.side_effect = [True, True, True, False, False]
        mock_logging_subprocess.return_value.returncode = 1
        adaptor = MaxAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        adaptor.on_start()

        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            adaptor.on_run(run_data)

        # THEN
        mock_sleep.assert_called_once_with(0.1)
        assert str(exc_info.value) == (
            "Max exited early and did not render successfully, please check render logs. "
            "Exit code 1"
        )

    @patch("time.sleep")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_run_data_wrong_schema(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
    ) -> None:
        """Tests that on_run completes without error, and waits"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        # First side_effect value consumed by setter
        is_rendering_mock = PropertyMock(side_effect=[None, True, False])
        MaxAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()
        run_data = {"bad": "data"}

        with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
            # WHEN
            adaptor.on_run(run_data)

        # THEN
        error_msg = " is a required property"
        assert error_msg in exc_info.value.message


class TestMaxAdaptor_on_stop:

    @patch("time.sleep")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_on_stop(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_stop completes without error"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        is_rendering_mock = PropertyMock(return_value=False)
        MaxAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()
        adaptor.on_run(run_data)

        # WHEN
        adaptor.on_stop()


class TestMaxAdaptor_on_cleanup:
    @patch("time.sleep")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor._logger")
    def test_on_cleanup_max_not_graceful_shutdown(
        self, mock_logger: Mock, mock_sleep: Mock, init_data: dict
    ) -> None:
        """Tests that on_cleanup reports when max does not gracefully shutdown"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)

        with (
            patch(
                "deadline.max_adaptor.MaxAdaptor.adaptor.MaxAdaptor._max_is_running",
                new_callable=lambda: True,
            ),
            patch.object(adaptor, "_MAX_END_TIMEOUT_SECONDS", 0.01),
            patch.object(adaptor, "_max_client") as mock_client,
        ):
            # WHEN
            adaptor.on_cleanup()

        # THEN
        mock_logger.error.assert_called_once_with(
            "Max did not complete cleanup actions and failed to gracefully shutdown. Terminating."
        )
        mock_client.terminate.assert_called_once()

    @patch("time.sleep")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor._logger")
    def test_on_cleanup_server_not_graceful_shutdown(
        self, mock_logger: Mock, mock_sleep: Mock, init_data: dict
    ) -> None:
        """Tests that on_cleanup reports when the server does not shutdown"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)

        with (
            patch(
                "deadline.max_adaptor.MaxAdaptor.adaptor.MaxAdaptor._max_is_running",
                new_callable=lambda: False,
            ),
            patch.object(adaptor, "_SERVER_END_TIMEOUT_SECONDS", 0.01),
            patch.object(adaptor, "_server_thread") as mock_server_thread,
        ):
            mock_server_thread.is_alive.return_value = True
            # WHEN
            adaptor.on_cleanup()

        # THEN
        mock_logger.error.assert_called_once_with("Failed to shutdown the Max Adaptor server.")
        mock_server_thread.join.assert_called_once_with(timeout=0.01)

    @patch("time.sleep")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.AdaptorServer")
    def test_on_cleanup(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_stop completes without error"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        is_rendering_mock = PropertyMock(return_value=False)
        MaxAdaptor._is_rendering = is_rendering_mock

        adaptor.on_start()
        adaptor.on_run(run_data)
        adaptor.on_stop()

        with patch(
            "deadline.max_adaptor.MaxAdaptor.adaptor.MaxAdaptor._max_is_running",
            new_callable=lambda: False,
        ):
            # WHEN
            adaptor.on_cleanup()

    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.MaxAdaptor.update_status")
    def test_handle_complete(self, mock_update_status: Mock, init_data: dict):
        """Tests that the _handle_complete method updates the progress correctly"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)
        regex_callbacks = adaptor._get_regex_callbacks()
        complete_regex = regex_callbacks[0].regex_list[0]

        # WHEN
        match = complete_regex.search("MaxClient: Finished Rendering Frame 1")
        if match:
            adaptor._handle_complete(match)

        # THEN
        assert match is not None
        mock_update_status.assert_called_once_with(progress=100)

    handle_progess_params = [(0, "[PROGRESS] 99 percent", 99)]

    @pytest.mark.parametrize("regex_index, stdout, expected_progress", handle_progess_params)
    @patch("deadline.max_adaptor.MaxAdaptor.adaptor.MaxAdaptor.update_status")
    def test_handle_progress(
        self,
        mock_update_status: Mock,
        regex_index: int,
        stdout: str,
        expected_progress: float,
        init_data: dict,
    ) -> None:
        """Tests that the _handle_progress method updates the progress correctly"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)
        regex_callbacks = adaptor._get_regex_callbacks()
        progress_regex = regex_callbacks[1].regex_list[regex_index]

        # WHEN
        match = progress_regex.search(stdout)
        if match:
            adaptor._handle_progress(match)

        # THEN
        assert match is not None
        mock_update_status.assert_called_once_with(progress=expected_progress)

    @pytest.mark.parametrize(
        "stdout, error_regex",
        [
            (
                "RuntimeError: Error encountered when initializing Max - Please check for "
                "sufficient disk space and necessary write permissions of MAX_APP_DIR.",
                re.compile(".*Error:.*"),
            ),
            (
                "Warning: file: somefile.mel line 1: filePathEditor: Attribute 'aiVolume.filename'"
                " is invalid or is not designated 'usedAsFilename'.",
                re.compile(".*Warning:.*"),
            ),
        ],
    )
    def test_handle_error(self, init_data: dict, stdout: str, error_regex: re.Pattern) -> None:
        """Tests that the _handle_error method throws a runtime error correctly"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)

        # WHEN
        match = error_regex.search(stdout)
        if match:
            adaptor._handle_error(match)

        # THEN
        assert match is not None
        assert str(adaptor._exc_info) == f"Max Encountered an Error: {stdout}"

    @pytest.mark.parametrize("strict_error_checking", [True, False])
    def test_strict_error_checking(self, init_data: dict, strict_error_checking: bool) -> None:
        """
        Tests that the strict_error_checking flag in the init_data determines if the handle_error
        RegexCallback is returned in the _get_regex_callbacks function
        """
        # GIVEN
        init_data["strict_error_checking"] = strict_error_checking
        adaptor = MaxAdaptor(init_data)
        error_regexes = [re.compile(".*Exception:.*|.*Error:.*|.*Warning.*")]

        # WHEN
        callbacks = adaptor._get_regex_callbacks()

        # THEN
        assert (
            any(error_regexes == regex_callback.regex_list for regex_callback in callbacks)
            == strict_error_checking
        )

    @pytest.mark.parametrize("adaptor_exc_info", [RuntimeError("Something Bad Happened!"), None])
    def test_has_exception(self, init_data: dict, adaptor_exc_info: Exception | None) -> None:
        """
        Validates that the adaptor._has_exception property raises when adaptor._exc_info is not None
        and returns false when adaptor._exc_info is None
        """
        adaptor = MaxAdaptor(init_data)
        adaptor._exc_info = adaptor_exc_info

        if adaptor_exc_info:
            with pytest.raises(RuntimeError) as exc_info:
                adaptor._has_exception

            assert exc_info.value == adaptor_exc_info
        else:
            assert not adaptor._has_exception

    @patch.object(MaxAdaptor, "_max_is_running", new_callable=PropertyMock(return_value=False))
    def test_raises_if_max_not_running(
        self,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run raises a MaxNotRunningError if max is not running"""
        # GIVEN
        adaptor = MaxAdaptor(init_data)

        # WHEN
        with pytest.raises(MaxNotRunningError) as raised_err:
            adaptor.on_run(run_data)

        # THEN
        assert raised_err.match("Cannot render because Max is not running.")


class TestMaxAdaptor_on_cancel:
    """Tests for MaxAdaptor.on_cancel"""

    def test_terminates_max_client(self, init_data: dict, caplog: pytest.LogCaptureFixture):
        """Tests that the max client is terminated on cancel"""
        # GIVEN
        caplog.set_level(0)
        adaptor = MaxAdaptor(init_data)
        adaptor._max_client = mock_client = Mock()

        # WHEN
        adaptor.on_cancel()

        # THEN
        mock_client.terminate.assert_called_once_with(grace_time_s=0)
        assert "CANCEL REQUESTED" in caplog.text

    def test_does_nothing_if_max_not_running(
        self, init_data: dict, caplog: pytest.LogCaptureFixture
    ):
        """Tests that nothing happens if a cancel is requested when max is not running"""
        # GIVEN
        caplog.set_level(0)
        adaptor = MaxAdaptor(init_data)
        adaptor._max_client = None

        # WHEN
        adaptor.on_cancel()

        # THEN
        assert "CANCEL REQUESTED" in caplog.text
        assert "Nothing to cancel because Max is not running" in caplog.text
