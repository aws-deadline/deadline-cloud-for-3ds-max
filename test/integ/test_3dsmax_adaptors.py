# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path

import pytest
import yaml
from flaky import flaky

from .helpers.output_comparison import are_images_similar
from .helpers.test_runners import run_adaptor_test
from .test_pathmapping import update_path_mapping_for_checkout

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
            "State01_OutputFileFormat": ".jpg",
            "State01_Frames": "1-2",
            "State01_ImageWidth": 1280,
            "State01_ImageHeight": 720,
            "State01_OutputFilePath": str(output_path),
            "State01_OutputFileName": "<stateset>_test_###_<camera>",
        }

        run_adaptor_test(test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE, job_params)
        assert are_images_similar(
            expected_image_directory=test_file_location / EXPECTED_OUTPUT_FOLDER,
            actual_image_directory=output_path,
            tolerance=2,
        )


@pytest.mark.adaptor
@flaky(max_runs=3, min_passes=1)
class TestBatchRenderAdaptors:
    """
    Tests that the 3dsMax adaptor correctly handles batch render jobs.

    Runs all batch render steps from the batch_render_test template in a single
    render pass and verifies the output images match expected results.
    """

    def test_batch_render_adaptor(self, script_location: Path, tmp_path: Path) -> None:
        """
        Run all 4 batch render steps via the full template and verify
        the output images match expected results.
        """
        test_file_location = script_location / "batch_render_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "BatchRenderTest2024.max"
        output_path = tmp_path / OUTPUT_FOLDER

        job_params = _load_job_params(test_file_location)
        job_params["MaxSceneFile"] = str(scene_location)

        # Point all steps' output to the same flat directory
        step_param_prefixes = [
            "B1_cam_only",
            "B2_with_state",
            "B3_with_preset",
            "B4_with_override",
        ]
        for prefix in step_param_prefixes:
            job_params[f"{prefix}_OutputFilePath"] = str(output_path)

        # Load path mapping rules for the preset step
        path_mapping_rules = None
        path_mapping_file = test_file_location / "path_mapping_rules.json"
        if path_mapping_file.exists():
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
            path_mapping_rules = update_path_mapping_for_checkout(path_mapping_file, checkout_root)

        full_template = test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE
        run_adaptor_test(full_template, job_params, path_mapping_rules)

        assert are_images_similar(
            expected_image_directory=test_file_location / EXPECTED_OUTPUT_FOLDER,
            actual_image_directory=output_path,
            tolerance=2,
        )

    def test_batch_render_missing_scene_state_adaptor(
        self, script_location: Path, tmp_path: Path
    ) -> None:
        """
        BE-1: Verify the adaptor raises a RuntimeError when a nonexistent scene state
        is specified in init-data.

        Modifies the with_state step's init-data to reference 'NonExistentState',
        which does not exist in the scene. The adaptor should fail with an error message
        indicating the scene state was not found.
        """
        test_file_location = script_location / "batch_render_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "BatchRenderTest2024.max"

        job_params = _load_job_params(test_file_location)
        job_params["MaxSceneFile"] = str(scene_location)

        full_template = test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE
        error_template = _create_error_template(
            full_template,
            "with_state",
            {"scene_state": "NonExistentState"},
            tmp_path,
        )

        output = run_adaptor_test(error_template, job_params, expect_failure=True)
        assert (
            "Scene State 'NonExistentState' does not exist in the scene" in output
            or "Failed to restore scene state 'NonExistentState'" in output
        ), f"Expected error about missing scene state, got:\n{output}"

    def test_batch_render_missing_preset_file_adaptor(
        self, script_location: Path, tmp_path: Path
    ) -> None:
        """
        BE-2: Verify the adaptor raises a RuntimeError when a nonexistent preset file
        is specified in init-data.

        Modifies the with_preset step's init-data to reference '/nonexistent/path.rps',
        which does not exist on disk. The adaptor should fail with an error message
        indicating the preset file was not found.
        """
        test_file_location = script_location / "batch_render_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "BatchRenderTest2024.max"

        job_params = _load_job_params(test_file_location)
        job_params["MaxSceneFile"] = str(scene_location)

        full_template = test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE
        error_template = _create_error_template(
            full_template,
            "with_preset",
            {"preset_file": "/nonexistent/path.rps"},
            tmp_path,
        )

        output = run_adaptor_test(error_template, job_params, expect_failure=True)
        assert (
            "Preset file '/nonexistent/path.rps' does not exist after path mapping" in output
        ), f"Expected error about missing preset file, got:\n{output}"

    def test_batch_render_invalid_pixel_aspect_adaptor(
        self, script_location: Path, tmp_path: Path
    ) -> None:
        """
        BE-3: Verify the adaptor raises a RuntimeError when an invalid pixel aspect
        value is specified in init-data.

        Modifies the with_override step's init-data to set pixel_aspect to '-1.0',
        which is not a valid positive number. The adaptor should fail with an error message
        indicating the pixel aspect is invalid.
        """
        test_file_location = script_location / "batch_render_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "BatchRenderTest2024.max"

        job_params = _load_job_params(test_file_location)
        job_params["MaxSceneFile"] = str(scene_location)

        full_template = test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE
        error_template = _create_error_template(
            full_template,
            "with_override",
            {"pixel_aspect": "-1.0"},
            tmp_path,
        )

        output = run_adaptor_test(error_template, job_params, expect_failure=True)
        assert (
            "Invalid pixel aspect: -1.0 (must be a positive number)" in output
        ), f"Expected error about invalid pixel aspect, got:\n{output}"


