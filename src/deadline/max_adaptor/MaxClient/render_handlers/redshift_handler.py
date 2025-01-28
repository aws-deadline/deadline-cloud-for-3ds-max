"""
3ds Max Deadline Cloud Adaptor - Redshift specific actions

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import sys

import pymxs  # noqa
from pymxs import runtime as rt

from .default_max_handler import DefaultMaxHandler

# Re-assign sys stdout and stderr to print in the console instead of the Max Listener
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__


class RedshiftHandler(DefaultMaxHandler):
    """Render Handler for Redshift"""

    def __init__(self):
        """
        Initializes Redshift Renderer and Redshift Handler
        """
        super().__init__()

    def check_renderer(self) -> None:
        """
        Checks if the active renderer is set to Redshift. If it is not, set it to Redshift.
        """
        current_renderer = str(rt.renderers.current).split(":")[0]
        if current_renderer != "Redshift_Renderer":
            rt.renderers.current = rt.Redshift_Renderer()
