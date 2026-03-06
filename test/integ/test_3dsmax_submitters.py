# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import yaml
import os
import sys
from deadline.max_adaptor.executable_handler import MaxExecutableHandler
import pytest

from pathlib import Path
from typing import Any

from .helpers.test_runners import is_valid_template, run_submitter_test
from .helpers.output_comparison import are_parameter_values_similar, are_asset_references_similar

from .test_const import (
    STICKY_SETTING,
    JOB_HISTORY_FOLDER,
    TEST_SCENE_FOLDER,
    TEMPLATE,
    EXPECTED_JOB_BUNDLE_FOLDER,
)


@pytest.mark.submitter
class TestSubmitters:
    """
    Tests that ensure submitters produce the correct job bundle given a scene file.
    """

    @pytest.fixture(autouse=True)
    def _add_submitter_to_pythonpath(self):
        # Resolve the relative path from the current script location
        submitter_path = Path(__file__).resolve().parents[2] / "src" / "deadline" / "max_submitter"
        submitter_path_str = str(submitter_path)

        # Add to PYTHONPATH if not already included
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        pythonpath_entries = current_pythonpath.split(os.pathsep) if current_pythonpath else []

        if submitter_path_str not in pythonpath_entries:
            pythonpath_entries.append(submitter_path_str)
            os.environ["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)

        # Add to sys.path if not already included
        if submitter_path_str not in sys.path:
            sys.path.append(submitter_path_str)

    def _cleanup_sticky_settings(self, scene_file: Path, script_location: Path):
        """
        We need to clean the sticky settings before the test runs so that we can ensure
        a clean environment.
        """

        sticky_settings_location = scene_file.with_name(f"{scene_file.stem}.{STICKY_SETTING}")
        Path(script_location / sticky_settings_location).unlink(missing_ok=True)

    def test_minimal_scene_submitter(self, script_location: Path, tmp_path: Path) -> None:

        job_history_dir = tmp_path / JOB_HISTORY_FOLDER
        output_path = script_location / "minimal_test" / TEST_SCENE_FOLDER
        scene_location = script_location / "minimal_test" / TEST_SCENE_FOLDER / "test.max"

        # Clean up test
        self._cleanup_sticky_settings(scene_location, script_location)

        os.makedirs(job_history_dir, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)

        max_exec = MaxExecutableHandler()

        run_submitter_test(
            max_exec.max_executable.full_path,
            str(script_location / "minimal_test" / "_test_max.py"),
            str(scene_location),
            str(job_history_dir),
            str(output_path),
        )

        # Check that we have a valid template
        assert is_valid_template(job_history_dir / TEMPLATE)

        # Check that the template is as expected.
        with (
            open(
                script_location / "minimal_test" / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE
            ) as expected,
            open(job_history_dir / TEMPLATE) as actual,
        ):
            assert yaml.safe_load(expected) == yaml.safe_load(actual)

        # Check that the parameter values are as expected.
        expected_parameter_values = {
            "parameterValues": [
                {"name": "MaxSceneFile", "value": str(scene_location)},
                {"name": "Frames", "value": "1-2"},
                {"name": "OutputFilePath", "value": str(output_path) + "/"},
                {"name": "OutputFileName", "value": "<stateset>_test_###_<camera>"},
                {"name": "OutputFileFormat", "value": ".jpg"},
                {"name": "ImageWidth", "value": 1280},
                {"name": "ImageHeight", "value": 720},
                {"name": "deadline:targetTaskRunStatus", "value": "READY"},
                {"name": "deadline:maxFailedTasksCount", "value": 20},
                {"name": "deadline:maxRetriesPerTask", "value": 5},
                {"name": "deadline:priority", "value": 50},
            ]
        }

        are_parameter_values_similar(job_history_dir, expected_parameter_values)

        # Check that the asset references are as expected.
        expected_asset_references: dict[str, dict[str, Any]] = {
            "assetReferences": {
                "inputs": {
                    "directories": [],
                    "filenames": {str(scene_location)},
                },
                "outputs": {
                    "directories": [str(output_path) + "/"],
                },
                "referencedPaths": [],
            }
        }

        are_asset_references_similar(job_history_dir, expected_asset_references)
