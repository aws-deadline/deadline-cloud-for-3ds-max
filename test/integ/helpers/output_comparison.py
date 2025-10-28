# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path
import PIL.Image
import numpy as np
from typing import Any
import yaml

from test.integ.test_const import ASSET_REFERENCES, PARAMETER_VALUES


def _print_test_directory(directory: Path, prefix: str) -> None:
    """
    Print directory information for debugging test comparisons.

    Args:
        directory: Path to the directory to inspect
        prefix: Label prefix (e.g., "Expected" or "Actual")
    """
    print(f"{prefix} image directory: {directory}")
    print(f"{prefix} directory exists: {directory.exists()}")

    if directory.exists():
        files = list(directory.iterdir())
        print(f"{prefix} files ({len(files)}):")
        for f in files:
            print(
                f"  - {f.name} (is_file: {f.is_file()}, size: {f.stat().st_size if f.is_file() else 'N/A'})"
            )
    else:
        print("  (directory does not exist)")


def are_images_similar(
    expected_image_directory: Path,
    actual_image_directory: Path,
    tolerance: int,
    max_diff_files: int = 0,
) -> bool:
    """
    Helper function that compare if the render output from the adaptor match what we expected

    Args:
        expected_image_directory: Path to directory containing expected/reference images
        actual_image_directory: Path to directory containing actual rendered images
        tolerance: Maximum allowed pixel value difference (0-255 scale) for images to be considered similar
        max_diff_files: Maximum number of mismatched images allowed before returning False (default: 0).
                       Useful for handling renderer variability due to random seeds affecting lighting,
                       noise, or other non-deterministic rendering effects

    Returns:
        bool: True if all images match within tolerance (or mismatches <= max_diff_files), False otherwise

    The function performs pixel-by-pixel comparison using numpy arrays and allows for some tolerance
    to account for normal rendering noise. It prints detailed debug information about file counts,
    differences, and which images match or mismatch.
    """
    # Debug: Print directory information about expected and rendered files to help debug.
    print("\n" + "=" * 80)
    print("DEBUG: Image Comparison")
    print("=" * 80)
    _print_test_directory(expected_image_directory, "Expected")
    _print_test_directory(actual_image_directory, "Actual")
    print("=" * 80 + "\n")

    # Assert that the number of files in both directories match
    expected_file_count = len([f for f in expected_image_directory.iterdir() if f.is_file()])
    actual_file_count = len([f for f in actual_image_directory.iterdir() if f.is_file()])

    assert expected_file_count == actual_file_count, (
        f"File count mismatch: Expected {expected_file_count} files, "
        f"but found {actual_file_count} files in actual output"
    )

    mismatched_count = 0

    for image in (expected_image_directory).iterdir():
        if not image.is_file():
            continue

        # Open the two image files with Pillow https://pillow.readthedocs.io/en/stable/index.html
        # and put them in numpy arrays. Pillow doesn't have a good built-in way to do image comparison
        # with tolerance.
        actual = np.asarray(PIL.Image.open(actual_image_directory / image.name))
        expected = np.asarray(PIL.Image.open(image))

        # Check that the two images are the same within a tolerance.
        # It's normal for there to be noise in an output image, so it is unlikely that two
        # renders will be exactly the same.

        # Calculate the absolute difference between images
        diff = np.abs(actual.astype(float) - expected.astype(float))
        max_diff = np.max(diff)
        mean_diff = np.mean(diff)

        if not np.allclose(actual, expected, atol=tolerance):
            print(f"MISMATCH: Image '{image.name}' does not match within tolerance {tolerance}")
            print(f"  Max difference: {max_diff:.2f}")
            print(f"  Mean difference: {mean_diff:.2f}")
            print(f"  Required tolerance to pass: {max_diff:.2f}")
            mismatched_count += 1
        else:
            print(
                f"MATCH: Image '{image.name}' matches (max diff: {max_diff:.2f}, mean diff: {mean_diff:.2f})"
            )

    if mismatched_count > max_diff_files:
        print(f"Total mismatched images: {mismatched_count} (max allowed: {max_diff_files})")
        return False

    if mismatched_count > 0:
        print(
            f"Total mismatched images: {mismatched_count} (within allowed threshold of {max_diff_files})"
        )
    else:
        print("All images match!")
    return True


def extract_parameter_value(expected_parameter_values, param_name):
    """
    Helper function that extract parameter value for path convert if needed
    """
    for param in expected_parameter_values["parameterValues"]:
        if param["name"] == param_name:
            return param["value"]
    return None


def are_parameter_values_similar(job_history_dir: Path, expected_parameter_values: dict[str, list]):
    """
    Helper function that asserts that parameter values in the job bundle are what's expected.
    """
    with open(job_history_dir / PARAMETER_VALUES) as actual:
        actual_parameter_values = yaml.safe_load(actual)
        # Compare the lengths so that we can cover the case of duplicate parameters.
        assert len(actual_parameter_values["parameterValues"]) == len(
            expected_parameter_values["parameterValues"]
        )

        # The order of the list of parameter values doesn't matter,
        for parameter_value in expected_parameter_values["parameterValues"]:
            name = parameter_value["name"]
            value = parameter_value["value"]

            # Convert to help with Windows path format
            if not isinstance(value, int):
                value = value.replace("\\", "/")

            assert value == extract_parameter_value(actual_parameter_values, name)


def are_asset_references_similar(
    job_history_dir: Path, expected_asset_references: dict[str, dict[str, Any]]
):
    """
    Helper function that asserts that asset reference values in the job bundle are what's expected.
    """
    with open(job_history_dir / ASSET_REFERENCES) as actual:
        actual_asset_reference = yaml.safe_load(actual)
        # We don't care what order the filenames list is in, so turn it into a set for easier comparison.
        # Compare the lengths before we turn it into a set so that we can cover the case of duplicate assets.
        assert len(actual_asset_reference["assetReferences"]["inputs"]["filenames"]) == len(
            expected_asset_references["assetReferences"]["inputs"]["filenames"]
        )
        actual_asset_reference["assetReferences"]["inputs"]["filenames"] = set(
            actual_asset_reference["assetReferences"]["inputs"]["filenames"]
        )
        directories = expected_asset_references["assetReferences"]["outputs"]["directories"]
        expected_asset_references["assetReferences"]["outputs"]["directories"] = [
            d.replace("\\", "/") for d in directories
        ]
        assert actual_asset_reference == expected_asset_references
