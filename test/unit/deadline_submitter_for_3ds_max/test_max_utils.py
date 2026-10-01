# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Any
from unittest.mock import patch, Mock, MagicMock

import pytest

from deadline.max_submitter.utilities.max_utils import get_render_output_info


class TestGetReferencedFilesFiltering:
    """Tests for output asset filtering in get_referenced_files()."""

    @pytest.fixture
    def mock_pymxs(self):
        """Mock pymxs module and runtime."""
        with patch.dict("sys.modules", {"pymxs": MagicMock()}):
            import sys

            mock_pymxs = sys.modules["pymxs"]
            mock_pymxs.byref = MagicMock(return_value=None)  # type: ignore[attr-defined]
            yield mock_pymxs

    @pytest.fixture
    def mock_rt(self, mock_pymxs):
        """Mock the pymxs runtime."""
        with patch("deadline.max_submitter.utilities.max_utils.rt") as mock_rt:
            # Default: no nested files
            mock_rt.ATSOps.GetDependentFiles.return_value = (0, None)
            mock_rt.maxFilePath = "C:/scenes/"
            mock_rt.maxFileName = "test.max"
            yield mock_rt

    @pytest.fixture
    def mock_asset_manager(self, mock_rt):
        """Setup AssetManager mock with configurable asset types."""

        def create_asset(asset_type: str) -> MagicMock:
            asset = MagicMock()
            asset.getType.return_value = asset_type
            return asset

        asset_map: dict[str, Any] = {}

        def get_asset_id(path):
            return path

        def get_asset(asset_id):
            return asset_map.get(asset_id, create_asset("#Bitmap"))

        mock_rt.AssetManager.getAssetId = get_asset_id
        mock_rt.AssetManager.getAsset = get_asset

        return asset_map, create_asset

    def test_excludes_render_output_assets(self, mock_pymxs, mock_rt, mock_asset_manager):
        """Verify that #RenderOutput type assets are excluded."""
        asset_map, create_asset = mock_asset_manager

        # Setup files: one texture, one render output
        files = ["C:\\textures\\diffuse.jpg", "C:\\output\\render.png"]
        mock_rt.ATSOps.GetFiles.return_value = (2, files)

        asset_map["C:\\textures\\diffuse.jpg"] = create_asset("#Bitmap")
        asset_map["C:\\output\\render.png"] = create_asset("#RenderOutput")

        from deadline.max_submitter.utilities.max_utils import get_referenced_files

        result = get_referenced_files()

        assert "C:/textures/diffuse.jpg" in result
        assert "C:/output/render.png" not in result

    def test_excludes_video_post_assets(self, mock_pymxs, mock_rt, mock_asset_manager):
        """Verify that #VideoPost type assets are excluded."""
        asset_map, create_asset = mock_asset_manager

        files = ["C:\\textures\\diffuse.jpg", "C:\\videopost\\output.avi"]
        mock_rt.ATSOps.GetFiles.return_value = (2, files)

        asset_map["C:\\textures\\diffuse.jpg"] = create_asset("#Bitmap")
        asset_map["C:\\videopost\\output.avi"] = create_asset("#VideoPost")

        from deadline.max_submitter.utilities.max_utils import get_referenced_files

        result = get_referenced_files()

        assert "C:/textures/diffuse.jpg" in result
        assert "C:/videopost/output.avi" not in result

    def test_includes_bitmap_assets(self, mock_pymxs, mock_rt, mock_asset_manager):
        """Verify that #Bitmap type assets are included."""
        asset_map, create_asset = mock_asset_manager

        files = ["C:\\textures\\diffuse.jpg", "C:\\textures\\normal.png", "C:\\textures\\spec.exr"]
        mock_rt.ATSOps.GetFiles.return_value = (3, files)

        for f in files:
            asset_map[f] = create_asset("#Bitmap")

        from deadline.max_submitter.utilities.max_utils import get_referenced_files

        result = get_referenced_files()

        assert len(result) == 3
        assert "C:/textures/diffuse.jpg" in result
        assert "C:/textures/normal.png" in result
        assert "C:/textures/spec.exr" in result

    def test_includes_xref_assets(self, mock_pymxs, mock_rt, mock_asset_manager):
        """Verify that #XRef type assets are included."""
        asset_map, create_asset = mock_asset_manager

        files = ["C:\\xrefs\\model.max", "C:\\xrefs\\scene.max"]
        mock_rt.ATSOps.GetFiles.return_value = (2, files)

        for f in files:
            asset_map[f] = create_asset("#XRef")

        from deadline.max_submitter.utilities.max_utils import get_referenced_files

        result = get_referenced_files()

        assert len(result) == 2
        assert "C:/xrefs/model.max" in result
        assert "C:/xrefs/scene.max" in result

    def test_includes_photometric_assets(self, mock_pymxs, mock_rt, mock_asset_manager):
        """Verify that #Photometric (IES) type assets are included."""
        asset_map, create_asset = mock_asset_manager

        files = ["C:\\lights\\spot.ies"]
        mock_rt.ATSOps.GetFiles.return_value = (1, files)

        asset_map["C:\\lights\\spot.ies"] = create_asset("#Photometric")

        from deadline.max_submitter.utilities.max_utils import get_referenced_files

        result = get_referenced_files()

        assert "C:/lights/spot.ies" in result

    def test_handles_asset_manager_exception(self, mock_pymxs, mock_rt):
        """Verify graceful handling when AssetManager fails - file should be included."""
        files = ["C:\\textures\\diffuse.jpg"]
        mock_rt.ATSOps.GetFiles.return_value = (1, files)

        # Make AssetManager raise an exception
        mock_rt.AssetManager.getAssetId.side_effect = Exception("Asset not found")

        from deadline.max_submitter.utilities.max_utils import get_referenced_files

        result = get_referenced_files()

        # File should still be included (fail-open behavior)
        assert "C:/textures/diffuse.jpg" in result

    def test_mixed_asset_types(self, mock_pymxs, mock_rt, mock_asset_manager):
        """Verify correct filtering with mixed input and output asset types."""
        asset_map, create_asset = mock_asset_manager

        files = [
            "C:\\textures\\diffuse.jpg",  # Bitmap - include
            "C:\\output\\render.png",  # RenderOutput - exclude
            "C:\\xrefs\\model.max",  # XRef - include
            "C:\\videopost\\out.avi",  # VideoPost - exclude
            "C:\\lights\\spot.ies",  # Photometric - include
            "C:\\output\\element_ao.exr",  # RenderOutput - exclude
        ]
        mock_rt.ATSOps.GetFiles.return_value = (6, files)

        asset_map["C:\\textures\\diffuse.jpg"] = create_asset("#Bitmap")
        asset_map["C:\\output\\render.png"] = create_asset("#RenderOutput")
        asset_map["C:\\xrefs\\model.max"] = create_asset("#XRef")
        asset_map["C:\\videopost\\out.avi"] = create_asset("#VideoPost")
        asset_map["C:\\lights\\spot.ies"] = create_asset("#Photometric")
        asset_map["C:\\output\\element_ao.exr"] = create_asset("#RenderOutput")

        from deadline.max_submitter.utilities.max_utils import get_referenced_files

        result = get_referenced_files()

        assert len(result) == 3
        assert "C:/textures/diffuse.jpg" in result
        assert "C:/xrefs/model.max" in result
        assert "C:/lights/spot.ies" in result
        assert "C:/output/render.png" not in result
        assert "C:/videopost/out.avi" not in result
        assert "C:/output/element_ao.exr" not in result


