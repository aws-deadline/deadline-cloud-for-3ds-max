"""
3ds Max Deadline Cloud Adaptor - V-Ray specific actions

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import sys

import pymxs  # noqa
from pymxs import runtime as rt

from .default_max_handler import DefaultMaxHandler

# Re-assign sys stdout and stderr to print in the console instead of the Max Listener
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__


class VrayHandler(DefaultMaxHandler):
    """Render Handler for V-Ray"""

    def __init__(self, GPU):
        """
        Initializes the V-Ray and V-Ray Handler
        """
        super().__init__()
        self.GPU: bool = GPU

    def check_renderer(self) -> None:
        """
        Checks if the active renderer is set to V-Ray. If it is not, set it to the latest version V-Ray.
        Gets the latest versions of V-Ray and V-Ray GPU from rt.rendererclass.classes.
        """
        current_renderer = str(rt.renderers.current).split(":")[0]

        # The V-Ray renderer class name is "V_Ray_6__update_#_#" and "V_Ray_GPU_6__update_#_#"
        if self.GPU:
            try:
                vray_gpu = [
                    i
                    for i in list(rt.rendererclass.classes)
                    if "V_Ray" in str(i) and "GPU" in str(i)
                ][-1]
            except Exception:
                print("Error: unable to find V-Ray GPU plugin")
                raise RuntimeError("Error: unable to find V-Ray GPU plugin")

            if "V_Ray_GPU" not in current_renderer:
                # Set to most recent version of V-Ray GPU
                rt.renderers.current = vray_gpu()
        else:
            try:
                vray = [
                    i
                    for i in list(rt.rendererclass.classes)
                    if "V_Ray" in str(i) and "GPU" not in str(i)
                ][-1]
            except Exception:
                print("Error: unable to find V-Ray plugin")
                raise RuntimeError("Error: unable to find V-Ray plugin")

            if "V_Ray" not in current_renderer or "V_Ray_GPU" in current_renderer:
                # Set to most recent version of V-Ray
                rt.renderers.current = vray()
