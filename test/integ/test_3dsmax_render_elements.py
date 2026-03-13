# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path
import yaml

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
@flaky(max_runs=1, min_passes=1)
class TestRenderElementsAdaptors:
    """
    This class tests that the 3dsMax adaptor can correctly handle relevant types of jobs
    """

    @pytest.mark.parametrize(
        "bundle_dir,scene_max,max_diff_files",
        [
            pytest.param(
                "vray_re_test",
                "fog.max",
                6,
                marks=pytest.mark.xfail(
                    reason="Known flaky V-Ray render elements test", strict=False
                ),
            ),
            ("re_enabled_test", "fog.max", 0),
            ("re_disabled_test", "fog.max", 0),
            ("lightmix", "scene.max", 4),
        ],
    )
    def test_render_element_scene_adaptor(
        self,
        script_location: Path,
        tmp_path: Path,
        bundle_dir: str,
        scene_max: str,
        max_diff_files: int,
    ) -> None:
        test_file_location = script_location / bundle_dir
        scene_location = test_file_location / TEST_SCENE_FOLDER / scene_max
        output_path = tmp_path / OUTPUT_FOLDER

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

        # Override only MaxSceneFile and State01_OutputFilePath from test parameters
        job_params["MaxSceneFile"] = str(scene_location)
        job_params["State01_OutputFilePath"] = str(output_path)

        run_adaptor_test(test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE, job_params)
        assert are_images_similar(
            expected_image_directory=test_file_location / EXPECTED_OUTPUT_FOLDER,
            actual_image_directory=output_path,
            tolerance=25,
            max_diff_files=max_diff_files,
        )
