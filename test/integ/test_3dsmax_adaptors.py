# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path

import pytest
from flaky import flaky

from .helpers.output_comparison import are_images_similar
from .helpers.test_runners import run_adaptor_test

from test.integ.test_const import (
    TEMPLATE,
    TEST_SCENE_FOLDER,
    OUTPUT_FOLDER,
    EXPECTED_JOB_BUNDLE_FOLDER,
    EXPECTED_OUTPUT_FOLDER,
)


@pytest.mark.adaptor
@flaky(max_runs=3, min_passes=1)
class TestAdaptors:
    """
    This class tests that the 3dsMax adaptor can correctly handle relevant types of jobs
    """

    def test_minimal_scene_adaptor(self, script_location: Path, tmp_path: Path) -> None:
        test_file_location = script_location / "minimal_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "test.max"
        output_path = tmp_path / OUTPUT_FOLDER

        job_params = {
            "MaxSceneFile": str(scene_location),
            "OutputFileFormat": ".jpg",
            "Frames": "1-2",
            "ImageWidth": 1280,
            "ImageHeight": 720,
            "OutputFilePath": str(output_path),
        }

        run_adaptor_test(test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE, job_params)
        assert are_images_similar(
            expected_image_directory=test_file_location / EXPECTED_OUTPUT_FOLDER,
            actual_image_directory=output_path,
            tolerance=2,
        )
