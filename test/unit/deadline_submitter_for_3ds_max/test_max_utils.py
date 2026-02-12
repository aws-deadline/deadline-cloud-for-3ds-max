# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Any
from unittest.mock import patch, MagicMock
import pytest


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
