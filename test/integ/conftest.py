# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def sync_machine_env_vars():
    """
    On Windows, read machine-level environment variables from the registry
    and merge any missing ones into the current process's os.environ.

    Machine-level env vars (e.g. VRAY_FOR_3DSMAX2026_MAIN set by the V-Ray
    installer) live in the registry. A running process only sees them if it
    was started AFTER they were written, AND the parent process propagated
    them. In CI (CodeBuild), the agent process may have been started before
    the installer ran, so its children never inherit the new vars even though
    they exist in the registry.
    """
    if os.name != "nt":
        return

    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ) as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    if name not in os.environ:
                        os.environ[name] = value
                        print(f"Synced machine env var: {name}={value}")
                    i += 1
                except OSError:
                    break
    except OSError as e:
        print(f"WARNING: Could not read machine env vars from registry: {e}")


@pytest.fixture(scope="session", autouse=True)
def setup_max_executable(sync_machine_env_vars):
    """
    Automatically set 3DSMAX_EXECUTABLE environment variable for all tests.
    This ensures the adaptor can find the correct executable when launched by openjd.
    """
    if not os.environ.get("3DSMAX_EXECUTABLE"):
        max_version_env = os.environ.get("MAX_VERSION")
        if not max_version_env:
            raise ValueError("Either 3DSMAX_EXECUTABLE or MAX_VERSION must be set")

        if os.name == "nt":
            max_path = f"C:\\Program Files\\Autodesk\\3ds Max {max_version_env}\\3dsmaxbatch.exe"
        else:
            raise OSError("3ds Max is only supported on Windows")

        os.environ["3DSMAX_EXECUTABLE"] = max_path
        print(f"Set 3DSMAX_EXECUTABLE={max_path}")


@pytest.fixture
def max_location() -> Path:
    """
    Returns the path to the 3ds Max executable.
    The environment variable is already set by setup_max_executable.
    """
    return Path(os.environ["3DSMAX_EXECUTABLE"])


@pytest.fixture
def script_location() -> Path:
    return Path(__file__).parent / "test_scripts"
