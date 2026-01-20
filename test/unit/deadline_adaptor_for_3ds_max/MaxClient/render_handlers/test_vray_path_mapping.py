# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest.mock import MagicMock, PropertyMock, patch

import pytest


class TestVrayProxyPathMapping:
    """Tests for VrayHandler path mapping functionality."""

    @patch.dict(
        "os.environ",
        {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        },
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_no_vray_proxy_class(self, mock_rt: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test graceful handling when VRayProxy class doesn't exist."""
        mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        handler = VrayHandler(gpu=False)
        handler.map_path = MagicMock(return_value="/mapped/path")

        del mock_rt.VRayProxy

        handler._apply_vray_proxy_path_mapping()

        captured = capsys.readouterr()
        assert "VRayProxy class not found" in captured.out

    @patch.dict(
        "os.environ",
        {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        },
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_no_proxies_in_scene(self, mock_rt: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test handling when no VRayProxy objects exist."""
        mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]
        mock_rt.objects = []
        mock_rt.VRayProxy = MagicMock()

        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        handler = VrayHandler(gpu=False)
        handler.map_path = MagicMock(return_value="/mapped/path")

        handler._apply_vray_proxy_path_mapping()

        handler.map_path.assert_not_called()

        captured = capsys.readouterr()
        assert "No VRayProxy objects found" in captured.out

    @patch.dict(
        "os.environ",
        {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        },
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_applies_path_mapping(self, mock_rt: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test that path mapping is correctly applied to VRayProxy objects."""
        mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

        mock_proxy = MagicMock()
        mock_proxy.name = "TreeProxy"
        mock_proxy.fileName = "C:/Assets/tree.vrmesh"

        mock_rt.objects = [mock_proxy]
        mock_rt.classOf.return_value = mock_rt.VRayProxy

        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        handler = VrayHandler(gpu=False)
        handler.map_path = MagicMock(return_value="/session/Assets/tree.vrmesh")

        handler._apply_vray_proxy_path_mapping()

        handler.map_path.assert_called_once_with("C:/Assets/tree.vrmesh")
        assert mock_proxy.fileName == "/session/Assets/tree.vrmesh"

        captured = capsys.readouterr()
        assert "Remapped VRayProxy 'TreeProxy'" in captured.out
        assert "1 proxies remapped" in captured.out

    @patch.dict(
        "os.environ",
        {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        },
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_skips_when_path_unchanged(
        self, mock_rt: MagicMock, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that proxy is not modified when path mapping returns same path."""
        mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

        mock_proxy = MagicMock()
        mock_proxy.name = "LocalProxy"
        mock_proxy.fileName = "/already/local/path.vrmesh"

        mock_rt.objects = [mock_proxy]
        mock_rt.classOf.return_value = mock_rt.VRayProxy

        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        handler = VrayHandler(gpu=False)
        handler.map_path = MagicMock(return_value="/already/local/path.vrmesh")

        handler._apply_vray_proxy_path_mapping()

        handler.map_path.assert_called_once_with("/already/local/path.vrmesh")

        captured = capsys.readouterr()
        assert "Remapped VRayProxy" not in captured.out
        assert "0 proxies remapped" in captured.out

    @patch.dict(
        "os.environ",
        {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        },
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_handles_mapping_failure(
        self, mock_rt: MagicMock, capsys: pytest.CaptureFixture
    ) -> None:
        """Test warning is printed when path mapping fails."""
        mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

        mock_proxy = MagicMock()
        mock_proxy.name = "BrokenProxy"
        original_filename = "C:/Assets/broken.vrmesh"

        type(mock_proxy).fileName = PropertyMock(
            side_effect=[original_filename, Exception("Access denied")]
        )

        mock_rt.objects = [mock_proxy]
        mock_rt.classOf.return_value = mock_rt.VRayProxy

        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        handler = VrayHandler(gpu=False)
        handler.map_path = MagicMock(return_value="/session/Assets/broken.vrmesh")

        handler._apply_vray_proxy_path_mapping()

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "BrokenProxy" in captured.out

    @patch.dict(
        "os.environ",
        {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        },
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_no_mapping_when_map_path_not_injected(self, mock_rt: MagicMock) -> None:
        """Test no path mapping when map_path function not injected."""
        mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

        mock_proxy = MagicMock()
        mock_proxy.name = "TreeProxy"
        mock_proxy.fileName = "C:/Assets/tree.vrmesh"

        mock_rt.objects = [mock_proxy]
        mock_rt.classOf.return_value = mock_rt.VRayProxy

        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        handler = VrayHandler(gpu=False)
        handler.map_path = None

        handler._apply_path_mapping()

        assert mock_proxy.fileName == "C:/Assets/tree.vrmesh"

    @patch.dict(
        "os.environ",
        {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        },
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_multiple_proxies(self, mock_rt: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test path mapping with multiple VRayProxy objects."""
        mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

        mock_proxy1 = MagicMock()
        mock_proxy1.name = "TreeProxy"
        mock_proxy1.fileName = "C:/Assets/tree.vrmesh"

        mock_proxy2 = MagicMock()
        mock_proxy2.name = "RockProxy"
        mock_proxy2.fileName = "C:/Assets/rock.vrmesh"

        mock_proxy3 = MagicMock()
        mock_proxy3.name = "LocalProxy"
        mock_proxy3.fileName = "/local/path.vrmesh"

        mock_rt.objects = [mock_proxy1, mock_proxy2, mock_proxy3]
        mock_rt.classOf.return_value = mock_rt.VRayProxy

        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        handler = VrayHandler(gpu=False)

        def mock_map_path(path: str) -> str:
            if path.startswith("C:/Assets/"):
                return path.replace("C:/Assets/", "/session/Assets/")
            return path

        handler.map_path = MagicMock(side_effect=mock_map_path)

        handler._apply_vray_proxy_path_mapping()

        assert mock_proxy1.fileName == "/session/Assets/tree.vrmesh"
        assert mock_proxy2.fileName == "/session/Assets/rock.vrmesh"

        captured = capsys.readouterr()
        assert "2 proxies remapped" in captured.out

    @patch.dict(
        "os.environ",
        {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        },
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_skips_proxy_without_filename(
        self, mock_rt: MagicMock, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that proxies without fileName attribute are skipped."""
        mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

        mock_proxy = MagicMock(spec=["name"])
        mock_proxy.name = "EmptyProxy"

        mock_rt.objects = [mock_proxy]
        mock_rt.classOf.return_value = mock_rt.VRayProxy

        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        handler = VrayHandler(gpu=False)
        handler.map_path = MagicMock(return_value="/mapped/path")

        handler._apply_vray_proxy_path_mapping()

        handler.map_path.assert_not_called()

        captured = capsys.readouterr()
        assert "0 proxies remapped" in captured.out


class TestDefaultMaxHandlerPathMapping:
    """Tests for DefaultMaxHandler path mapping base functionality."""

    def test_apply_path_mapping_base_does_nothing(self) -> None:
        """Test that base _apply_path_mapping does nothing."""
        from deadline.max_adaptor.MaxClient.render_handlers.default_max_handler import (
            DefaultMaxHandler,
        )

        handler = DefaultMaxHandler()
        handler.map_path = MagicMock(return_value="/mapped/path")

        handler._apply_path_mapping()

        handler.map_path.assert_not_called()

    @patch("deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.rt")
    @patch("deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.os.path.isfile")
    def test_set_scene_file_calls_apply_path_mapping(
        self, mock_isfile: MagicMock, mock_rt: MagicMock
    ) -> None:
        """Test that set_scene_file calls _apply_path_mapping when map_path is set."""
        mock_isfile.return_value = True

        from deadline.max_adaptor.MaxClient.render_handlers.default_max_handler import (
            DefaultMaxHandler,
        )

        handler = DefaultMaxHandler()
        handler.map_path = MagicMock(return_value="/mapped/path")

        original_apply = handler._apply_path_mapping
        call_tracker = MagicMock()

        def tracked_apply() -> None:
            call_tracker()
            original_apply()

        handler._apply_path_mapping = tracked_apply  # type: ignore[method-assign]

        handler.set_scene_file({"scene_file": "/path/to/scene.max"})

        call_tracker.assert_called_once()

    @patch("deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.rt")
    @patch("deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.os.path.isfile")
    def test_set_scene_file_skips_path_mapping_when_not_injected(
        self, mock_isfile: MagicMock, mock_rt: MagicMock
    ) -> None:
        """Test that set_scene_file skips _apply_path_mapping when map_path is None."""
        mock_isfile.return_value = True

        from deadline.max_adaptor.MaxClient.render_handlers.default_max_handler import (
            DefaultMaxHandler,
        )

        handler = DefaultMaxHandler()
        handler.map_path = None

        call_tracker = MagicMock()
        original_apply = handler._apply_path_mapping

        def tracked_apply() -> None:
            call_tracker()
            original_apply()

        handler._apply_path_mapping = tracked_apply  # type: ignore[method-assign]

        handler.set_scene_file({"scene_file": "/path/to/scene.max"})

        call_tracker.assert_not_called()
