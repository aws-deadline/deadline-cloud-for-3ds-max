"""
3ds Max Deadline Cloud Adaptor - V-Ray specific actions

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import math
import os
import sys
from typing import Any

from pymxs import runtime as rt

from deadline.max_shared.utilities.max_utils import set_vray_output_path

from .default_max_handler import DefaultMaxHandler

# Re-assign sys stdout and stderr to print in the console instead of the Max Listener
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__


class VrayHandler(DefaultMaxHandler):
    """Render Handler for V-Ray"""

    def __init__(self, gpu: bool) -> None:
        """
        Initializes the V-Ray and V-Ray Handler
        """
        super().__init__()
        self.gpu: bool = gpu
        self._validate_vray_environment()

    def _validate_vray_environment(self) -> None:
        """
        Validates that required VRay environment variables are set.
        Raises RuntimeError with actionable message if variables are missing.
        """
        # Get 3ds Max year using the same formula as max_render_submitter.py
        max_version: Any = rt.maxVersion()
        # Convert to int to handle both real values and mock objects
        version_major: int = int(max_version[0])
        year: int = 2000 + math.ceil(version_major / 1000.0) - 2

        # Define required environment variables
        required_vars: list[str] = [
            f"VRAY_FOR_3DSMAX{year}_MAIN",
            f"VRAY_FOR_3DSMAX{year}_PLUGINS",
            f"VRAY_MDL_PATH_3DSMAX{year}",
        ]

        # Check for missing variables
        missing_vars: list[str] = [var for var in required_vars if var not in os.environ]

        if missing_vars:
            error_msg = (
                f"V-Ray renderer detected, but required environment variables are missing.\n"
                f"Please set the following variables in to the system environment variables:\n"
                f"{os.linesep.join(f'  - {var}' for var in missing_vars)}"
            )
            print(error_msg, flush=True)
            raise RuntimeError(error_msg)
        else:
            # Print confirmation that VRay environment is properly configured
            success_msg = (
                f"V-Ray environment validated successfully for 3ds Max {year}:\n"
                f"{os.linesep.join(f'  - {var}: {os.environ[var]}' for var in required_vars)}"
            )
            print(success_msg, flush=True)

    def check_renderer(self) -> None:
        """
        Checks if the active renderer is set to V-Ray. If it is not, set it to the latest version V-Ray.
        Gets the latest versions of V-Ray and V-Ray GPU from rt.rendererclass.classes.
        """
        current_renderer = str(rt.renderers.current).split(":")[0]

        # The V-Ray renderer class name is "V_Ray_6__update_#_#" and "V_Ray_GPU_6__update_#_#"
        if self.gpu:
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

    def _apply_path_mapping(self) -> None:
        """
        Applies path mapping to V-Ray specific assets.

        Currently handles:
        - VRayProxy objects (.vrmesh files)

        TODO: Add support for VRayHDRI (HDR environment maps)
        TODO: Add support for VRayMesh (V-Ray mesh export files)
        TODO: Add support for VRayFur (fur/hair geometry files)
        TODO: Add support for VRayScene (V-Ray scene files .vrscene)
        """
        if self.map_path is None:
            return

        self._apply_vray_proxy_path_mapping()

    def _apply_vray_proxy_path_mapping(self) -> None:
        """
        Applies path mapping to all VRayProxy objects in the scene.
        """
        # Check if VRayProxy class exists
        if not hasattr(rt, "VRayProxy"):
            self.log_to_console("VRayProxy class not found - V-Ray may not be loaded")
            return

        # rt.objects returns pymxs objects (dynamically typed)
        proxies: list[Any] = [obj for obj in rt.objects if rt.classOf(obj) == rt.VRayProxy]

        if not proxies:
            self.log_to_console("No VRayProxy objects found in scene")
            return

        mapped_count: int = 0
        for proxy in proxies:
            original_path: Any = getattr(proxy, "fileName", None)
            if not original_path:
                continue

            original_path_str: str = str(original_path)

            # Use the injected map_path function (guaranteed non-None by caller)
            assert self.map_path is not None  # For mypy
            self.log_to_console(f"Requesting Path Mapping for path '{original_path_str}'.")
            mapped_path: str = self.map_path(original_path_str)
            self.log_to_console(f"Mapped path '{original_path_str}' to '{mapped_path}'.")

            if mapped_path != original_path_str:
                try:
                    proxy.fileName = mapped_path
                    mapped_count += 1
                    self.log_to_console(
                        f"Remapped VRayProxy '{proxy.name}': {original_path_str} -> {mapped_path}"
                    )
                except Exception as e:
                    self.log_to_console(f"Warning: Failed to remap VRayProxy '{proxy.name}': {e}")

        self.log_to_console(f"VRMesh path mapping complete: {mapped_count} proxies remapped")

    def start_render(self, data: dict) -> None:
        """
        Override to set V-Ray output path before rendering.

        Always sets V-Ray output path for both standard V-Ray and V-Ray RT.
        """
        # Always set V-Ray output path
        if self.output_dir and self.output_name:
            set_vray_output_path(
                output_path=self.output_dir,
                output_name=self.output_name,
                output_format=self.output_format or ".exr",
            )

        super().start_render(data)
