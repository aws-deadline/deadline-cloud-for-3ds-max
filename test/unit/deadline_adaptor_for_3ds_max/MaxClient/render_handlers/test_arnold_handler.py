# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestArnoldHandler:
    """Tests for ArnoldHandler renderer activation."""

    @pytest.mark.parametrize(
        "current_renderer_str,expected_set_called",
        [
            pytest.param(
                "Default_Scanline_Renderer:Default_Scanline_Renderer", True, id="from_scanline"
            ),
            pytest.param("V_Ray_6_Hotfix_3:V_Ray_6_Hotfix_3", True, id="from_vray"),
            pytest.param("Redshift_Renderer:Redshift_Renderer", True, id="from_redshift"),
            pytest.param("Arnold:Arnold", False, id="already_arnold_no_op"),
        ],
    )
    def test_check_renderer_sets_arnold_when_not_active(
        self, current_renderer_str: str, expected_set_called: bool
    ) -> None:
        """check_renderer() should set rt.Arnold() only when the active renderer is not already Arnold."""
        with patch("deadline.max_adaptor.MaxClient.render_handlers.arnold_handler.rt") as mock_rt:
            # Plain string assignment — handler does str(rt.renderers.current).split(":")[0],
            # which works on a string and yields the expected value before the colon.
            mock_rt.renderers.current = current_renderer_str

            from deadline.max_adaptor.MaxClient.render_handlers.arnold_handler import (
                ArnoldHandler,
            )

            handler = ArnoldHandler()
            handler.check_renderer()

            if expected_set_called:
                mock_rt.Arnold.assert_called_once()
                # And the new renderer should be assigned back into rt.renderers.current
                assert mock_rt.renderers.current is mock_rt.Arnold.return_value
            else:
                mock_rt.Arnold.assert_not_called()
                # current should not have been overwritten
                assert mock_rt.renderers.current == current_renderer_str
