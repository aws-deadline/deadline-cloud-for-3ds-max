# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Integration tests for path mapping functionality with VRMesh assets.

This module tests that the 3dsMax adaptor correctly handles path mapping rules
to remap asset paths (like VRMesh files) at render time.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml
from flaky import flaky

from .helpers.test_runners import run_adaptor_test

from test.integ.test_const import (
    TEMPLATE,
    TEST_SCENE_FOLDER,
    OUTPUT_FOLDER,
    EXPECTED_JOB_BUNDLE_FOLDER,
)

# 3ds Max log file location - dynamically find for any version
EXPECTED_IMAGES_FOLDER = "expected_images"


def get_max_log_path() -> Optional[Path]:
    """
    Find the 3ds Max log file path based on the 3ds Max version in PATH.

    The function looks for 3ds Max installation paths in the PATH environment
    variable (e.g., C:\\Program Files\\Autodesk\\3ds Max 2026) to determine
    which version is being used for testing.

    The log file is located at:
    %LOCALAPPDATA%/Autodesk/3dsMax/<version> - 64bit/ENU/Network/Max.log

    Returns:
        Path to the Max.log file if found, None otherwise.
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        return None

    # Look for 3ds Max version in PATH environment variable
    path_env = os.environ.get("PATH", "")
    max_version_pattern = re.compile(r"3ds\s*Max\s*(\d{4})", re.IGNORECASE)

    max_version = None
    for path_entry in path_env.split(os.pathsep):
        match = max_version_pattern.search(path_entry)
        if match:
            max_version = int(match.group(1))
            print(f"Found 3ds Max {max_version} in PATH: {path_entry}")
            break

    if max_version:
        # Construct log path using the version found in PATH
        log_path = (
            Path(local_app_data)
            / "Autodesk"
            / "3dsMax"
            / f"{max_version} - 64bit"
            / "ENU"
            / "Network"
            / "Max.log"
        )
        return log_path

    # Fallback: scan for any installed version if not found in PATH
    print("Warning: 3ds Max not found in PATH, scanning for installed versions...")
    max_base_path = Path(local_app_data) / "Autodesk" / "3dsMax"
    if not max_base_path.exists():
        return None

    # Look for any 3ds Max version directory (2024, 2025, 2026, etc.)
    version_dirs = []
    for version_dir in max_base_path.iterdir():
        if version_dir.is_dir() and "64bit" in version_dir.name:
            try:
                year = int(version_dir.name.split()[0])
                if 2024 <= year <= 2030:
                    version_dirs.append((year, version_dir))
            except (ValueError, IndexError):
                continue

    if version_dirs:
        # Sort by year descending and return the most recent
        version_dirs.sort(key=lambda x: x[0], reverse=True)
        return version_dirs[0][1] / "ENU" / "Network" / "Max.log"

    return None


def create_path_mapping_rules(
    source_scene_path: str,
    destination_scene_path: str,
    additional_rules: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Create path mapping rules JSON structure for test execution.

    This utility function generates path mapping rules that remap asset paths
    from a source location to a destination location. This is useful for testing
    scenarios where assets are stored in different locations than where the scene
    file references them.

    Args:
        source_scene_path: The original path where assets are referenced in the scene file.
        destination_scene_path: The actual path where assets exist at test time.
        additional_rules: Optional list of additional path mapping rule dictionaries.

    Returns:
        A dictionary conforming to the pathmapping-1.0 schema.
    """
    rules = [
        {
            "source_path_format": "WINDOWS",
            "source_path": source_scene_path.replace("\\", "/"),
            "destination_path": destination_scene_path.replace("\\", "/"),
        }
    ]

    if additional_rules:
        rules.extend(additional_rules)

    return {"version": "pathmapping-1.0", "path_mapping_rules": rules}


