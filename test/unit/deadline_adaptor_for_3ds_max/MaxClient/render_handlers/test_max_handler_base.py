# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations
from unittest.mock import patch, Mock

import pytest
from deadline.max_adaptor.MaxClient.render_handlers import DefaultMaxHandler
from deadline.max_adaptor.MaxClient.render_handlers.default_max_handler import (
    BatchRenderViewApplier,
)
from deadline.max_adaptor.MaxClient.render_element_manager import RenderElementResult
from deadline.max_adaptor.executable_handler import MaxExecutableHandler
from deadline.max_shared.utilities.max_utils import BatchRenderView


@pytest.fixture
def maxhandlerbase():
    return DefaultMaxHandler()


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


class TestDefaultMaxHandler:
    @pytest.mark.parametrize("args", [{"output_file_path": "C:/Users/Sandie/Desktop"}])
    def test_set_output_file_path(self, maxhandlerbase: DefaultMaxHandler, args: dict):
        """Tests that setting the image height calls the correct functions"""
        # WHEN
        maxhandlerbase.set_output_file_path(args)

        # THEN
        assert maxhandlerbase.output_dir == args["output_file_path"]

    @pytest.mark.parametrize("args", [{"output_file_name": "Output__#####"}])
    def test_set_output_file_name(self, maxhandlerbase: DefaultMaxHandler, args: dict):
        """Tests that setting the image height calls the correct functions"""
        # WHEN
        maxhandlerbase.set_output_file_name(args)

        # THEN
        assert maxhandlerbase.output_name == args["output_file_name"]

    @pytest.mark.parametrize("args", [{"output_file_format": ".png"}])
    def test_set_output_file_format(self, maxhandlerbase: DefaultMaxHandler, args: dict):
        """Tests that setting the image height calls the correct functions"""
        # WHEN
        maxhandlerbase.set_output_file_format(args)

        # THEN
        assert maxhandlerbase.output_format == args["output_file_format"]

    @patch("deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.rt")
    @patch.object(MaxExecutableHandler, "is_executable_type")
    def test_log_to_console(
        self,
        mock_executable_handler: Mock,
        mock_rt: Mock,
        maxhandlerbase: DefaultMaxHandler,
        capsys: pytest.CaptureFixture,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_executable_handler.return_value = False
        test_message_3dsmax: str = "3dsmax test message"

        maxhandlerbase.log_to_console(test_message_3dsmax)

        captured_result = capsys.readouterr()
        assert captured_result.out == f"{test_message_3dsmax}\n"
        assert mock_rt.logsystem.logEntry.called

        mock_executable_handler.return_value = True
        test_message_3dsmaxbatch: str = "3dsmaxbatch test message"

        maxhandlerbase.log_to_console(test_message_3dsmaxbatch)

        captured_result = capsys.readouterr()
        assert test_message_3dsmaxbatch in captured_result.out

    @patch("deadline.max_adaptor.MaxClient.render_element_manager.RenderElementManager")
    def test_configure_render_elements_success(
        self, mock_render_element_manager_class: Mock, maxhandlerbase: DefaultMaxHandler
    ):
        """Tests that configure_render_elements works correctly with render element manager"""
        # GIVEN
        mock_render_element_manager = Mock()
        mock_render_element_manager.configure_render_elements.return_value = RenderElementResult(
            success=True,
            message="Success",
        )
        mock_render_element_manager_class.return_value = mock_render_element_manager

        data = {"RenderElements": "true"}

        # WHEN
        maxhandlerbase.configure_render_elements(data)

        # THEN
        mock_render_element_manager.configure_render_elements.assert_called_once_with(data)
        assert maxhandlerbase.render_element_manager == mock_render_element_manager

    @patch("deadline.max_adaptor.MaxClient.render_element_manager.RenderElementManager")
    def test_configure_render_elements_failure(
        self, mock_render_element_manager_class: Mock, maxhandlerbase: DefaultMaxHandler
    ):
        """Tests that configure_render_elements handles failure correctly"""
        # GIVEN
        mock_render_element_manager = Mock()
        mock_render_element_manager.configure_render_elements.return_value = RenderElementResult(
            success=False,
            error="Test error",
        )
        mock_render_element_manager_class.return_value = mock_render_element_manager

        data = {"RenderElements": "true"}

        # WHEN/THEN
        with pytest.raises(RuntimeError, match="Render elements configuration failed: Test error"):
            maxhandlerbase.configure_render_elements(data)

    def test_cleanup_render_elements_no_manager(self, maxhandlerbase: DefaultMaxHandler):
        """Tests that cleanup_render_elements handles missing render element manager gracefully"""
        # GIVEN
        data = {"RenderElements": "true"}

        # WHEN/THEN - Should not raise exception
        maxhandlerbase.cleanup_render_elements(data)

    @pytest.mark.parametrize(
        "name,number,expected",
        [
            # With hash padding — zero-padded frame number replaces hashes
            ("output_#####", 1, "output_00001"),
            ("output_####", 42, "output_0042"),
            ("output_###", 100, "output_100"),
            # No hashes — return name as-is (single-frame, no numbering needed)
            ("output", 0, "output"),
            ("output", 7, "output"),
        ],
    )
    def test_reformat_framenumber_padding(
        self, maxhandlerbase: DefaultMaxHandler, name: str, number: int, expected: str
    ) -> None:
        assert maxhandlerbase.reformat_framenumber_padding(name, number) == expected

    def test_cleanup_render_elements_not_configured(self, maxhandlerbase: DefaultMaxHandler):
        """Tests that cleanup_render_elements handles unconfigured render elements gracefully"""
        # GIVEN
        mock_render_element_manager = Mock()
        mock_render_element_manager.has_render_elements_configured.return_value = False
        maxhandlerbase.render_element_manager = mock_render_element_manager

        data = {"RenderElements": "true"}

        # WHEN/THEN - Should not raise exception
        maxhandlerbase.cleanup_render_elements(data)

    def test_cleanup_render_elements_success(self, maxhandlerbase: DefaultMaxHandler):
        """Tests that cleanup_render_elements calls render element manager correctly"""
        # GIVEN
        mock_render_element_manager = Mock()
        mock_render_element_manager.has_render_elements_configured.return_value = True
        mock_render_element_manager.restore_render_elements.return_value = RenderElementResult(
            success=True,
            message="Restored",
        )
        maxhandlerbase.render_element_manager = mock_render_element_manager

        data = {"RenderElements": "true"}

        # WHEN
        maxhandlerbase.cleanup_render_elements(data)

        # THEN
        mock_render_element_manager.restore_render_elements.assert_called_once()


class TestBatchRender:
    """Tests for batch rendering functionality in DefaultMaxHandler and BatchRenderViewApplier."""

    class TestApplyBatchView:
        """Tests for DefaultMaxHandler.apply_batch_render_view method."""

        @pytest.fixture(autouse=True)
        def mock_applier(self, maxhandlerbase: DefaultMaxHandler):
            """Mock the batch render view applier for all tests in this class."""
            with patch.object(maxhandlerbase, "_batch_render_view_applier") as mock:
                yield mock

        def test_action_dict_contains_batch_render_view(self, maxhandlerbase: DefaultMaxHandler):
            """Verify batch_render_view is registered in the action_dict."""
            assert "batch_render_view" in maxhandlerbase.action_dict
            assert (
                maxhandlerbase.action_dict["batch_render_view"]
                == maxhandlerbase.apply_batch_render_view
            )

        def test_stores_name_and_calls_applier(
            self, maxhandlerbase: DefaultMaxHandler, mock_applier: Mock
        ):
            """Verify apply_batch_render_view stores the name and delegates to BatchRenderViewApplier."""
            maxhandlerbase.apply_batch_render_view({"batch_render_view": "TestView"})
            assert maxhandlerbase.batch_render_view == "TestView"
            mock_applier.apply.assert_called_once_with("TestView")

        @pytest.mark.parametrize("data", [{}, {"batch_render_view": ""}])
        def test_raises_with_missing_or_empty_name(
            self, maxhandlerbase: DefaultMaxHandler, data: dict
        ):
            """Verify apply_batch_render_view raises RuntimeError when batch_render_view is missing or empty."""
            with pytest.raises(
                RuntimeError, match="batch_render_view action called without a view name"
            ):
                maxhandlerbase.apply_batch_render_view(data)

    class TestStartRender:
        """Tests for start_render with batch_render_view in output filename."""

        @pytest.fixture(autouse=True)
        def mock_rt(self):
            """Mock the pymxs runtime for all tests in this class."""
            with patch(
                "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.rt"
            ) as mock:
                yield mock

        @pytest.fixture(autouse=True)
        def mock_os_path_exists(self):
            """Mock os.path.exists for all tests in this class."""
            with patch(
                "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.os.path.exists"
            ) as mock:
                mock.return_value = True
                yield mock

        @pytest.fixture(autouse=True)
        def mock_os_makedirs(self):
            """Mock os.makedirs for all tests in this class."""
            with patch(
                "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.os.makedirs"
            ) as mock:
                yield mock

        @pytest.fixture(autouse=True)
        def mock_os_remove(self):
            """Mock os.remove for all tests in this class."""
            with patch(
                "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.os.remove"
            ) as mock:
                yield mock

        @pytest.mark.parametrize(
            "batch_render_view,output_pattern,run_data,expected_in_output,not_expected_in_output",
            [
                ("BatchView1", "render_####", {"frame": 10}, ["BatchView1"], []),
                (None, "render_####", {"frame": 10}, [], ["BatchView1"]),
                (
                    "BatchView1",
                    "<camera>_render_####",
                    {"frame": 10, "camera": "Camera001"},
                    ["BatchView1", "Camera001"],
                    [],
                ),
            ],
            ids=["with_batch_view", "without_batch_view", "with_batch_view_and_camera"],
        )
        def test_output_filename_composition(
            self,
            maxhandlerbase: DefaultMaxHandler,
            mock_rt: Mock,
            batch_render_view: str,
            output_pattern: str,
            run_data: dict,
            expected_in_output: list,
            not_expected_in_output: list,
        ):
            """Verify output filename includes correct components based on batch_render_view and camera."""
            maxhandlerbase.output_dir = "/output"
            maxhandlerbase.output_name = output_pattern
            maxhandlerbase.output_format = ".png"
            maxhandlerbase.batch_render_view = batch_render_view

            if "camera" in run_data:
                maxhandlerbase.camera_node = None
                # Create a mock camera with proper name attribute
                mock_camera = Mock()
                mock_camera.name = "Camera001"
                mock_rt.cameras = [mock_camera]
                mock_rt.getNodeByName.return_value = Mock()
            else:
                maxhandlerbase.camera_node = Mock()

            maxhandlerbase.start_render(run_data)

            mock_rt.render.assert_called_once()
            call_kwargs = mock_rt.render.call_args[1]
            for expected in expected_in_output:
                assert expected in call_kwargs["outputFile"]
            for not_expected in not_expected_in_output:
                assert not_expected not in call_kwargs["outputFile"]

    class TestBatchRenderViewApplier:
        """Tests for BatchRenderViewApplier class."""

        @pytest.fixture(autouse=True)
        def mock_rt(self):
            """Mock the pymxs runtime for all tests in this class."""
            with patch(
                "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.rt"
            ) as mock:
                yield mock

        @patch(
            "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.get_batch_render_view_by_name"
        )
        def test_apply_calls_methods_conditionally(
            self, mock_get_batch_view: Mock, sample_batch_view: BatchRenderView
        ):
            """Verify apply calls configuration methods only when batch render view has values."""
            mock_get_batch_view.return_value = sample_batch_view
            applier = BatchRenderViewApplier()

            with (
                patch.object(applier, "_apply_camera") as mock_camera,
                patch.object(applier, "_apply_scene_state") as mock_scene_state,
                patch.object(applier, "_load_preset") as mock_preset,
                patch.object(applier, "_apply_resolution_override") as mock_resolution,
            ):
                applier.apply("TestBatchView")

                mock_get_batch_view.assert_called_once_with("TestBatchView")
                mock_camera.assert_called_once_with(sample_batch_view)
                mock_scene_state.assert_called_once_with(sample_batch_view)
                mock_preset.assert_called_once_with(sample_batch_view)
                mock_resolution.assert_called_once_with(sample_batch_view)

        @patch(
            "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.get_batch_render_view_by_name"
        )
        def test_apply_skips_methods_when_no_values(self, mock_get_batch_view: Mock):
            """Verify apply skips configuration methods when batch render view has no values."""
            empty_batch_view = BatchRenderView(name="Empty")
            mock_get_batch_view.return_value = empty_batch_view
            applier = BatchRenderViewApplier()

            with (
                patch.object(applier, "_apply_camera") as mock_camera,
                patch.object(applier, "_apply_scene_state") as mock_scene_state,
                patch.object(applier, "_load_preset") as mock_preset,
                patch.object(applier, "_apply_resolution_override") as mock_resolution,
            ):
                applier.apply("Empty")

                mock_camera.assert_not_called()
                mock_scene_state.assert_not_called()
                mock_preset.assert_not_called()
                mock_resolution.assert_not_called()

        class TestApplyCamera:
            """Tests for BatchRenderViewApplier._apply_camera method."""

            def test_sets_camera_node(self, mock_rt: Mock):
                """Verify camera is set via callback when specified."""
                camera_callback = Mock()
                applier = BatchRenderViewApplier(set_camera_callback=camera_callback)
                mock_camera_node = Mock()
                mock_rt.getNodeByName.return_value = mock_camera_node
                mock_rt.isKindOf.return_value = True

                applier._apply_camera(BatchRenderView(name="Test", camera="Camera001"))

                mock_rt.getNodeByName.assert_called_once_with("Camera001")
                camera_callback.assert_called_once_with(mock_camera_node)

            def test_raises_when_camera_not_found(self, mock_rt: Mock):
                """Verify RuntimeError when camera doesn't exist in scene."""
                applier = BatchRenderViewApplier()
                mock_rt.getNodeByName.return_value = None

                with pytest.raises(RuntimeError, match="Camera 'NonExistent' does not exist"):
                    applier._apply_camera(BatchRenderView(name="Test", camera="NonExistent"))

            def test_raises_when_not_camera_type(self, mock_rt: Mock):
                """Verify RuntimeError when object is not a camera."""
                applier = BatchRenderViewApplier()
                mock_rt.getNodeByName.return_value = Mock()
                mock_rt.isKindOf.return_value = False

                with pytest.raises(RuntimeError, match="Object 'NotACamera' is not a camera"):
                    applier._apply_camera(BatchRenderView(name="Test", camera="NotACamera"))

        class TestApplySceneState:
            """Tests for BatchRenderViewApplier._apply_scene_state method."""

            def test_restores_state(self, mock_rt: Mock):
                """Verify scene state is restored when specified."""
                applier = BatchRenderViewApplier()
                mock_scene_state_mgr = Mock()
                mock_scene_state_mgr.FindSceneState.return_value = 1  # Found at index 1
                mock_scene_state_mgr.RestoreAllParts.return_value = True
                mock_rt.sceneStateMgr = mock_scene_state_mgr

                applier._apply_scene_state(BatchRenderView(name="Test", scene_state="State2"))

                mock_scene_state_mgr.FindSceneState.assert_called_once_with("State2")
                mock_scene_state_mgr.RestoreAllParts.assert_called_once_with("State2")

            def test_raises_when_state_not_found(self, mock_rt: Mock):
                """Verify RuntimeError when scene state doesn't exist."""
                applier = BatchRenderViewApplier()
                mock_scene_state_mgr = Mock()
                mock_scene_state_mgr.FindSceneState.return_value = -1  # Not found
                mock_rt.sceneStateMgr = mock_scene_state_mgr

                with pytest.raises(RuntimeError, match="Scene State 'NonExistent' does not exist"):
                    applier._apply_scene_state(
                        BatchRenderView(name="Test", scene_state="NonExistent")
                    )

            def test_raises_when_restore_fails(self, mock_rt: Mock):
                """Verify RuntimeError when RestoreAllParts returns False."""
                applier = BatchRenderViewApplier()
                mock_scene_state_mgr = Mock()
                mock_scene_state_mgr.FindSceneState.return_value = 0
                mock_scene_state_mgr.RestoreAllParts.return_value = False
                mock_rt.sceneStateMgr = mock_scene_state_mgr

                with pytest.raises(RuntimeError, match="Failed to restore scene state 'FailState'"):
                    applier._apply_scene_state(
                        BatchRenderView(name="Test", scene_state="FailState")
                    )

        class TestLoadPreset:
            """Tests for BatchRenderViewApplier._load_preset method."""

            @patch(
                "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.os.path.exists"
            )
            def test_loads_file(self, mock_exists: Mock, mock_rt: Mock):
                """Verify preset file is loaded when specified."""
                applier = BatchRenderViewApplier()
                mock_exists.return_value = True
                mock_rt.renderPresets.LoadAll.return_value = True

                applier._load_preset(
                    BatchRenderView(name="Test", preset_file="C:/presets/render.rps")
                )

                mock_rt.renderPresets.LoadAll.assert_called_once_with(0, "C:/presets/render.rps")

            @patch(
                "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.os.path.exists"
            )
            def test_applies_path_mapping(self, mock_exists: Mock, mock_rt: Mock):
                """Verify path mapping is applied to preset file path."""
                map_path = Mock(return_value="/mapped/path/render.rps")
                applier = BatchRenderViewApplier(map_path=map_path)
                mock_exists.return_value = True
                mock_rt.renderPresets.LoadAll.return_value = True

                applier._load_preset(
                    BatchRenderView(name="Test", preset_file="C:/presets/render.rps")
                )

                map_path.assert_called_once_with("C:/presets/render.rps")
                mock_rt.renderPresets.LoadAll.assert_called_once_with(0, "/mapped/path/render.rps")

            @patch(
                "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.os.path.exists"
            )
            def test_raises_when_file_not_found(self, mock_exists: Mock):
                """Verify RuntimeError when preset file doesn't exist."""
                applier = BatchRenderViewApplier()
                mock_exists.return_value = False

                with pytest.raises(RuntimeError, match="Preset file .* does not exist"):
                    applier._load_preset(BatchRenderView(name="Test", preset_file="C:/missing.rps"))

            @patch(
                "deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.os.path.exists"
            )
            def test_raises_when_load_fails(self, mock_exists: Mock, mock_rt: Mock):
                """Verify RuntimeError when preset loading fails."""
                applier = BatchRenderViewApplier()
                mock_exists.return_value = True
                mock_rt.renderPresets.LoadAll.return_value = False

                with pytest.raises(RuntimeError, match="Failed to load preset file"):
                    applier._load_preset(BatchRenderView(name="Test", preset_file="C:/bad.rps"))

        class TestApplyResolutionOverride:
            """Tests for BatchRenderViewApplier._apply_resolution_override method."""

            def test_sets_all_values(self, mock_rt: Mock):
                """Verify all resolution values are set when override is enabled."""
                applier = BatchRenderViewApplier()

                applier._apply_resolution_override(
                    BatchRenderView(
                        name="Test", override_preset=True, width=1920, height=1080, pixel_aspect=1.5
                    )
                )

                assert mock_rt.renderWidth == 1920
                assert mock_rt.renderHeight == 1080
                assert mock_rt.renderPixelAspect == 1.5

            @pytest.mark.parametrize(
                "expected_attrs",
                [
                    {"renderWidth": 1920},
                    {"renderHeight": 1080},
                    {"renderPixelAspect": 1.5},
                    {"renderWidth": 1920, "renderHeight": 1080},
                ],
                ids=["width_only", "height_only", "pixel_aspect_only", "width_and_height"],
            )
            def test_sets_partial_values(self, mock_rt: Mock, expected_attrs):
                """Verify only provided values are set and others remain unchanged."""
                applier = BatchRenderViewApplier()

                # Set default values
                defaults = {"renderWidth": 100, "renderHeight": 100, "renderPixelAspect": 1.0}
                for attr, value in defaults.items():
                    setattr(mock_rt, attr, value)

                applier._apply_resolution_override(
                    BatchRenderView(
                        name="Test",
                        override_preset=True,
                        width=expected_attrs.get("renderWidth"),
                        height=expected_attrs.get("renderHeight"),
                        pixel_aspect=expected_attrs.get("renderPixelAspect"),
                    )
                )

                # Verify expected values were set
                for attr, value in expected_attrs.items():
                    assert getattr(mock_rt, attr) == value

                # Verify unchanged values remain at defaults
                for attr in defaults.keys() - expected_attrs.keys():
                    assert getattr(mock_rt, attr) == defaults[attr]

            def test_raises_on_invalid_width(self, mock_rt: Mock):
                """Verify RuntimeError when width is invalid."""
                applier = BatchRenderViewApplier()

                with pytest.raises(RuntimeError, match="Invalid width override"):
                    applier._apply_resolution_override(
                        BatchRenderView(name="Test", override_preset=True, width=0)
                    )

            def test_raises_on_invalid_height(self, mock_rt: Mock):
                """Verify RuntimeError when height is invalid."""
                applier = BatchRenderViewApplier()

                with pytest.raises(RuntimeError, match="Invalid height override"):
                    applier._apply_resolution_override(
                        BatchRenderView(name="Test", override_preset=True, height=-100)
                    )

            def test_raises_on_invalid_pixel_aspect(self, mock_rt: Mock):
                """Verify RuntimeError when pixel_aspect is invalid."""
                applier = BatchRenderViewApplier()

                with pytest.raises(RuntimeError, match="Invalid pixel aspect override"):
                    applier._apply_resolution_override(
                        BatchRenderView(name="Test", override_preset=True, pixel_aspect=-1.0)
                    )