class TestGetRenderOutputInfo:
    """Tests for get_render_output_info() — Path-based decomposition of render output."""

    @pytest.fixture(autouse=True)
    def mock_rt(self):
        with patch("deadline.max_submitter.utilities.max_utils.rt") as mock_rt:
            # Set default to None so truthiness check works correctly
            mock_rt.rendOutputFilename = None
            yield mock_rt

    def test_returns_path_stem_suffix(self, mock_rt):
        """Standard render output is decomposed into parent, stem, suffix."""
        # Use forward slashes for cross-platform compatibility
        mock_rt.rendOutputFilename = "C:/output/render_###.png"

        output_dir, output_name, output_ext = get_render_output_info()

        assert output_dir == "C:/output"
        assert output_name == "render_###"
        assert output_ext == ".png"

    def test_forward_slash_path(self, mock_rt):
        mock_rt.rendOutputFilename = "C:/output/myScene_###.exr"

        output_dir, output_name, output_ext = get_render_output_info()

        assert output_name == "myScene_###"
        assert output_ext == ".exr"

    def test_no_extension(self, mock_rt):
        """Test path without extension."""
        # Use forward slashes for cross-platform compatibility
        mock_rt.rendOutputFilename = "C:/output/render_###"

        output_dir, output_name, output_ext = get_render_output_info()

        assert output_name == "render_###"
        assert output_ext == ""

    def test_empty_output_falls_back_to_scene(self, mock_rt):
        """When rendOutputFilename is empty, fall back to scene-based defaults."""
        mock_rt.rendOutputFilename = ""
        mock_rt.maxFilePath = "C:\\scenes\\"
        mock_rt.maxFileName = "myScene.max"

        output_dir, output_name, output_ext = get_render_output_info()

        assert output_dir == "C:/scenes/"
        assert output_name == "myScene_###"
        assert output_ext == ""

    def test_none_output_falls_back_to_scene(self, mock_rt):
        """When rendOutputFilename is None/falsy, fall back to scene-based defaults."""
        mock_rt.rendOutputFilename = None
        mock_rt.maxFilePath = "C:\\scenes\\"
        mock_rt.maxFileName = "testStudio.max"

        output_dir, output_name, output_ext = get_render_output_info()

        assert output_dir == "C:/scenes/"
        assert output_name == "testStudio_###"
        assert output_ext == ""


