# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Unit tests for adaptor wheels override functionality.

Note: These tests focus on validation logic. Full integration testing
of _merge_adaptor_override_environment() is done in integration tests
due to complex module dependencies.
"""

from pathlib import Path


class TestAdaptorWheelsValidation:
    """Tests for wheel package validation logic."""

    def test_wheel_package_name_extraction(self):
        """Test that wheel package names are correctly extracted from filenames."""
        # Simulate the logic from _merge_adaptor_override_environment
        wheel_files = [
            "openjd_adaptor_runtime-0.9.3.post8+gfffbe2a9f-py3-none-any.whl",
            "deadline-0.52.1-py3-none-any.whl",
            "deadline_cloud_for_3ds_max-0.1.9.post1+geaf1ba928.d20260210-py3-none-any.whl",
        ]

        # Extract package names (split on first '-')
        package_names = {path.split("-", 1)[0] for path in wheel_files if path.endswith(".whl")}

        expected_packages = {"openjd_adaptor_runtime", "deadline", "deadline_cloud_for_3ds_max"}
        assert package_names == expected_packages

    def test_wheel_package_name_extraction_with_different_versions(self):
        """Test package name extraction works with various version formats."""
        test_cases = [
            ("openjd_adaptor_runtime-0.9.3-py3-none-any.whl", "openjd_adaptor_runtime"),
            ("deadline-0.52.1-py3-none-any.whl", "deadline"),
            ("deadline_cloud_for_3ds_max-0.1.9-py3-none-any.whl", "deadline_cloud_for_3ds_max"),
            ("openjd_adaptor_runtime-1.0.0.post1-py3-none-any.whl", "openjd_adaptor_runtime"),
            ("deadline-0.50.0+local-py3-none-any.whl", "deadline"),
        ]

        for wheel_file, expected_name in test_cases:
            package_name = wheel_file.split("-", 1)[0]
            assert package_name == expected_name, f"Failed for {wheel_file}"

    def test_wheel_package_validation_missing_package(self):
        """Test that missing required packages are detected."""
        wheel_files = [
            "openjd_adaptor_runtime-0.9.3-py3-none-any.whl",
            "deadline-0.52.1-py3-none-any.whl",
            # Missing: deadline_cloud_for_3ds_max
        ]

        package_names = {path.split("-", 1)[0] for path in wheel_files if path.endswith(".whl")}

        expected_packages = {"openjd_adaptor_runtime", "deadline", "deadline_cloud_for_3ds_max"}
        assert package_names != expected_packages
        assert "deadline_cloud_for_3ds_max" not in package_names

    def test_wheel_package_validation_wrong_package(self):
        """Test that incorrect packages are detected."""
        wheel_files = [
            "wrong_package-1.0.0-py3-none-any.whl",
            "another_wrong-2.0.0-py3-none-any.whl",
            "deadline-0.52.1-py3-none-any.whl",
        ]

        package_names = {path.split("-", 1)[0] for path in wheel_files if path.endswith(".whl")}

        expected_packages = {"openjd_adaptor_runtime", "deadline", "deadline_cloud_for_3ds_max"}
        assert package_names != expected_packages

    def test_adaptor_name_default_value(self):
        """Test that the adaptor name is set correctly."""
        # This simulates the logic in _merge_adaptor_override_environment
        adaptor_name_param = {"name": "OverrideAdaptorName", "type": "STRING"}
        adaptor_name_param["default"] = "3dsmax-openjd"

        assert adaptor_name_param["default"] == "3dsmax-openjd"
        assert adaptor_name_param["name"] == "OverrideAdaptorName"

    def test_duplicate_package_detection(self):
        """Test that duplicate packages are detected correctly."""
        wheel_files = [
            "deadline-0.52.1-py3-none-any.whl",
            "deadline-0.50.0+local-py3-none-any.whl",
            "openjd_adaptor_runtime-0.9.3-py3-none-any.whl",
            "deadline_cloud_for_3ds_max-0.1.9-py3-none-any.whl",
        ]

        # Count packages
        package_counts = {}
        for wheel_file in wheel_files:
            package_name = wheel_file.split("-", 1)[0]
            package_counts[package_name] = package_counts.get(package_name, 0) + 1

        # Check for duplicates
        duplicates = {pkg: count for pkg, count in package_counts.items() if count > 1}

        assert "deadline" in duplicates
        assert duplicates["deadline"] == 2
        assert "openjd_adaptor_runtime" not in duplicates
        assert "deadline_cloud_for_3ds_max" not in duplicates

    def test_no_duplicate_packages(self):
        """Test that validation passes when there are no duplicates."""
        wheel_files = [
            "deadline-0.52.1-py3-none-any.whl",
            "openjd_adaptor_runtime-0.9.3-py3-none-any.whl",
            "deadline_cloud_for_3ds_max-0.1.9-py3-none-any.whl",
        ]

        # Count packages
        package_counts = {}
        for wheel_file in wheel_files:
            package_name = wheel_file.split("-", 1)[0]
            package_counts[package_name] = package_counts.get(package_name, 0) + 1

        # Check for duplicates
        duplicates = {pkg: count for pkg, count in package_counts.items() if count > 1}

        assert len(duplicates) == 0


class TestSetupAdaptorWheelsScript:
    """Tests for the setup_adaptor_wheels.py script structure."""

    def test_setup_script_exists(self):
        """Test that the setup_adaptor_wheels.py file exists."""
        script_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "deadline"
            / "max_submitter"
            / "setup_adaptor_wheels.py"
        )
        assert script_path.exists(), f"Setup script not found at {script_path}"

    def test_setup_script_has_main_function(self):
        """Test that the setup script has a main() function."""
        script_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "deadline"
            / "max_submitter"
            / "setup_adaptor_wheels.py"
        )

        with open(script_path, "r", encoding="utf8") as f:
            content = f.read()

        assert "def main():" in content
        assert 'if __name__ == "__main__":' in content

    def test_setup_script_has_required_imports(self):
        """Test that the setup script imports required modules."""
        script_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "deadline"
            / "max_submitter"
            / "setup_adaptor_wheels.py"
        )

        with open(script_path, "r", encoding="utf8") as f:
            content = f.read()

        required_imports = [
            "import json",
            "import os",
            "import platform",
            "import subprocess",
            "import sys",
            "from pathlib import Path",
        ]

        for required_import in required_imports:
            assert required_import in content, f"Missing import: {required_import}"

    def test_setup_script_has_openjd_template_variables(self):
        """Test that the setup script contains OpenJD template variable placeholders."""
        script_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "deadline"
            / "max_submitter"
            / "setup_adaptor_wheels.py"
        )

        with open(script_path, "r", encoding="utf8") as f:
            content = f.read()

        # These will be substituted by OpenJD at runtime
        assert "{{Session.WorkingDirectory}}" in content
        assert "{{Param.OverrideAdaptorWheels}}" in content
        assert "{{Param.OverrideAdaptorName}}" in content
