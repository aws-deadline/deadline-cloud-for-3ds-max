# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Tests for get_render_handler() — the renderer-to-handler lookup."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _patch_pymxs():
    """Patch pymxs.runtime references used by every handler module."""
    with (
        patch("deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.rt"),
        patch("deadline.max_adaptor.MaxClient.render_handlers.arnold_handler.rt"),
        patch("deadline.max_adaptor.MaxClient.render_handlers.art_handler.rt"),
        patch("deadline.max_adaptor.MaxClient.render_handlers.corona_handler.rt"),
        patch("deadline.max_adaptor.MaxClient.render_handlers.redshift_handler.rt"),
        patch("deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt"),
    ):
        yield


@pytest.mark.parametrize(
    "renderer_name,expected_class_name",
    [
        pytest.param("Arnold", "ArnoldHandler", id="arnold"),
        pytest.param("Corona", "CoronaHandler", id="corona"),
        pytest.param("ART_Renderer", "ArtHandler", id="art"),
        pytest.param("Redshift_Renderer", "RedshiftHandler", id="redshift"),
        pytest.param("Default_Scanline_Renderer", "DefaultMaxHandler", id="default_scanline"),
        pytest.param("Some_Unknown_Renderer", "DefaultMaxHandler", id="unknown_falls_back"),
    ],
)
def test_get_render_handler_returns_expected_handler(
    renderer_name: str, expected_class_name: str
) -> None:
    """Every supported renderer name should resolve to its specific handler class."""
    # Skip V-Ray here — it requires env-var validation that's covered in test_vray_handler.py.
    with patch.dict("os.environ", {}, clear=False):
        from deadline.max_adaptor.MaxClient.render_handlers import get_render_handler

        handler = get_render_handler(renderer_name)
        assert type(handler).__name__ == expected_class_name


def test_get_render_handler_default_argument_is_scanline() -> None:
    """Calling get_render_handler() with no argument should return DefaultMaxHandler."""
    from deadline.max_adaptor.MaxClient.render_handlers import get_render_handler

    handler = get_render_handler()
    assert type(handler).__name__ == "DefaultMaxHandler"
