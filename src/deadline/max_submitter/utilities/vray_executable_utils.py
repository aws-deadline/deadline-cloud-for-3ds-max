# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Utilities for finding V-Ray and 3ds Max executable paths."""

import logging
import os

from pymxs import runtime as rt

_logger = logging.getLogger(__name__)


def get_vray_executable_path() -> str:
    """Find vray.exe — checks VRAY_EXECUTABLE env var, then V-Ray environment.

    Set the VRAY_EXECUTABLE environment variable to the full path of vray.exe
    for reliable detection. Falls back to deriving the path from V-Ray's own
    environment variables (e.g. VRAY_FOR_3DSMAX2025_MAIN).
    """
    # Primary: explicit env var
    env_path = os.environ.get("VRAY_EXECUTABLE", "")
    if env_path and os.path.exists(env_path):
        return env_path

    # Fallback: derive from V-Ray's own env vars (set by V-Ray installer)
    try:
        max_version = 2000 + (int(rt.maxVersion()[0] / 1000.0) - 2)
        vray_main = os.environ.get(f"VRAY_FOR_3DSMAX{max_version}_MAIN", "")
        if vray_main:
            candidate = os.path.join(vray_main, "vray.exe")
            if os.path.exists(candidate):
                return candidate
    except Exception as e:
        _logger.debug(f"V-Ray env var fallback failed: {e}")

    raise FileNotFoundError(
        "V-Ray executable not found. Please set the VRAY_EXECUTABLE environment "
        "variable to the full path of vray.exe."
    )


def get_3dsmax_executable_path() -> str:
    """Find 3dsmaxcmd.exe — checks MAXCMD_EXECUTABLE env var, then current 3ds Max install.

    Set the MAXCMD_EXECUTABLE environment variable to the full path of 3dsmaxcmd.exe
    for reliable detection. Falls back to the current 3ds Max installation directory.
    """
    # Primary: explicit env var
    env_path = os.environ.get("MAXCMD_EXECUTABLE", "")
    if env_path and os.path.exists(env_path):
        return env_path

    # Fallback: derive from current 3ds Max session
    try:
        max_dir = rt.symbolicPaths.getPathValue("$max")
        max_cmd_path = os.path.join(max_dir, "3dsmaxcmd.exe")
        if os.path.exists(max_cmd_path):
            return max_cmd_path
    except Exception as e:
        _logger.debug(f"3ds Max path fallback failed: {e}")

    raise FileNotFoundError(
        "3dsmaxcmd.exe not found. Please set the MAXCMD_EXECUTABLE environment "
        "variable to the full path of 3dsmaxcmd.exe."
    )
