# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Integration tests for the V-Ray Standalone submitter (PR #244)."""

import json
import os
import sys
import yaml

from pathlib import Path

import pytest

from deadline.max_adaptor.executable_handler import MaxExecutableHandler

from .helpers.test_runners import is_valid_template, run_submitter_test
from .test_const import (
    JOB_HISTORY_FOLDER,
    PARAMETER_VALUES,
    TEMPLATE,
    TEST_SCENE_FOLDER,
)


# fog.max from the render-elements suite already has V-Ray as the active
# renderer. Sticky-settings filenames don't collide between the two suites.
VRAY_SCENE_DIR = "vray_re_test"
VRAY_SCENE_FILE = "fog.max"
VRAY_STICKY_SETTINGS = "fog.deadline_vrscene_settings.json"

DRIVER_SCRIPT = "_test_driver.py"
CONFIG_FILE = "test_config.json"


def _expected_param(parameter_values, name):
    for entry in parameter_values["parameterValues"]:
        if entry["name"] == name:
            return entry["value"]
    return None


def _config(
    *,
    render_engine: int,
    rt_timeout: float = 0.0,
    rt_noise: float = 0.001,
    rt_sample_level: int = 0,
    region_columns: int = 1,
    region_rows: int = 1,
    expect_failure: bool = False,
) -> dict:
    return {
        "render_engine": render_engine,
        "rt_timeout": rt_timeout,
        "rt_noise": rt_noise,
        "rt_sample_level": rt_sample_level,
        "region_columns": region_columns,
        "region_rows": region_rows,
        "expect_failure": expect_failure,
    }


