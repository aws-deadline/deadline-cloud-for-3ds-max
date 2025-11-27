# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import sys
from unittest.mock import Mock, patch

import pytest


class TestVrayHandler:
    """Tests for VrayHandler environment variable validation"""

    @patch.dict(
        os.environ,
        {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        },
        clear=True,
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_vray_handler_with_all_env_vars(self, mock_rt: Mock) -> None:
        """Test VRay handler initializes successfully with all env vars"""
        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        # Mock 3ds Max 2025: #(27000, 27, 0, 0, 0)
        mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

        # Should not raise
        handler = VrayHandler(gpu=False)
        assert handler is not None
        assert handler.gpu is False

    @patch.dict(
        os.environ,
        {
            "VRAY_FOR_3DSMAX2026_MAIN": "C:\\ProgramData\\VRay\\main",
            "VRAY_FOR_3DSMAX2026_PLUGINS": "C:\\ProgramData\\VRay\\plugins",
            "VRAY_MDL_PATH_3DSMAX2026": "C:\\Program Files\\VRay\\mdl",
        },
        clear=True,
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_vray_gpu_handler_with_all_env_vars(self, mock_rt: Mock) -> None:
        """Test VRay GPU handler also validates environment"""
        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        # Mock 3ds Max 2026: #(28000, 28, 0, 0, 0)
        mock_rt.maxVersion.return_value = [28000, 28, 0, 0, 0]

        # Should not raise
        handler = VrayHandler(gpu=True)
        assert handler is not None
        assert handler.gpu is True

    def test_vray_handler_missing_all_env_vars(self) -> None:
        """Test VRay handler fails with missing env vars"""
        with patch.dict("os.environ", {}, clear=True):
            with patch("pymxs.runtime") as mock_rt:
                # Mock 3ds Max 2025: #(27000, 27, 0, 0, 0)
                mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

                # Clear the module cache to ensure fresh import after patching
                if "deadline.max_adaptor.MaxClient.render_handlers.vray_handler" in sys.modules:
                    del sys.modules["deadline.max_adaptor.MaxClient.render_handlers.vray_handler"]

                from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import (
                    VrayHandler,
                )

                # Expect RuntimeError
                with pytest.raises(RuntimeError) as exc_info:
                    VrayHandler(gpu=False)

                # Verify error message
                error_msg = str(exc_info.value)
                assert "V-Ray renderer detected" in error_msg
                assert "required environment variables are missing" in error_msg
                assert "VRAY_FOR_3DSMAX2025_MAIN" in error_msg
                assert "VRAY_FOR_3DSMAX2025_PLUGINS" in error_msg
                assert "VRAY_MDL_PATH_3DSMAX2025" in error_msg

    def test_vray_handler_missing_main_variable(self) -> None:
        """Test VRay handler fails with missing MAIN variable"""
        env_vars = {
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            with patch("pymxs.runtime") as mock_rt:
                # Mock 3ds Max 2025
                mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

                if "deadline.max_adaptor.MaxClient.render_handlers.vray_handler" in sys.modules:
                    del sys.modules["deadline.max_adaptor.MaxClient.render_handlers.vray_handler"]

                from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import (
                    VrayHandler,
                )

                # Expect RuntimeError
                with pytest.raises(RuntimeError) as exc_info:
                    VrayHandler(gpu=False)

                # Verify error message contains the missing variable
                error_msg = str(exc_info.value)
                assert "VRAY_FOR_3DSMAX2025_MAIN" in error_msg
                # Should not mention the variables that are present
                assert "VRAY_FOR_3DSMAX2025_PLUGINS" not in error_msg
                assert "VRAY_MDL_PATH_3DSMAX2025" not in error_msg

    def test_vray_handler_missing_plugins_variable(self) -> None:
        """Test VRay handler fails with missing PLUGINS variable"""
        env_vars = {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            with patch("pymxs.runtime") as mock_rt:
                # Mock 3ds Max 2025
                mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

                if "deadline.max_adaptor.MaxClient.render_handlers.vray_handler" in sys.modules:
                    del sys.modules["deadline.max_adaptor.MaxClient.render_handlers.vray_handler"]

                from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import (
                    VrayHandler,
                )

                # Expect RuntimeError
                with pytest.raises(RuntimeError) as exc_info:
                    VrayHandler(gpu=False)

                # Verify error message contains the missing variable
                error_msg = str(exc_info.value)
                assert "VRAY_FOR_3DSMAX2025_PLUGINS" in error_msg

    def test_vray_handler_missing_mdl_path_variable(self) -> None:
        """Test VRay handler fails with missing MDL_PATH variable"""
        env_vars = {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            with patch("pymxs.runtime") as mock_rt:
                # Mock 3ds Max 2025
                mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

                if "deadline.max_adaptor.MaxClient.render_handlers.vray_handler" in sys.modules:
                    del sys.modules["deadline.max_adaptor.MaxClient.render_handlers.vray_handler"]

                from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import (
                    VrayHandler,
                )

                # Expect RuntimeError
                with pytest.raises(RuntimeError) as exc_info:
                    VrayHandler(gpu=False)

                # Verify error message contains the missing variable
                error_msg = str(exc_info.value)
                assert "VRAY_MDL_PATH_3DSMAX2025" in error_msg

    @patch.dict(
        os.environ,
        {
            "VRAY_FOR_3DSMAX2024_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2024_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2024": "/path/to/mdl",
        },
        clear=True,
    )
    @patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt")
    def test_vray_handler_with_3dsmax_2024(self, mock_rt: Mock) -> None:
        """Test VRay handler with 3ds Max 2024"""
        from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import VrayHandler

        # Mock 3ds Max 2024: #(26000, 26, 0, 0, 4098)
        mock_rt.maxVersion.return_value = [26000, 26, 0, 0, 4098]

        # Should not raise
        handler = VrayHandler(gpu=False)
        assert handler is not None

    def test_vray_handler_wrong_year_env_vars(self) -> None:
        """Test VRay handler fails when env vars are for wrong year"""
        env_vars = {
            "VRAY_FOR_3DSMAX2024_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2024_PLUGINS": "/path/to/plugins",
            "VRAY_MDL_PATH_3DSMAX2024": "/path/to/mdl",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            with patch("pymxs.runtime") as mock_rt:
                # Mock 3ds Max 2025 but env vars are for 2024
                mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

                if "deadline.max_adaptor.MaxClient.render_handlers.vray_handler" in sys.modules:
                    del sys.modules["deadline.max_adaptor.MaxClient.render_handlers.vray_handler"]

                from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import (
                    VrayHandler,
                )

                # Expect RuntimeError because 2025 variables are missing
                with pytest.raises(RuntimeError) as exc_info:
                    VrayHandler(gpu=False)

                # Verify error message asks for 2025 variables
                error_msg = str(exc_info.value)
                assert "VRAY_FOR_3DSMAX2025_MAIN" in error_msg
                assert "VRAY_FOR_3DSMAX2025_PLUGINS" in error_msg
                assert "VRAY_MDL_PATH_3DSMAX2025" in error_msg

    def test_vray_handler_multiple_missing_vars(self) -> None:
        """Test VRay handler lists all missing variables"""
        env_vars = {
            "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
            "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            with patch("pymxs.runtime") as mock_rt:
                # Mock 3ds Max 2025
                mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

                # Clear module cache after patching pymxs
                if "deadline.max_adaptor.MaxClient.render_handlers.vray_handler" in sys.modules:
                    del sys.modules["deadline.max_adaptor.MaxClient.render_handlers.vray_handler"]

                from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import (
                    VrayHandler,
                )

                # Expect RuntimeError
                with pytest.raises(RuntimeError) as exc_info:
                    VrayHandler(gpu=False)

                # Verify error message contains only the missing variable
                error_msg = str(exc_info.value)
                assert "VRAY_MDL_PATH_3DSMAX2025" in error_msg
                # Present variables should not be in the error
                assert "VRAY_FOR_3DSMAX2025_MAIN" not in error_msg
                assert "VRAY_FOR_3DSMAX2025_PLUGINS" not in error_msg