class TestHoldAndFetchScene:
    """Tests for hold_and_fetch_scene context manager."""

    @pytest.fixture(autouse=True)
    def mock_rt(self):
        """Mock pymxs runtime for all tests."""
        with patch("deadline.max_submitter.utilities.max_utils.rt") as mock:
            mock.execute.return_value = "C:/temp"
            yield mock

    @pytest.fixture(autouse=True)
    def mock_submission_utils(self):
        """Mock submission_utils for all tests."""
        with patch("deadline.max_submitter.utilities.max_utils.submission_utils") as mock:
            mock.save_max_backup_file.return_value = "undefined"
            mock.restore_max_copy.return_value = "undefined"
            yield mock

    def test_holds_scene_on_entry(self, mock_rt, mock_submission_utils):
        """Verify scene is held when entering context."""
        from deadline.max_submitter.utilities.max_utils import hold_and_fetch_scene

        with hold_and_fetch_scene():
            pass

        mock_submission_utils.save_max_backup_file.assert_called_once()
        call_args = mock_submission_utils.save_max_backup_file.call_args
        assert call_args[1]["use_max_hold"] is True

    def test_fetches_scene_on_exit(self, mock_rt, mock_submission_utils):
        """Verify scene is restored when exiting context."""
        from deadline.max_submitter.utilities.max_utils import hold_and_fetch_scene

        with hold_and_fetch_scene():
            pass

        mock_submission_utils.restore_max_copy.assert_called_once()

    def test_fetches_scene_on_exception(self, mock_rt, mock_submission_utils):
        """Verify scene is restored even when exception occurs."""
        from deadline.max_submitter.utilities.max_utils import hold_and_fetch_scene

        with pytest.raises(ValueError):
            with hold_and_fetch_scene():
                raise ValueError("Test error")

        # Should still restore
        mock_submission_utils.restore_max_copy.assert_called_once()

    def test_raises_on_hold_failure(self, mock_rt, mock_submission_utils):
        """Verify RuntimeError is raised when hold fails."""
        from deadline.max_submitter.utilities.max_utils import hold_and_fetch_scene

        mock_submission_utils.save_max_backup_file.return_value = "Error: Failed to save"

        with pytest.raises(RuntimeError, match="Failed to hold scene"):
            with hold_and_fetch_scene():
                pass