@pytest.mark.submitter
class TestVRayStandaloneSubmitter:

    @pytest.fixture(autouse=True)
    def _add_submitter_to_pythonpath(self):
        # Per DEVELOPMENT.md, both <repo>/src and <repo>/src/deadline/max_submitter
        # need to be on PYTHONPATH. Prepend so local source wins over any
        # stale copy in 3ds Max's site-packages.
        src_path = Path(__file__).resolve().parents[2] / "src"
        submitter_path = src_path / "deadline" / "max_submitter"

        for path in (submitter_path, src_path):
            path_str = str(path)

            current_pythonpath = os.environ.get("PYTHONPATH", "")
            entries = current_pythonpath.split(os.pathsep) if current_pythonpath else []
            if path_str in entries:
                entries.remove(path_str)
            entries.insert(0, path_str)
            os.environ["PYTHONPATH"] = os.pathsep.join(entries)

            if path_str in sys.path:
                sys.path.remove(path_str)
            sys.path.insert(0, path_str)

    def _cleanup_sticky_settings(self, scene_file: Path):
        Path(scene_file.parent / VRAY_STICKY_SETTINGS).unlink(missing_ok=True)

    def _run_driver(self, script_location: Path, config: dict, tmp_path: Path) -> Path:
        job_history_dir = tmp_path / JOB_HISTORY_FOLDER
        scene_dir = script_location / VRAY_SCENE_DIR / TEST_SCENE_FOLDER
        scene_location = scene_dir / VRAY_SCENE_FILE
        output_path = scene_dir

        self._cleanup_sticky_settings(scene_location)

        os.makedirs(job_history_dir, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)

        with open(job_history_dir / CONFIG_FILE, "w", encoding="utf8") as f:
            json.dump(config, f)

        run_submitter_test(
            MaxExecutableHandler().max_executable.full_path,
            str(script_location / "vray_standalone_test" / DRIVER_SCRIPT),
            str(scene_location),
            str(job_history_dir),
            str(output_path),
        )

        return job_history_dir

    def _load_bundle(self, job_history_dir: Path) -> tuple[dict, dict]:
        assert is_valid_template(job_history_dir / TEMPLATE)
        with open(job_history_dir / TEMPLATE) as f:
            template = yaml.safe_load(f)
        with open(job_history_dir / PARAMETER_VALUES) as f:
            parameter_values = yaml.safe_load(f)
        return template, parameter_values

    def test_vray_standalone_cuda_no_tile_submitter(
        self, script_location: Path, tmp_path: Path
    ) -> None:
        job_history_dir = self._run_driver(
            script_location,
            _config(
                render_engine=5,
                rt_timeout=30.0,
                rt_noise=0.005,
                rt_sample_level=1024,
            ),
            tmp_path,
        )
        template, parameter_values = self._load_bundle(job_history_dir)

        step_names = [step["name"] for step in template["steps"]]
        assert "ExportVRScene" in step_names
        assert any("Render" in name and "Region" not in name for name in step_names)

        param_defs = {p["name"]: p for p in template.get("parameterDefinitions", [])}
        assert param_defs["RenderEngine"]["type"] == "INT"
        assert param_defs["RenderEngine"]["allowedValues"] == [0, 5, 7]
        for rt_param, rt_type in (
            ("RTTimeout", "FLOAT"),
            ("RTNoise", "FLOAT"),
            ("RTSampleLevel", "INT"),
        ):
            assert param_defs[rt_param]["type"] == rt_type

        assert _expected_param(parameter_values, "RenderEngine") == "5"
        assert _expected_param(parameter_values, "RTTimeout") == "30.0"
        assert _expected_param(parameter_values, "RTNoise") == "0.005"
        assert _expected_param(parameter_values, "RTSampleLevel") == "1024"
        assert _expected_param(parameter_values, "RegionColumns") == "1"
        assert _expected_param(parameter_values, "RegionRows") == "1"

    def test_vray_standalone_cpu_default_submitter(
        self, script_location: Path, tmp_path: Path
    ) -> None:
        job_history_dir = self._run_driver(
            script_location,
            _config(render_engine=0),
            tmp_path,
        )
        template, parameter_values = self._load_bundle(job_history_dir)

        param_defs = {p["name"]: p for p in template.get("parameterDefinitions", [])}
        for required in ("RenderEngine", "RTTimeout", "RTNoise", "RTSampleLevel"):
            assert required in param_defs
        assert param_defs["RenderEngine"]["allowedValues"] == [0, 5, 7]

        assert _expected_param(parameter_values, "RenderEngine") == "0"
        assert _expected_param(parameter_values, "RTTimeout") == "0.0"
        assert _expected_param(parameter_values, "RTNoise") == "0.001"
        assert _expected_param(parameter_values, "RTSampleLevel") == "0"

    def test_vray_standalone_invalid_engine_rejected(
        self, script_location: Path, tmp_path: Path
    ) -> None:
        job_history_dir = self._run_driver(
            script_location,
            _config(render_engine=99, expect_failure=True),
            tmp_path,
        )

        assert not (job_history_dir / TEMPLATE).exists()

        outcome_file = job_history_dir / "validation_outcome.txt"
        assert outcome_file.exists()

        outcome = outcome_file.read_text(encoding="utf8")
        assert outcome.startswith("VALIDATION_FAILED")
        assert "Invalid render engine" in outcome

    def test_vray_standalone_rtx_tile_submitter(
        self, script_location: Path, tmp_path: Path
    ) -> None:
        job_history_dir = self._run_driver(
            script_location,
            _config(
                render_engine=7,
                rt_timeout=60.0,
                rt_noise=0.002,
                rt_sample_level=2048,
                region_columns=2,
                region_rows=2,
            ),
            tmp_path,
        )
        template, parameter_values = self._load_bundle(job_history_dir)

        step_names = [step["name"] for step in template["steps"]]
        assert "ExportVRScene" in step_names
        assert any("Region" in name for name in step_names)

        param_defs = {p["name"]: p for p in template.get("parameterDefinitions", [])}
        assert param_defs["RenderEngine"]["allowedValues"] == [0, 5, 7]
        for rt_param in ("RTTimeout", "RTNoise", "RTSampleLevel"):
            assert rt_param in param_defs

        assert _expected_param(parameter_values, "RenderEngine") == "7"
        assert _expected_param(parameter_values, "RTTimeout") == "60.0"
        assert _expected_param(parameter_values, "RTNoise") == "0.002"
        assert _expected_param(parameter_values, "RTSampleLevel") == "2048"
        assert _expected_param(parameter_values, "RegionColumns") == "2"
        assert _expected_param(parameter_values, "RegionRows") == "2"
