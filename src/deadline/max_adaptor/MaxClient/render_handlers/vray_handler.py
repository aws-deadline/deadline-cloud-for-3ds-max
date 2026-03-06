"""
3ds Max Deadline Cloud Adaptor - V-Ray specific actions

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import math
import os
import sys
from pathlib import Path
from typing import Any

from pymxs import runtime as rt

from deadline.max_shared.utilities.filename_utils import format_output_filename
from deadline.max_shared.utilities.max_utils import (
    configure_vray_raw_output,
    is_vray_raw_output_format,
    set_vray_output_path,
)

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
        self.log_to_console("VrayHandler._apply_path_mapping called")
        if self.map_path is None:
            self.log_to_console("VrayHandler._apply_path_mapping: map_path is None, skipping")
            return

        self.log_to_console(
            "VrayHandler._apply_path_mapping: map_path is set, applying VRay proxy path mapping"
        )
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

    def start_render(self, data: dict[str, Any]) -> None:
        """
        Override to set V-Ray output path before rendering.

        Resolves output filename tokens before setting V-Ray output paths,
        so the split buffer filename matches the resolved main output.

        Automatically uses raw output pipeline for .vrimg and .exr formats,
        which stores all render elements in a single multichannel container file.
        For other formats, uses standard V-Ray split buffer output.
        """
        if self.output_dir and self.output_name:
            output_format = self.output_format or ".exr"

            camera_name = data.get("camera", "") or ""
            scene_name = Path(rt.maxFileName).stem if rt.maxFileName else ""
            state_set_name = self.state_set_name or ""

            resolved_name = format_output_filename(
                pattern=self.output_name,
                camera_name=camera_name,
                state_set_name=state_set_name,
                scene_name=scene_name,
            )

            # Auto-detect raw output mode based on format
            if is_vray_raw_output_format(output_format):
                self.log_to_console(f"V-Ray raw output mode enabled for format: {output_format}")
                warnings = configure_vray_raw_output(
                    output_path=self.output_dir,
                    output_name=resolved_name,
                    output_format=output_format,
                )
                for warning in warnings:
                    self.log_to_console(f"Warning: {warning}")
            else:
                # Standard V-Ray output path for other formats
                set_vray_output_path(
                    output_path=self.output_dir,
                    output_name=resolved_name,
                    output_format=output_format,
                )

        super().start_render(data)