class TestExtractSettingsFromPreset:
    """Tests for extract_settings_from_preset function."""

    @pytest.fixture(autouse=True)
    def mock_rt(self):
        """Mock pymxs runtime for all tests."""
        with patch("deadline.max_submitter.utilities.max_utils.rt") as mock:
            mock.execute.return_value = "C:/temp"
            mock.renderPresets.LoadAll.return_value = True
            mock.rendTimeType = 3  # User chosen range
            mock.rendStart = 1
            mock.rendEnd = 100
            mock.renderWidth = 1920
            mock.renderHeight = 1080
            mock.sliderTime = 1
            mock.animationRange.start = 0
            mock.animationRange.end = 250
            mock.rendPickupFrames = "1,5,10-20"
            yield mock

    @pytest.fixture(autouse=True)
    def mock_hold_and_fetch(self):
        """Mock hold_and_fetch_scene context manager."""
        with patch("deadline.max_submitter.utilities.max_utils.hold_and_fetch_scene") as mock:
            mock.return_value.__enter__ = Mock()
            mock.return_value.__exit__ = Mock(return_value=False)
            yield mock

    @pytest.fixture(autouse=True)
    def mock_os_path_exists(self):
        """Mock os.path.exists to return True by default."""
        with patch("deadline.max_submitter.utilities.max_utils.os.path.exists") as mock:
            mock.return_value = True
            yield mock

    def test_returns_empty_when_file_not_exists(self, mock_os_path_exists):
        """Verify empty settings returned when preset file doesn't exist."""
        from deadline.max_submitter.utilities.max_utils import extract_settings_from_preset

        mock_os_path_exists.return_value = False

        result = extract_settings_from_preset("C:/presets/nonexistent.rps")

        assert result["frame_range"] is None
        assert result["width"] is None
        assert result["height"] is None

    def test_extracts_single_frame(self, mock_rt):
        """Verify frame range extraction for rendTimeType=1 (single frame)."""
        from deadline.max_submitter.utilities.max_utils import extract_settings_from_preset

        mock_rt.rendTimeType = 1
        mock_rt.sliderTime = 42

        result = extract_settings_from_preset("C:/presets/render.rps")

        assert result["frame_range"] == "42"

    def test_extracts_active_time_segment(self, mock_rt):
        """Verify frame range extraction for rendTimeType=2 (active time segment)."""
        from deadline.max_submitter.utilities.max_utils import extract_settings_from_preset

        mock_rt.rendTimeType = 2
        mock_rt.animationRange.start = 10
        mock_rt.animationRange.end = 200

        result = extract_settings_from_preset("C:/presets/render.rps")

        assert result["frame_range"] == "10-200"

    def test_extracts_user_chosen_range(self, mock_rt):
        """Verify frame range extraction for rendTimeType=3 (user chosen range)."""
        from deadline.max_submitter.utilities.max_utils import extract_settings_from_preset

        mock_rt.rendTimeType = 3
        mock_rt.rendStart = 50
        mock_rt.rendEnd = 150

        result = extract_settings_from_preset("C:/presets/render.rps")

        assert result["frame_range"] == "50-150"

    def test_extracts_pickup_frames(self, mock_rt):
        """Verify frame range extraction for rendTimeType=4 (pick up frames)."""
        from deadline.max_submitter.utilities.max_utils import extract_settings_from_preset

        mock_rt.rendTimeType = 4
        mock_rt.rendPickupFrames = "1,3,5,10-20,30"

        result = extract_settings_from_preset("C:/presets/render.rps")

        assert result["frame_range"] == "1,3,5,10-20,30"

    def test_extracts_resolution(self, mock_rt):
        """Verify resolution extraction from preset."""
        from deadline.max_submitter.utilities.max_utils import extract_settings_from_preset

        mock_rt.renderWidth = 3840
        mock_rt.renderHeight = 2160

        result = extract_settings_from_preset("C:/presets/render.rps")

        assert result["width"] == 3840
        assert result["height"] == 2160

    def test_loads_preset_file(self, mock_rt):
        """Verify preset file is loaded via renderPresets.LoadAll."""
        from deadline.max_submitter.utilities.max_utils import extract_settings_from_preset

        extract_settings_from_preset("C:/presets/my_preset.rps")

        mock_rt.renderPresets.LoadAll.assert_called_once_with(0, "C:/presets/my_preset.rps")

    def test_unknown_rend_time_type_returns_empty_frame_range(self, mock_rt):
        """Verify empty frame range for unknown rendTimeType."""
        from deadline.max_submitter.utilities.max_utils import extract_settings_from_preset

        mock_rt.rendTimeType = 99  # Unknown type

        result = extract_settings_from_preset("C:/presets/render.rps")

        # Frame range should be None for unknown type, but resolution should still be extracted
        assert result["frame_range"] is None
        assert result["width"] == 1920
        assert result["height"] == 1080
