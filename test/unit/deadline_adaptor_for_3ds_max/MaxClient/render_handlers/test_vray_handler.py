# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest.mock import patch

import pytest


class TestVrayHandler:
    """Tests for VrayHandler environment variable validation"""

    @pytest.mark.parametrize(
        "max_version,year,gpu,env_vars",
        [
            pytest.param(
                [27000, 27, 0, 0, 0],
                2025,
                False,
                {
                    "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
                    "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
                    "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
                },
                id="3dsmax_2025_cpu",
            ),
            pytest.param(
                [28000, 28, 0, 0, 0],
                2026,
                True,
                {
                    "VRAY_FOR_3DSMAX2026_MAIN": "C:\\ProgramData\\VRay\\main",
                    "VRAY_FOR_3DSMAX2026_PLUGINS": "C:\\ProgramData\\VRay\\plugins",
                    "VRAY_MDL_PATH_3DSMAX2026": "C:\\Program Files\\VRay\\mdl",
                },
                id="3dsmax_2026_gpu",
            ),
            pytest.param(
                [26000, 26, 0, 0, 4098],
                2024,
                False,
                {
                    "VRAY_FOR_3DSMAX2024_MAIN": "/path/to/main",
                    "VRAY_FOR_3DSMAX2024_PLUGINS": "/path/to/plugins",
                    "VRAY_MDL_PATH_3DSMAX2024": "/path/to/mdl",
                },
                id="3dsmax_2024_cpu",
            ),
        ],
    )
    def test_vray_handler_with_valid_env_vars(
        self, max_version: list[int], year: int, gpu: bool, env_vars: dict[str, str]
    ) -> None:
        """Test VRay handler initializes successfully with all required env vars"""
        with patch.dict("os.environ", env_vars, clear=True):
            with patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt") as mock_rt:
                mock_rt.maxVersion.return_value = max_version

                from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import (
                    VrayHandler,
                )

                handler = VrayHandler(gpu=gpu)
                assert handler is not None
                assert handler.gpu is gpu

    @pytest.mark.parametrize(
        "env_vars,expected_missing",
        [
            pytest.param(
                {},
                [
                    "VRAY_FOR_3DSMAX2025_MAIN",
                    "VRAY_FOR_3DSMAX2025_PLUGINS",
                    "VRAY_MDL_PATH_3DSMAX2025",
                ],
                id="all_missing",
            ),
            pytest.param(
                {
                    "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
                    "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
                },
                ["VRAY_FOR_3DSMAX2025_MAIN"],
                id="missing_main",
            ),
            pytest.param(
                {
                    "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
                    "VRAY_MDL_PATH_3DSMAX2025": "/path/to/mdl",
                },
                ["VRAY_FOR_3DSMAX2025_PLUGINS"],
                id="missing_plugins",
            ),
            pytest.param(
                {
                    "VRAY_FOR_3DSMAX2025_MAIN": "/path/to/main",
                    "VRAY_FOR_3DSMAX2025_PLUGINS": "/path/to/plugins",
                },
                ["VRAY_MDL_PATH_3DSMAX2025"],
                id="missing_mdl_path",
            ),
            pytest.param(
                {
                    "VRAY_FOR_3DSMAX2024_MAIN": "/path/to/main",
                    "VRAY_FOR_3DSMAX2024_PLUGINS": "/path/to/plugins",
                    "VRAY_MDL_PATH_3DSMAX2024": "/path/to/mdl",
                },
                [
                    "VRAY_FOR_3DSMAX2025_MAIN",
                    "VRAY_FOR_3DSMAX2025_PLUGINS",
                    "VRAY_MDL_PATH_3DSMAX2025",
                ],
                id="wrong_year_2024_instead_of_2025",
            ),
        ],
    )
    def test_vray_handler_missing_env_vars(
        self, env_vars: dict[str, str], expected_missing: list[str]
    ) -> None:
        """Test VRay handler fails with missing environment variables"""
        with patch.dict("os.environ", env_vars, clear=True):
            with patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt") as mock_rt:
                mock_rt.maxVersion.return_value = [27000, 27, 0, 0, 0]

                from deadline.max_adaptor.MaxClient.render_handlers.vray_handler import (
                    VrayHandler,
                )

                with pytest.raises(RuntimeError) as exc_info:
                    VrayHandler(gpu=False)

                error_msg = str(exc_info.value)
                assert "V-Ray renderer detected" in error_msg
                assert "required environment variables are missing" in error_msg

                # Check that all expected missing variables are in the error message
                for var in expected_missing:
                    assert var in error_msg

                # Check that present variables are not in the error message
                all_vars = {
                    "VRAY_FOR_3DSMAX2025_MAIN",
                    "VRAY_FOR_3DSMAX2025_PLUGINS",
                    "VRAY_MDL_PATH_3DSMAX2025",
                }
                present_vars = all_vars - set(expected_missing)
                for var in present_vars:
                    if var in env_vars:
                        assert var not in error_msg
