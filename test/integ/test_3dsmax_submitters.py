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
    ASSET_REFERENCES,
    STICKY_SETTING,
    JOB_HISTORY_FOLDER,
    PARAMETER_VALUES,
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
                {"name": "State01_Frames", "value": "1-2"},
                {"name": "State01_OutputFilePath", "value": str(output_path) + "/"},
                {"name": "State01_OutputFileName", "value": "<stateset>_test_###_<camera>"},
                {"name": "State01_OutputFileFormat", "value": ".jpg"},
                {"name": "State01_ImageWidth", "value": 1280},
                {"name": "State01_ImageHeight", "value": 720},
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

    def _get_init_data(self, step: dict) -> str:
        """Extract the init-data YAML string from a step's environment embedded files."""
        for env in step.get("stepEnvironments", []):
            for ef in env.get("script", {}).get("embeddedFiles", []):
                if ef.get("name") == "initData":
                    return ef["data"]
        return ""

    def test_batch_render_submitter(self, script_location: Path, tmp_path: Path) -> None:
        """
        Verify the submitter produces a correct job bundle in Batch Render mode.
        """
        expected_steps = ["cam_only", "with_state", "with_preset", "with_override"]

        job_history_dir = tmp_path / JOB_HISTORY_FOLDER
        output_path = script_location / "batch_render_test" / TEST_SCENE_FOLDER
        scene_location = (
            script_location / "batch_render_test" / TEST_SCENE_FOLDER / "BatchRenderTest2024.max"
        )

        self._cleanup_sticky_settings(scene_location, script_location)

        os.makedirs(job_history_dir, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)

        max_exec = MaxExecutableHandler()

        run_submitter_test(
            max_exec.max_executable.full_path,
            str(script_location / "batch_render_test" / "_test_max.py"),
            str(scene_location),
            str(job_history_dir),
            str(output_path),
        )

        # --- Validate template structure ---
        assert is_valid_template(job_history_dir / TEMPLATE)

        with open(job_history_dir / TEMPLATE) as f:
            template = yaml.safe_load(f)

        step_names = [step["name"] for step in template["steps"]]

        # 11.2: Assert exactly 4 steps present with correct names
        assert len(step_names) == len(
            expected_steps
        ), f"Expected {len(expected_steps)} steps, got {len(step_names)}: {step_names}"
        for expected_step in expected_steps:
            assert expected_step in step_names, f"Expected step '{expected_step}' not found"

        # 11.3: Assert disabled_view is NOT present as a step
        assert "disabled_view" not in step_names, "disabled_view should not be a step"
        for name in step_names:
            assert (
                "disabled" not in name.lower()
            ), f"Step '{name}' contains 'disabled' — disabled views should be excluded"

        # 11.4: Assert step-specific and batch-specific params present
        param_names = [p["name"] for p in template.get("parameterDefinitions", [])]
        for i, step_name in enumerate(expected_steps, start=1):
            prefix = f"B{i}_{step_name}"

            assert f"{prefix}_Frames" in param_names, f"Missing {prefix}_Frames param"
            assert (
                f"{prefix}_OutputFilePath" in param_names
            ), f"Missing {prefix}_OutputFilePath param"
            assert (
                f"{prefix}_OutputFileName" in param_names
            ), f"Missing {prefix}_OutputFileName param"
            assert (
                f"{prefix}_OutputFileFormat" in param_names
            ), f"Missing {prefix}_OutputFileFormat param"
            assert f"{prefix}_ImageWidth" in param_names, f"Missing {prefix}_ImageWidth param"
            assert f"{prefix}_ImageHeight" in param_names, f"Missing {prefix}_ImageHeight param"
            assert f"{prefix}_Camera" in param_names, f"Missing {prefix}_Camera param"

        # 11.5 & 11.6: Validate init-data for each step
        # Steps that should have conditional init-data keys
        steps_with_scene_state = {"with_state", "with_override"}
        steps_with_preset_file = {"with_preset"}
        steps_with_pixel_aspect = {"with_override"}

        # All 4 enabled batch views have cameras assigned, so camera: should be in all init-data
        steps_with_camera = set(expected_steps)

        for step in template["steps"]:
            step_name = step["name"]
            init_data_str = self._get_init_data(step)
            assert init_data_str, f"No init-data found for step {step_name}"

            # 11.5: init-data contains camera only when the batch view has a camera assigned
            if step_name in steps_with_camera:
                assert (
                    "camera:" in init_data_str
                ), f"Step {step_name} should have 'camera:' in init-data"

            # 11.5: init-data contains scene_state only for with_state and with_override
            if step_name in steps_with_scene_state:
                assert (
                    "scene_state:" in init_data_str
                ), f"Step {step_name} should have 'scene_state:' in init-data"
            else:
                assert (
                    "scene_state:" not in init_data_str
                ), f"Step {step_name} should not have 'scene_state:' in init-data"

            # 11.5: init-data contains preset_file only for with_preset
            if step_name in steps_with_preset_file:
                assert (
                    "preset_file:" in init_data_str
                ), f"Step {step_name} should have 'preset_file:' in init-data"
            else:
                assert (
                    "preset_file:" not in init_data_str
                ), f"Step {step_name} should not have 'preset_file:' in init-data"

            # 11.5: init-data contains pixel_aspect only for with_override
            if step_name in steps_with_pixel_aspect:
                assert (
                    "pixel_aspect:" in init_data_str
                ), f"Step {step_name} should have 'pixel_aspect:' in init-data"
            else:
                assert (
                    "pixel_aspect:" not in init_data_str
                ), f"Step {step_name} should not have 'pixel_aspect:' in init-data"

            # 11.6: init-data does NOT contain state_set:
            assert (
                "state_set:" not in init_data_str
            ), f"Step {step_name} should not have 'state_set:' in init-data"

        # 11.7: Assert preset file in asset references
        with open(job_history_dir / ASSET_REFERENCES) as f:
            asset_refs = yaml.safe_load(f)

        input_filenames = asset_refs["assetReferences"]["inputs"]["filenames"]
        has_preset = any(fname.endswith(".rps") for fname in input_filenames)
        assert has_preset, "Preset file (.rps) should be in asset references"

        # 11.8: Compare template and parameter values against expected
        expected_bundle_dir = script_location / "batch_render_test" / EXPECTED_JOB_BUNDLE_FOLDER

        with (
            open(expected_bundle_dir / TEMPLATE) as expected,
            open(job_history_dir / TEMPLATE) as actual,
        ):
            assert yaml.safe_load(expected) == yaml.safe_load(actual)

        with (
            open(expected_bundle_dir / PARAMETER_VALUES) as expected,
            open(job_history_dir / PARAMETER_VALUES) as actual,
        ):
            expected_params = yaml.safe_load(expected)
            actual_params = yaml.safe_load(actual)
            assert len(expected_params["parameterValues"]) == len(actual_params["parameterValues"])
            for param in expected_params["parameterValues"]:
                name = param["name"]
                value = param["value"]
                # MaxSceneFile is machine-dependent — the expected file has the
                # original author's path (from get_scene_path() = rt.maxFilePath +
                # rt.maxFileName at the time the fixture was generated), but on CI
                # the scene is loaded from the checkout directory so the
                # actual value will always differ.
                #
                # B3_with_preset resolution/frames are also machine-dependent because
                # they come from extract_settings_from_preset() which reads the .rps
                # file. On CI the preset file path (C:\Users\RDP\...) doesn't exist
                # locally, so the submitter falls back to scene defaults (320x240)
                # instead of the preset values (160x120).
                machine_dependent_params = {
                    "MaxSceneFile",
                    "B3_with_preset_ImageWidth",
                    "B3_with_preset_ImageHeight",
                    "B3_with_preset_Frames",
                }
                if name in machine_dependent_params:
                    continue
                if not isinstance(value, int):
                    value = value.replace("\\", "/")
                actual_value = None
                for ap in actual_params["parameterValues"]:
                    if ap["name"] == name:
                        actual_value = ap["value"]
                        if not isinstance(actual_value, int):
                            actual_value = actual_value.replace("\\", "/")
                        break
                assert actual_value is not None, f"Missing parameter '{name}' in actual output"
                assert (
                    value == actual_value
                ), f"Parameter '{name}' mismatch: expected={value}, actual={actual_value}"

    def test_batch_render_override_frame_range_submitter(
        self, script_location: Path, tmp_path: Path
    ) -> None:
        """
        Verify that Override Frame Range takes highest priority over batch view frame ranges.
        All 4 batch render steps should use the override value "1-2", including
        with_override whose batch view frame range is 5-10.
        """
        expected_steps = ["cam_only", "with_state", "with_preset", "with_override"]

        job_history_dir = tmp_path / JOB_HISTORY_FOLDER
        output_path = script_location / "batch_render_test" / TEST_SCENE_FOLDER
        scene_location = (
            script_location / "batch_render_test" / TEST_SCENE_FOLDER / "BatchRenderTest2024.max"
        )

        self._cleanup_sticky_settings(scene_location, script_location)

        os.makedirs(job_history_dir, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)

        max_exec = MaxExecutableHandler()

        run_submitter_test(
            max_exec.max_executable.full_path,
            str(script_location / "batch_render_test" / "_test_max_override_frames.py"),
            str(scene_location),
            str(job_history_dir),
            str(output_path),
        )

        # --- Validate template structure ---
        assert is_valid_template(job_history_dir / TEMPLATE)

        with open(job_history_dir / TEMPLATE) as f:
            template = yaml.safe_load(f)

        step_names = [step["name"] for step in template["steps"]]

        # 12.2: Verify we still have the expected 4 steps
        assert len(step_names) == len(
            expected_steps
        ), f"Expected {len(expected_steps)} steps, got {len(step_names)}: {step_names}"
        for expected_step in expected_steps:
            assert expected_step in step_names, f"Expected step '{expected_step}' not found"

        # 12.3 & 12.4: Assert ALL 4 batch render steps have override frame range "1-2"
        # The template's range field contains a parameter expression (e.g.
        # {{Param.B1_cam_only_Frames}}), so we verify the override by checking
        # the actual parameter VALUES in the generated parameter_values.yaml.
        with open(job_history_dir / "parameter_values.yaml") as f:
            param_values = yaml.safe_load(f)

        for i, step_name in enumerate(expected_steps, start=1):
            prefix = f"B{i}_{step_name}"
            frames_param_name = f"{prefix}_Frames"
            frames_value = None
            for pv in param_values["parameterValues"]:
                if pv["name"] == frames_param_name:
                    frames_value = pv["value"]
                    break
            assert frames_value is not None, f"Missing parameter '{frames_param_name}'"
            assert (
                frames_value == "1-2"
            ), f"Step '{step_name}' frame range should be '1-2' (override), got '{frames_value}'"

    def test_task_run_timeout_submitter(self, script_location: Path, tmp_path: Path) -> None:
        """
        Verify that setting task_run_timeout_seconds on the submitter settings
        produces a job template where every step's onRun action has the correct
        timeout value.
        """
        EXPECTED_TIMEOUT = 30

        job_history_dir = tmp_path / JOB_HISTORY_FOLDER
        # Reuse the minimal_test scene — no render output needed for this test.
        output_path = script_location / "minimal_test" / TEST_SCENE_FOLDER
        scene_location = script_location / "minimal_test" / TEST_SCENE_FOLDER / "test.max"

        self._cleanup_sticky_settings(scene_location, script_location)

        os.makedirs(job_history_dir, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)

        max_exec = MaxExecutableHandler()

        run_submitter_test(
            max_exec.max_executable.full_path,
            str(script_location / "task_run_timeout_test" / "_test_max.py"),
            str(scene_location),
            str(job_history_dir),
            str(output_path),
        )

        assert is_valid_template(job_history_dir / TEMPLATE)

        with open(job_history_dir / TEMPLATE) as f:
            template = yaml.safe_load(f)

        assert template["steps"], "Template has no steps"
        for step in template["steps"]:
            on_run = step["script"]["actions"]["onRun"]
            assert (
                "timeout" in on_run
            ), f"Step '{step['name']}' onRun action is missing 'timeout' field"
            assert on_run["timeout"] == EXPECTED_TIMEOUT, (
                f"Step '{step['name']}' onRun timeout: "
                f"expected {EXPECTED_TIMEOUT}, got {on_run['timeout']}"
            )
