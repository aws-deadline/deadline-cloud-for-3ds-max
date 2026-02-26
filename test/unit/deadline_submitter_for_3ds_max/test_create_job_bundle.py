# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for create_job_bundle.py functions.
"""

from unittest.mock import Mock, patch
import pytest

from deadline.max_shared.utilities.max_utils import BatchRenderView


@pytest.fixture
def sample_state_set():
    """Create a sample StateSetData for testing."""
    from deadline.max_submitter.data_classes import StateSetData

    return StateSetData(
        state_set="Default",
        renderer="V_Ray_6",
        frame_range="1-100",
        output_directories={"/output"},
        output_file_dir="/output",
        output_file_name="render_####",
        output_file_format=".png",
        image_resolution=(1920, 1080),
        ui_group_label="Default State Set",
    )


@pytest.fixture
def sample_batch_view():
    """Create a sample BatchRenderView for testing."""
    return BatchRenderView(
        name="TestBatchView",
        enabled=True,
        camera="Camera001",
        output_filename="C:/output/render.png",
        scene_state="MySceneState",
        preset_file="C:/presets/render.rps",
        override_preset=True,
        frame_start=1,
        frame_end=100,
        width=1920,
        height=1080,
        pixel_aspect=1.0,
    )


class TestCreateParamDefinitions:
    """Tests for _create_param_definitions function."""

    @pytest.fixture
    def default_job_template(self):
        """Create a minimal default job template."""
        return {
            "name": "",
            "parameterDefinitions": [],
            "steps": [
                {
                    "name": "Default",
                    "parameterSpace": {
                        "taskParameterDefinitions": [{"name": "Frame", "range": ""}]
                    },
                    "stepEnvironments": [{"script": {"embeddedFiles": [{"data": ""}]}}],
                    "script": {"embeddedFiles": [{"data": ""}]},
                }
            ],
        }

    @pytest.fixture
    def mock_settings(self):
        """Create mock RenderSubmitterUISettings."""
        settings = Mock()
        settings.name = "TestJob"
        settings.description = "Test description"
        settings.batch_render_enabled = False
        settings.batch_render = Mock()
        settings.batch_render.enabled_views = []
        settings.camera_selection = "Camera001"
        settings.include_adaptor_wheels = False
        settings.enabled_modify_render_elements = False
        return settings

    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    def test_creates_step_params_without_batch(
        self,
        mock_get_render_elements,
        mock_get_batch_views,
        default_job_template,
        mock_settings,
        sample_state_set,
    ):
        """Verify step-specific parameters are created without batch rendering."""
        from deadline.max_submitter.create_job_bundle import _create_param_definitions

        mock_get_batch_views.return_value = []
        mock_get_render_elements.return_value = []

        result = _create_param_definitions(
            default_job_template, mock_settings, [sample_state_set], ["Camera001"]
        )

        # Verify job name is set
        assert result["name"] == "TestJob"

        # Verify step-specific parameters exist
        param_names = [p["name"] for p in result["parameterDefinitions"]]
        assert "Default_Frames" in param_names
        assert "Default_OutputFilePath" in param_names
        assert "Default_OutputFileFormat" in param_names
        assert "Default_ImageWidth" in param_names
        assert "Default_ImageHeight" in param_names

    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    def test_creates_step_params_with_batch(
        self,
        mock_get_render_elements,
        mock_get_batch_views,
        default_job_template,
        mock_settings,
        sample_state_set,
        sample_batch_view,
    ):
        """Verify step-specific parameters are created with batch rendering enabled."""
        from deadline.max_submitter.create_job_bundle import _create_param_definitions

        mock_settings.batch_render_enabled = True
        mock_settings.batch_render.enabled_views = ["TestBatchView"]
        mock_get_batch_views.return_value = [sample_batch_view]
        mock_get_render_elements.return_value = []

        result = _create_param_definitions(
            default_job_template, mock_settings, [sample_state_set], ["Camera001"]
        )

        # Verify batch view step parameters exist
        param_names = [p["name"] for p in result["parameterDefinitions"]]
        assert "StateSet_Default_Batch_TestBatchView_Frames" in param_names
        assert "StateSet_Default_Batch_TestBatchView_OutputFilePath" in param_names

    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    def test_camera_param_added_for_specific_camera(
        self,
        mock_get_render_elements,
        mock_get_batch_views,
        default_job_template,
        mock_settings,
        sample_state_set,
    ):
        """Verify Camera parameter is added when a specific camera is selected."""
        from deadline.max_submitter.create_job_bundle import _create_param_definitions

        mock_get_batch_views.return_value = []
        mock_get_render_elements.return_value = []
        mock_settings.camera_selection = "Camera001"

        result = _create_param_definitions(
            default_job_template, mock_settings, [sample_state_set], ["Camera001", "Camera002"]
        )

        param_names = [p["name"] for p in result["parameterDefinitions"]]
        assert "Camera" in param_names

    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    def test_camera_param_not_added_for_all_cameras(
        self,
        mock_get_render_elements,
        mock_get_batch_views,
        default_job_template,
        mock_settings,
        sample_state_set,
    ):
        """Verify Camera parameter is NOT added when all cameras are selected."""
        from deadline.max_submitter.create_job_bundle import _create_param_definitions
        from deadline.max_submitter.data_const import ALL_CAMERAS_STR

        mock_get_batch_views.return_value = []
        mock_get_render_elements.return_value = []
        mock_settings.camera_selection = ALL_CAMERAS_STR

        result = _create_param_definitions(
            default_job_template, mock_settings, [sample_state_set], ["Camera001", "Camera002"]
        )

        param_names = [p["name"] for p in result["parameterDefinitions"]]
        assert "Camera" not in param_names


class TestCreateStepDefinitions:
    """Tests for _create_step_definitions function."""

    @pytest.fixture
    def job_template_with_params(self):
        """Create a job template with parameter definitions."""
        return {
            "name": "TestJob",
            "parameterDefinitions": [],
            "steps": [
                {
                    "name": "Default",
                    "parameterSpace": {
                        "taskParameterDefinitions": [{"name": "Frame", "range": ""}]
                    },
                    "stepEnvironments": [{"script": {"embeddedFiles": [{"data": ""}]}}],
                    "script": {"embeddedFiles": [{"data": ""}]},
                }
            ],
        }

    @pytest.fixture
    def mock_settings(self):
        """Create mock RenderSubmitterUISettings."""
        settings = Mock()
        settings.batch_render_enabled = False
        settings.batch_render = Mock()
        settings.batch_render.enabled_views = []
        settings.camera_selection = "Camera001"
        return settings

    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    def test_creates_steps_without_batch(
        self,
        mock_get_render_elements,
        mock_get_batch_views,
        job_template_with_params,
        mock_settings,
        sample_state_set,
    ):
        """Verify steps are created without batch rendering."""
        from deadline.max_submitter.create_job_bundle import _create_step_definitions

        mock_get_batch_views.return_value = []
        mock_get_render_elements.return_value = []

        result = _create_step_definitions(
            job_template_with_params, mock_settings, [sample_state_set], ["Camera001"]
        )

        assert len(result["steps"]) == 1
        assert result["steps"][0]["name"] == "Default"

    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    def test_creates_steps_with_batch(
        self,
        mock_get_render_elements,
        mock_get_batch_views,
        job_template_with_params,
        mock_settings,
        sample_state_set,
        sample_batch_view,
    ):
        """Verify steps are created with batch rendering enabled."""
        from deadline.max_submitter.create_job_bundle import _create_step_definitions

        mock_settings.batch_render_enabled = True
        mock_settings.batch_render.enabled_views = ["TestBatchView"]
        mock_get_batch_views.return_value = [sample_batch_view]
        mock_get_render_elements.return_value = []

        result = _create_step_definitions(
            job_template_with_params, mock_settings, [sample_state_set], ["Camera001"]
        )

        assert len(result["steps"]) == 1
        assert result["steps"][0]["name"] == "StateSet_Default_Batch_TestBatchView"

        # Verify batch_render_view is in init data
        init_data = result["steps"][0]["stepEnvironments"][0]["script"]["embeddedFiles"][0]["data"]
        assert "batch_render_view: TestBatchView" in init_data

    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    def test_raises_without_state_sets(
        self,
        mock_get_render_elements,
        mock_get_batch_views,
        job_template_with_params,
        mock_settings,
    ):
        """Verify ValueError is raised when no state sets are provided."""
        from deadline.max_submitter.create_job_bundle import _create_step_definitions

        mock_get_batch_views.return_value = []
        mock_get_render_elements.return_value = []

        with pytest.raises(ValueError, match="At least one state set is required"):
            _create_step_definitions(job_template_with_params, mock_settings, [], ["Camera001"])


class TestGetBatchViewSettings:
    """Tests for _get_batch_view_settings function."""

    def test_returns_state_set_defaults_without_preset_or_overrides(self):
        """Verify state set defaults are returned when no preset or overrides."""
        from deadline.max_submitter.create_job_bundle import _get_batch_view_settings

        batch_view = BatchRenderView(name="Test", override_preset=False)

        result = _get_batch_view_settings(
            batch_view=batch_view,
            state_set_frame_range="1-100",
            state_set_resolution=(1920, 1080),
        )

        assert result["frame_range"] == "1-100"
        assert result["width"] == 1920
        assert result["height"] == 1080

    @patch("deadline.max_submitter.create_job_bundle.max_utils.extract_settings_from_preset")
    def test_uses_preset_values_when_available(self, mock_extract):
        """Verify preset values are used when preset file is provided."""
        from deadline.max_submitter.create_job_bundle import _get_batch_view_settings

        mock_extract.return_value = {
            "frame_range": "50-150",
            "width": 3840,
            "height": 2160,
        }

        batch_view = BatchRenderView(
            name="Test",
            preset_file="C:/presets/render.rps",
            override_preset=False,
        )

        result = _get_batch_view_settings(
            batch_view=batch_view,
            state_set_frame_range="1-100",
            state_set_resolution=(1920, 1080),
        )

        mock_extract.assert_called_once_with("C:/presets/render.rps")
        assert result["frame_range"] == "50-150"
        assert result["width"] == 3840
        assert result["height"] == 2160

    def test_override_values_take_precedence(self):
        """Verify override values take precedence over preset and state set."""
        from deadline.max_submitter.create_job_bundle import _get_batch_view_settings

        batch_view = BatchRenderView(
            name="Test",
            override_preset=True,
            frame_start=200,
            frame_end=300,
            width=4096,
            height=2048,
        )

        result = _get_batch_view_settings(
            batch_view=batch_view,
            state_set_frame_range="1-100",
            state_set_resolution=(1920, 1080),
        )

        assert result["frame_range"] == "200-300"
        assert result["width"] == 4096
        assert result["height"] == 2048

    @patch("deadline.max_submitter.create_job_bundle.max_utils.extract_settings_from_preset")
    def test_skips_preset_when_all_overrides_provided(self, mock_extract):
        """Verify preset loading is skipped when all overrides are provided."""
        from deadline.max_submitter.create_job_bundle import _get_batch_view_settings

        batch_view = BatchRenderView(
            name="Test",
            preset_file="C:/presets/render.rps",
            override_preset=True,
            frame_start=1,
            frame_end=100,
            width=1920,
            height=1080,
        )

        result = _get_batch_view_settings(
            batch_view=batch_view,
            state_set_frame_range="1-50",
            state_set_resolution=(1280, 720),
        )

        # Preset should not be loaded when has_all_overrides is True
        mock_extract.assert_not_called()
        assert result["frame_range"] == "1-100"
        assert result["width"] == 1920
        assert result["height"] == 1080

    @patch("deadline.max_submitter.create_job_bundle.max_utils.extract_settings_from_preset")
    def test_falls_back_on_preset_error(self, mock_extract):
        """Verify fallback to state set defaults when preset loading fails."""
        from deadline.max_submitter.create_job_bundle import _get_batch_view_settings

        mock_extract.side_effect = Exception("Failed to load preset")

        batch_view = BatchRenderView(
            name="Test",
            preset_file="C:/presets/bad.rps",
            override_preset=False,
        )

        result = _get_batch_view_settings(
            batch_view=batch_view,
            state_set_frame_range="1-100",
            state_set_resolution=(1920, 1080),
        )

        # Should fall back to state set defaults
        assert result["frame_range"] == "1-100"
        assert result["width"] == 1920
        assert result["height"] == 1080


class TestGetJobParameters:
    """Tests for _get_job_parameters function."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock RenderSubmitterUISettings."""
        settings = Mock()
        settings.batch_render_enabled = False
        settings.batch_render = Mock()
        settings.batch_render.enabled_views = []
        settings.camera_selection = "Camera001"
        settings.render_elements = False
        settings.enabled_modify_render_elements = False
        return settings

    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    @patch("deadline.max_submitter.create_job_bundle.max_utils.get_scene_path")
    def test_creates_parameters_without_batch(
        self,
        mock_get_scene_path,
        mock_get_render_elements,
        mock_get_batch_views,
        mock_settings,
        sample_state_set,
    ):
        """Verify parameters are created without batch rendering."""
        from deadline.max_submitter.create_job_bundle import _get_job_parameters

        mock_get_scene_path.return_value = "C:/scenes/test.max"
        mock_get_batch_views.return_value = []
        mock_get_render_elements.return_value = []

        result = _get_job_parameters(mock_settings, [sample_state_set])

        param_names = [p["name"] for p in result]
        assert "MaxSceneFile" in param_names
        assert "Default_Frames" in param_names
        assert "Default_OutputFilePath" in param_names
        assert "Camera" in param_names

    @patch("deadline.max_submitter.create_job_bundle.QProgressDialog")
    @patch("deadline.max_submitter.create_job_bundle.QApplication")
    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    @patch("deadline.max_submitter.create_job_bundle.max_utils.get_scene_path")
    def test_creates_progress_dialog_for_batch(
        self,
        mock_get_scene_path,
        mock_get_render_elements,
        mock_get_batch_views,
        mock_qapp,
        mock_progress_dialog,
        mock_settings,
        sample_state_set,
        sample_batch_view,
    ):
        """Verify progress dialog is created when processing batch views."""
        from deadline.max_submitter.create_job_bundle import _get_job_parameters

        mock_get_scene_path.return_value = "C:/scenes/test.max"
        mock_settings.batch_render_enabled = True
        mock_settings.batch_render.enabled_views = ["TestBatchView"]
        mock_get_batch_views.return_value = [sample_batch_view]
        mock_get_render_elements.return_value = []

        mock_progress = Mock()
        mock_progress_dialog.return_value = mock_progress

        _get_job_parameters(mock_settings, [sample_state_set])

        # Verify progress dialog was created and shown
        mock_progress_dialog.assert_called_once()
        mock_progress.show.assert_called_once()
        mock_progress.close.assert_called_once()

    @patch("deadline.max_submitter.create_job_bundle.get_batch_render_views")
    @patch("deadline.max_submitter.create_job_bundle.get_render_elements")
    @patch("deadline.max_submitter.create_job_bundle.max_utils.get_scene_path")
    def test_camera_param_not_added_for_all_cameras(
        self,
        mock_get_scene_path,
        mock_get_render_elements,
        mock_get_batch_views,
        mock_settings,
        sample_state_set,
    ):
        """Verify Camera parameter is NOT added when all cameras are selected."""
        from deadline.max_submitter.create_job_bundle import _get_job_parameters
        from deadline.max_submitter.data_const import ALL_CAMERAS_STR

        mock_get_scene_path.return_value = "C:/scenes/test.max"
        mock_get_batch_views.return_value = []
        mock_get_render_elements.return_value = []
        mock_settings.camera_selection = ALL_CAMERAS_STR

        result = _get_job_parameters(mock_settings, [sample_state_set])

        param_names = [p["name"] for p in result]
        assert "Camera" not in param_names
