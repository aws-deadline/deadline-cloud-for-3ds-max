# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from .default_max_handler import DefaultMaxHandler
from .art_handler import ArtHandler

__all__ = ["DefaultMaxHandler", "get_render_handler"]


def get_render_handler(renderer: str = "Default_Scanline_Renderer") -> DefaultMaxHandler:
    """
    Returns the render handler instance for the given renderer.

    Args:
    :param renderer: The renderer to get the render handler of. Defaults to "Default_Scanline_Renderer".
    :type renderer: (str, optional)

    :returns: the Render Handler instance for the given renderer.
    """
    if renderer == "ART_Renderer":
        return ArtHandler()
    else:
        return DefaultMaxHandler()
