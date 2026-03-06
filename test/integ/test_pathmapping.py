# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Integration tests for path mapping functionality with VRMesh assets.

This module tests that the 3dsMax adaptor correctly handles path mapping rules
to remap asset paths (like VRMesh files) at render time.
"""

import json
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

EXPECTED_IMAGES_FOLDER = "expected_images"


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


def verify_path_mapping_in_output(
    output: str,
    expected_source_pattern: str,
    expected_dest_pattern: str,
) -> List[str]:
    """
    Verify that path mapping occurred correctly by checking the adaptor stdout output.

    Args:
        output: The captured stdout from the adaptor process.
        expected_source_pattern: Pattern to match in the source path (e.g., "assets/Bench.vrmesh").
        expected_dest_pattern: Pattern to match in the destination path (e.g., "vray_vrmesh_remap_test/scene/Bench.vrmesh").

    Returns:
        List of matching output lines.

    Raises:
        AssertionError: If no valid remap is found in the output.
    """
    matching_lines = []
    remap_pattern = re.compile(r"Remapped VRayProxy '([^']+)':\s*(.+?)\s*->\s*(.+)")

    for line in output.splitlines():
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
        f"to '{expected_dest_pattern}'.\nOutput lines found: {matching_lines}"
    )

    return matching_lines


def get_vrmesh_remap_count_from_output(output: str) -> int:
    """
    Get the count of VRMesh proxies remapped from the adaptor stdout output.

    Args:
        output: The captured stdout from the adaptor process.

    Returns:
        Number of proxies remapped, or -1 if not found.
    """
    pattern = re.compile(r"VRMesh path mapping complete:\s*(\d+)\s*proxies remapped")

    for line in output.splitlines():
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

        adaptor_output = run_adaptor_test(
            test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE,
            job_params,
            path_mapping_rules,
        )

        # Save adaptor output to a log file for easy viewing
        log_file = tmp_path / f"{bundle_dir}_output.log"
        log_file.write_text(adaptor_output, encoding="utf-8")
        print(f"Adaptor output saved to: {log_file}")

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

        # Verify path mapping occurred correctly using captured stdout
        # This avoids reliance on the Max.log file which can be truncated by 3ds Max.
        remap_lines = verify_path_mapping_in_output(
            adaptor_output,
            expected_source_pattern="assets/Bench.vrmesh",
            expected_dest_pattern="vray_vrmesh_remap_test/scene/Bench.vrmesh",
        )

        print(f"\nPath mapping log entries found ({len(remap_lines)}):")
        for line in remap_lines:
            print(f"  {line}")

        # Verify the expected number of proxies were remapped
        remap_count = get_vrmesh_remap_count_from_output(adaptor_output)
        print(f"\nVRMesh proxies remapped: {remap_count}")

        assert remap_count >= 1, (
            f"Expected at least 1 VRMesh proxy to be remapped, but found {remap_count}.\n"
            f"Adaptor stdout did not contain expected remap count line."
        )
