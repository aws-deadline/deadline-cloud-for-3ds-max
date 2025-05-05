# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import subprocess
import yaml
import json
import re

from pathlib import Path
from typing import Any


def run_command(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    """
    Helper function to log, run command and also print out output, error for better debug
    """
    output = subprocess.run(args, capture_output=True)

    print(f"Ran the following: {' '.join(output.args)}")
    print(f"\nstdout:\n\n{output.stdout.decode('utf-8', errors='replace')}")
    print(f"\nstderr:\n\n{output.stderr.decode('utf-8', errors='replace')}")

    return output


def is_valid_template(template_location: Path) -> bool:
    """
    Helper function to run openjd CLI "check" command to check correctness of template.yaml file
    """
    output = run_command(["openjd", "check", str(template_location), "--output", "json"])

    decoded_stdout = output.stdout.decode("utf-8")

    # Regex to extract part of the stdout that follow json format by matching "{", "}" and anything inside.
    # This is because some stdout might contain other log beside just the json format output from openjd CLI
    match = re.search(r"\{.*\}", decoded_stdout, re.DOTALL)
    if not match:
        return False

    json_str = match.group(0)
    output_json = json.loads(json_str)

    return output_json["status"] == "success"


def run_submitter_test(
    max_location: str,
    test_script_location: str,
    scene_location: str,
    job_history_dir: str,
    output_path: str,
) -> subprocess.CompletedProcess[bytes]:
    """
    Function to run the submitter test by passing a script with parameters to 3dsmax batch
    """
    args = [
        max_location,
        test_script_location,
        "-sceneFile",
        scene_location,
        "-mxsString",
        f"job_history_dir:{job_history_dir}",
        "-mxsString",
        f"output_dir:{output_path}",
        "-v",
        "5",
    ]

    return run_command(args)


def run_adaptor_test(template_path: Path, job_params: dict[str, Any]) -> None:
    """
    Function to use openjd CLI "run" command to run the 3dsmax adaptor to render image
    """
    with open(template_path) as f:
        template = yaml.safe_load(f)

    for step in template["steps"]:
        output = run_command(
            [
                "openjd",
                "run",
                str(template_path),
                "--step",
                step["name"],
                "--job-param",
                json.dumps(job_params),
            ]
        )
        assert output.returncode == 0
