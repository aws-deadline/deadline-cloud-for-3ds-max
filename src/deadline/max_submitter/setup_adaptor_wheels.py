# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#!/usr/bin/env python3
"""Cross-platform script to set up adaptor wheels in a virtual environment."""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def main():
    system = platform.system()
    working_dir = Path(r"{{Session.WorkingDirectory}}")
    wheels_dir = Path(r"{{Param.OverrideAdaptorWheels}}")
    adaptor_name = r"{{Param.OverrideAdaptorName}}"

    print(f"Platform: {system}")
    print(f"Working directory: {working_dir}")
    print(f"Wheels directory: {wheels_dir}")
    print(f"Adaptor name: {adaptor_name}")
    print()

    # Show available wheels
    print("The adaptor wheels that are attached to the job:")
    for wheel in sorted(wheels_dir.glob("*.whl")):
        print(f"  {wheel.name}")
    print()

    # Create venv
    venv_dir = working_dir / "venv"
    print(f"Creating Python venv for the {adaptor_name} command")
    python_cmd = "python" if system == "Windows" else "/usr/local/bin/python3"
    subprocess.run([python_cmd, "-m", "venv", str(venv_dir)], check=True)
    print()

    # Save initial environment
    env_file = working_dir / ".envInitial"
    with open(env_file, "w", encoding="utf8") as f:
        json.dump(dict(os.environ), f)

    # Determine venv paths based on platform
    if system == "Windows":
        venv_pip = venv_dir / "Scripts" / "pip.exe"
        adaptor_exe = venv_dir / "Scripts" / f"{adaptor_name}.exe"
    else:
        venv_pip = venv_dir / "bin" / "pip"
        adaptor_exe = venv_dir / "bin" / adaptor_name

    # Install wheels
    print("Installing adaptor into the venv")
    openjd_wheels = list(wheels_dir.glob("openjd*.whl"))
    deadline_wheels = list(wheels_dir.glob("deadline*.whl"))

    for wheel in openjd_wheels + deadline_wheels:
        print(f"  Installing {wheel.name}")
        subprocess.run([str(venv_pip), "install", str(wheel)], check=True)
    print()

    # Verify adaptor was installed
    if not adaptor_exe.exists():
        print(f"ERROR: The Override Adaptor {adaptor_name} was not installed as expected.")
        print(f"Expected location: {adaptor_exe}")
        sys.exit(1)

    print(f"Successfully installed {adaptor_name}")

    # Capture environment changes
    after_env = dict(os.environ)

    # Update PATH to include venv
    if system == "Windows":
        venv_bin = str(venv_dir / "Scripts")
    else:
        venv_bin = str(venv_dir / "bin")

    if "PATH" in after_env:
        after_env["PATH"] = f"{venv_bin}{os.pathsep}{after_env['PATH']}"
    else:
        after_env["PATH"] = venv_bin

    # Load initial environment
    with open(env_file, "r", encoding="utf8") as f:
        before_env = json.load(f)

    # Output environment changes for OpenJD
    for key, value in after_env.items():
        if value != before_env.get(key):
            print(f"updating {key}={value}")
            print(f"openjd_env: {key}={value}")

    for key in before_env:
        if key not in after_env:
            print(f"openjd_unset_env: {key}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