def update_path_mapping_for_checkout(
    path_mapping_file: Path,
    checkout_root: Path,
) -> Dict[str, Any]:
    """
    Update path mapping rules to use the current checkout path.

    This function reads an existing path mapping rules file and updates the
    destination paths to point to the current code checkout location. This is
    necessary because the path mapping rules may have been created with hardcoded
    paths from a different machine or checkout location.

    Args:
        path_mapping_file: Path to the existing path_mapping_rules.json file.
        checkout_root: The root path of the current code checkout.

    Returns:
        Updated path mapping rules dictionary with destination paths adjusted
        to the current checkout location.
    """
    with open(path_mapping_file, "r") as f:
        path_mapping = json.load(f)

    updated_rules = []
    for rule in path_mapping.get("path_mapping_rules", []):
        updated_rule = rule.copy()

        # Extract the relative path portion from the destination path
        # The destination path typically contains the full path like:
        # C:/Users/RDP/deadline-cloud-for-3ds-max/test/integ/test_scripts/...
        dest_path = rule.get("destination_path", "").replace("\\", "/")

        # Find the relative path starting from test/integ/test_scripts
        relative_marker = "test/integ/test_scripts"
        if relative_marker in dest_path:
            relative_path = relative_marker + dest_path.split(relative_marker, 1)[1]
            new_dest = str(checkout_root / relative_path).replace("\\", "/")
            updated_rule["destination_path"] = new_dest

        updated_rules.append(updated_rule)

    return {
        "version": path_mapping.get("version", "pathmapping-1.0"),
        "path_mapping_rules": updated_rules,
    }


def verify_path_mapping_in_log(
    log_path: Path,
    expected_source_pattern: str,
    expected_dest_pattern: str,
) -> List[str]:
    """
    Verify that path mapping occurred correctly by checking the 3ds Max log file.

    Args:
        log_path: Path to the 3ds Max log file.
        expected_source_pattern: Pattern to match in the source path (e.g., "assets\\Bench.vrmesh").
        expected_dest_pattern: Pattern to match in the destination path (e.g., "vray_vrmesh_remap_test\\scene\\Bench.vrmesh").

    Returns:
        List of matching log lines.

    Raises:
        AssertionError: If the log file does not exist or no valid remap is found.
    """
    assert log_path.exists(), f"Log file not found: {log_path}"

    matching_lines = []
    remap_pattern = re.compile(r"Remapped VRayProxy '([^']+)':\s*(.+?)\s*->\s*(.+)")

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "Remapped VRayProxy" in line:
                matching_lines.append(line.strip())

    # Verify at least one remap occurred with expected paths
    found_valid_remap = False
    for line in matching_lines:
        match = remap_pattern.search(line)
        if match:
            _, source_path, dest_path = match.groups()
            # Normalize paths for comparison
            source_normalized = source_path.replace("\\", "/").lower()
            dest_normalized = dest_path.replace("\\", "/").lower()
            expected_source_normalized = expected_source_pattern.replace("\\", "/").lower()
            expected_dest_normalized = expected_dest_pattern.replace("\\", "/").lower()

            if (
                expected_source_normalized in source_normalized
                and expected_dest_normalized in dest_normalized
            ):
                found_valid_remap = True
                break

    assert found_valid_remap, (
        f"Path mapping verification failed. Expected remapping from '{expected_source_pattern}' "
        f"to '{expected_dest_pattern}'.\nLog entries found: {matching_lines}"
    )

    return matching_lines


def get_vrmesh_remap_count_from_log(log_path: Path) -> int:
    """
    Get the count of VRMesh proxies remapped from the log file.

    Args:
        log_path: Path to the 3ds Max log file.

    Returns:
        Number of proxies remapped, or -1 if not found.
    """
    if not log_path.exists():
        return -1

    pattern = re.compile(r"VRMesh path mapping complete:\s*(\d+)\s*proxies remapped")

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                return int(match.group(1))

    return -1