def _load_job_params(test_file_location: Path) -> dict:
    """
    Load job parameters from the parameter_values.yaml file in the expected job bundle.

    Returns a dict of param_name -> param_value, following the same pattern
    as test_3dsmax_render_elements.py.
    """
    parameter_values_path = (
        test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / "parameter_values.yaml"
    )
    with open(parameter_values_path, "r") as f:
        parameter_data = yaml.safe_load(f)

    job_params = {}
    for param in parameter_data["parameterValues"]:
        job_params[param["name"]] = param["value"]

    return job_params


def _create_error_template(
    base_template_path: Path,
    step_name: str,
    init_data_overrides: dict,
    output_path: Path,
) -> Path:
    """
    Create a modified single-step template with altered init-data for error testing.

    Takes the full batch_render_test template, extracts the specified step, and
    applies key-value overrides to the init-data string using line-based replacement
    (avoids YAML parsing issues with OpenJD template expressions like {{Param.X}}).

    Args:
        base_template_path: Path to the full batch render template with all steps.
        step_name: Name of the step to extract and modify.
        init_data_overrides: Dict of init-data keys to override (e.g. {"scene_state": "NonExistentState"}).
        output_path: Directory where the temporary template file will be written.

    Returns:
        Path to the newly created modified template file.
    """
    with open(base_template_path) as f:
        template = yaml.safe_load(f)

    # Extract the target step
    matching_steps = [s for s in template["steps"] if s["name"] == step_name]
    assert (
        len(matching_steps) == 1
    ), f"Expected exactly 1 step named '{step_name}', found {len(matching_steps)}"
    template["steps"] = matching_steps

    # Find and modify the init-data embedded file
    step = template["steps"][0]
    step_env = step["stepEnvironments"][0]
    embedded_files = step_env["script"]["embeddedFiles"]

    for ef in embedded_files:
        if ef["name"] == "initData":
            # Replace values using line-based substitution to avoid YAML parsing
            # issues with OpenJD template expressions (e.g. {{Param.MaxSceneFile}})
            lines = ef["data"].splitlines(keepends=True)
            new_lines = []
            for line in lines:
                replaced = False
                for key, value in init_data_overrides.items():
                    if line.lstrip().startswith(f"{key}:"):
                        new_lines.append(f"{key}: '{value}'\n")
                        replaced = True
                        break
                if not replaced:
                    new_lines.append(line)
            ef["data"] = "".join(new_lines)
            break

    error_template_path = output_path / f"template_error_{step_name}.yaml"
    with open(error_template_path, "w") as f:
        yaml.dump(template, f, default_flow_style=False, sort_keys=False)

    return error_template_path
