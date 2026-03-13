# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import subprocess
import yaml
import json
import re
import os
import sys

from pathlib import Path
from typing import Any, Dict, List, Optional


def _decode_bytes(data: bytes) -> str:
    """
    Decode subprocess output bytes, handling UTF-16 (common from 3ds Max) and UTF-8.
    Strips any remaining null bytes that can appear in mixed-encoding output.
    """
    # Try UTF-16 first if BOM is present
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    # Try UTF-8, then strip stray null bytes (from UTF-16LE without BOM)
    text = data.decode("utf-8", errors="replace")
    return text.replace("\x00", "")


def run_command(args: List[str]) -> subprocess.CompletedProcess[bytes]:
    """
    Helper function to log, run command and also print out output, error for better debug
    """
    # Debug: Print environment paths before running command
    print("\n" + "=" * 80)
    print("DEBUG: Environment Paths Before Running Command")
    print("=" * 80)
    print(f"Command: {' '.join(args)}")
    print(f"\nPython Executable: {sys.executable}")
    print(f"\nPATH:\n{os.environ.get('PATH', 'NOT SET')}")
    print(f"\nPYTHONPATH:\n{os.environ.get('PYTHONPATH', 'NOT SET')}")

    # Check if pywin32_system32 is in PATH
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    pywin32_in_path = any("pywin32_system32" in entry for entry in path_entries)
    print(f"\npywin32_system32 in PATH: {pywin32_in_path}")

    if pywin32_in_path:
        pywin32_paths = [entry for entry in path_entries if "pywin32_system32" in entry]
        print(f"pywin32_system32 paths found: {pywin32_paths}")

    print("=" * 80 + "\n")

    output = subprocess.run(args, capture_output=True)

    print(f"Ran the following: {' '.join(output.args)}")
    print(f"\nstdout:\n\n{_decode_bytes(output.stdout)}")

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


def run_adaptor_test(
    template_path: Path,
    job_params: Dict[str, Any],
    path_mapping_rules: Optional[Dict[str, Any]] = None,
    expect_failure: bool = False,
) -> str:
    """
    Run the 3dsmax adaptor via openjd CLI for each step in the template.

    Args:
        template_path: Path to the job template YAML file.
        job_params: Dictionary of job parameters to pass to the template.
        path_mapping_rules: Optional path mapping rules for asset path remapping.
        expect_failure: If True, expects at least one step to fail and returns
            combined stdout+stderr. If False, asserts all steps succeed and
            returns combined stdout.

    Returns:
        Combined output from all steps as a string.
    """
    scripts_dir = os.path.join(os.path.split(sys.executable)[0])
    current_path = os.environ.get("PATH", "")
    if scripts_dir not in current_path:
        os.environ["PATH"] = scripts_dir + os.pathsep + current_path
        print(f"Added Scripts directory to PATH: {scripts_dir}")

    with open(template_path) as f:
        template = yaml.safe_load(f)

    filtered_params = {
        key: value for key, value in job_params.items() if not key.startswith("deadline:")
    }

    combined_output = ""
    any_failed = False
    for step in template["steps"]:
        command = [
            "openjd",
            "run",
            str(template_path),
            "--step",
            step["name"],
            "--job-param",
            json.dumps(filtered_params),
        ]

        if path_mapping_rules:
            command.extend(["--path-mapping-rules", json.dumps(path_mapping_rules)])
            print(f"\nPath Mapping Rules:\n{json.dumps(path_mapping_rules, indent=2)}")

        output = run_command(command)

        if expect_failure:
            combined_output += _decode_bytes(output.stdout) + _decode_bytes(output.stderr)
            if output.returncode != 0:
                any_failed = True
                break
        else:
            assert output.returncode == 0
            combined_output += _decode_bytes(output.stdout)

    if expect_failure:
        assert (
            any_failed
        ), f"Expected adaptor to fail but all steps succeeded.\nOutput:\n{combined_output}"

    return combined_output