@pytest.mark.adaptor
@pytest.mark.pathmapping
@flaky(max_runs=1, min_passes=1)
class TestPathMappingAdaptors:
    """
    Tests for path mapping functionality in the 3dsMax adaptor.

    These tests verify that the adaptor correctly applies path mapping rules
    to remap asset paths (like VRMesh files) during rendering.
    """

    @pytest.mark.parametrize(
        "bundle_dir,scene_max",
        [
            ("vray_vrmesh_remap_test", "fog.max"),
        ],
    )
    def test_vrmesh_path_remap_adaptor(
        self,
        script_location: Path,
        tmp_path: Path,
        bundle_dir: str,
        scene_max: str,
    ) -> None:
        """
        Test that VRMesh assets are correctly remapped using path mapping rules.

        This test verifies that when a scene references VRMesh files from a different
        location, the path mapping rules correctly redirect the adaptor to find the
        assets in their actual location.
        """
        # Get the log path and delete it for a clean test run
        max_log_path = get_max_log_path()
        if max_log_path and max_log_path.exists():
            print(f"Deleting existing log file for clean test run: {max_log_path}")
            max_log_path.unlink()

        test_file_location = script_location / bundle_dir
        scene_location = test_file_location / TEST_SCENE_FOLDER / scene_max
        output_path = tmp_path / OUTPUT_FOLDER
        path_mapping_file = test_file_location / "path_mapping_rules.json"

        # Get the checkout root (workspace root) by finding the repo name in the path
        repo_name = "deadline-cloud-for-3ds-max"
        current_path = Path(__file__).resolve()
        checkout_root = None
        for parent in current_path.parents:
            if parent.name == repo_name:
                checkout_root = parent
                break
        assert (
            checkout_root is not None
        ), f"Could not find repository root '{repo_name}' in path: {current_path}"

        # Update path mapping rules to use current checkout path
        path_mapping_rules = update_path_mapping_for_checkout(path_mapping_file, checkout_root)

        # Parse parameter_values.yaml file for this test bundle
        parameter_values_path = (
            test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / "parameter_values.yaml"
        )
        with open(parameter_values_path, "r") as f:
            parameter_data = yaml.safe_load(f)

        # Convert parameter values to a dictionary
        job_params = {}
        for param in parameter_data["parameterValues"]:
            job_params[param["name"]] = param["value"]

        # Override only MaxSceneFile and OutputFilePath from test parameters
        job_params["MaxSceneFile"] = str(scene_location)
        job_params["OutputFilePath"] = str(output_path)

        run_adaptor_test(
            test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE,
            job_params,
            path_mapping_rules,
        )

        # Verify output directory was created
        assert output_path.exists(), f"Output directory was not created: {output_path}"

        # Verify output files exist by comparing with expected_images folder
        expected_images_path = test_file_location / EXPECTED_IMAGES_FOLDER
        if expected_images_path.exists():
            expected_files = list(expected_images_path.glob("*"))
            assert len(expected_files) > 0, f"No expected images found in {expected_images_path}"

            for expected_file in expected_files:
                output_file = output_path / expected_file.name
                assert output_file.exists(), (
                    f"Expected output file not found: {output_file}\n"
                    f"Expected based on: {expected_file}"
                )
                print(f"Verified output file exists: {output_file}")

        # Verify path mapping occurred correctly by checking the log file
        if max_log_path and max_log_path.exists():
            # Check that VRMesh remapping occurred
            remap_lines = verify_path_mapping_in_log(
                max_log_path,
                expected_source_pattern="assets/Bench.vrmesh",
                expected_dest_pattern="vray_vrmesh_remap_test/scene/Bench.vrmesh",
            )

            print(f"\nPath mapping log entries found ({len(remap_lines)}):")
            for line in remap_lines:
                print(f"  {line}")

            # Verify the expected number of proxies were remapped
            remap_count = get_vrmesh_remap_count_from_log(max_log_path)
            print(f"\nVRMesh proxies remapped: {remap_count}")

            assert remap_count >= 1, (
                f"Expected at least 1 VRMesh proxy to be remapped, but found {remap_count}.\n"
                f"Check the log file: {max_log_path}"
            )
        else:
            print(
                f"Log file not found at {max_log_path or 'unknown path'}, "
                "cannot verify path mapping"
            )
            assert False, (
                f"Log file not found at {max_log_path or 'unknown path'}. "
                "Cannot verify path mapping occurred correctly."
            )
