#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Setup runner for 3ds Max integration tests in CodeBuild."""

import argparse
import hashlib
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import boto3
from botocore.config import Config

# SHA256 checksums for installers
MAX_CHECKSUMS = {
    "2024": {
        "windows": "C07C5EF9B0ADCE499F0CD51B909B4E2AE40EC56B71980FE8963240CBABB28569",
    },
    "2025": {
        "windows": "E2A3B5A47EB1556542CA44FBA3ADC745EB4BDCAEE25D993BF54C68CCCDA55D05",
    },
    "2026": {
        "windows": "D873A86AE8C53E021DFFDC0093AA5D5D9E88F4268B9BD098D9C02DABFBF2E67F",
    },
}

VRAY_CHECKSUMS = {
    "2024": {
        "windows": "39679C851FCFB20C779FF77E9906B56411F11FB79E6332B087DDABDBA35778F0",
    },
    "2025": {
        "windows": "DF4A1A68BA17569A3B17CB4FA230BFEF7F73569CB4A0B3718B27524CF769A70C",
    },
    "2026": {
        "windows": "8D46DE59C21C3BE45FB3B338E31F7FF6AA32D17B9493EF2FA81F667304B469F7",
    },
}


def run(cmd, check=True, cwd=None, stdin=None):
    """Run a shell command, exiting on failure if check is True."""
    print(f"Running: {cmd if isinstance(cmd, str) else shlex.join(cmd)}")
    result = subprocess.run(cmd, check=False, cwd=cwd, stdin=stdin)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


def download_from_s3(s3_path, local_path):
    """Download a file from S3 with expected bucket owner verification."""
    bucket = os.environ.get("INSTALLER_BUCKET")
    if not bucket:
        print("ERROR: INSTALLER_BUCKET not set")
        sys.exit(1)

    expected_bucket_owner = os.environ.get("INSTALLER_BUCKET_EXPECTED_OWNER")
    if not expected_bucket_owner:
        raise ValueError("INSTALLER_BUCKET_EXPECTED_OWNER environment variable is required")
    if not (expected_bucket_owner.isdigit() and len(expected_bucket_owner) == 12):
        raise ValueError("INSTALLER_BUCKET_EXPECTED_OWNER must be a 12-digit AWS Account ID")

    config = Config(read_timeout=300, connect_timeout=60, retries={"max_attempts": 2})
    s3 = boto3.client("s3", config=config)

    print(f"Downloading s3://{bucket}/{s3_path} to {local_path}")
    s3.download_file(
        bucket, s3_path, str(local_path), ExtraArgs={"ExpectedBucketOwner": expected_bucket_owner}
    )


def verify_checksum(file_path, expected_checksum):
    """Verify SHA256 checksum of downloaded file."""

    print(f"Verifying checksum for {file_path}...")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    actual = sha256.hexdigest()
    if actual != expected_checksum:
        print("ERROR: Checksum mismatch!")
        print(f"  Expected: {expected_checksum}")
        print(f"  Actual:   {actual}")
        sys.exit(1)

    print("OK Checksum verified")
    return True


def _install_3dsmax(version):
    """Install 3ds Max for the given version if not already installed."""
    max_dir = Path(f"C:/Program Files/Autodesk/3ds Max {version}")
    max_marker = max_dir / ".installed"

    if max_marker.exists():
        print(f"3ds Max {version} already installed")
        return

    print(f"Installing 3ds Max {version}...")
    max_setup_dir = Path("C:/3dsmax_setup")
    max_setup_dir.mkdir(parents=True, exist_ok=True)

    max_zip = max_setup_dir / f"3dsMax{version}.zip"
    download_from_s3(f"3dsmax/{version}/3dsMax{version}.zip", max_zip)
    verify_checksum(max_zip, MAX_CHECKSUMS[version]["windows"])

    print("Extracting 3ds Max installer...")
    run(
        [
            "powershell",
            "-Command",
            f"Expand-Archive -Path '{max_zip}' -DestinationPath '{max_setup_dir}' -Force",
        ]
    )

    setup_exe = max_setup_dir / f"3dsMax{version}" / "Setup.exe"
    if not setup_exe.exists():
        print(f"ERROR: Setup.exe not found at {setup_exe}")
        sys.exit(1)

    print("Starting 3ds Max installation...")
    result = subprocess.run(
        ["powershell", "-Command", f'Start-Process "{setup_exe}" -ArgumentList "-q" -Wait'],
        capture_output=True,
        text=True,
        check=False,
    )

    print(f"Installation exit code: {result.returncode}")
    if result.stdout:
        print(f"Installation output: {result.stdout}")
    if result.stderr:
        print(f"Installation errors: {result.stderr}")

    # Verify installation
    max_exe = max_dir / "3dsmaxbatch.exe"
    if max_exe.exists():
        print(f"SUCCESS: 3dsmaxbatch.exe found at {max_exe}")
        max_marker.touch()
    else:
        print(f"ERROR: 3dsmaxbatch.exe NOT found at {max_exe}")
        sys.exit(1)

    # Cleanup
    max_zip.unlink(missing_ok=True)
    run(
        ["powershell", "-Command", f"Remove-Item -Path '{max_setup_dir}' -Recurse -Force"],
        check=False,
    )


def _install_vray(version):
    """Install V-Ray for the given 3ds Max version if not already installed."""
    vray_plugin_dir = Path(f"C:/ProgramData/Autodesk/ApplicationPlugins/VRay3dsMax{version}")
    vray_bin = vray_plugin_dir / "bin" / "vray.exe"
    chaos_dir = Path(f"C:/Program Files/Chaos/V-Ray/3ds Max {version}")

    if vray_bin.exists() and chaos_dir.exists():
        print(f"V-Ray for 3ds Max {version} already installed")
        print(f"  Plugin dir: {vray_plugin_dir}")
        print(f"  Chaos dir:  {chaos_dir}")
        return

    print(f"Installing V-Ray for 3ds Max {version}...")
    vray_setup_dir = Path("C:/vray_setup")
    vray_setup_dir.mkdir(parents=True, exist_ok=True)

    vray_installer = vray_setup_dir / f"vray{version}.exe"
    download_from_s3(f"3dsmax/{version}/vray{version}.exe", vray_installer)
    verify_checksum(vray_installer, VRAY_CHECKSUMS[version]["windows"])

    print("Starting V-Ray installation...")
    result = subprocess.run(
        [
            "powershell",
            "-Command",
            (
                f'Start-Process "{vray_installer}"'
                f" -ArgumentList '-gui=0','-auto=1','-quiet=1'"
                f" -Wait"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    print(f"V-Ray installation exit code: {result.returncode}")
    if result.stdout:
        print(f"V-Ray installation output: {result.stdout}")
    if result.stderr:
        print(f"V-Ray installation errors: {result.stderr}")

    # Verify V-Ray installation
    install_ok = True
    if chaos_dir.exists():
        print(f"SUCCESS: Chaos directory found at {chaos_dir}")
    else:
        print(f"ERROR: Chaos directory NOT found at {chaos_dir}")
        install_ok = False

    if vray_bin.exists():
        print(f"SUCCESS: vray.exe found at {vray_bin}")
    else:
        print(f"ERROR: vray.exe NOT found at {vray_bin}")
        if vray_plugin_dir.exists():
            print(f"  Contents of {vray_plugin_dir}:")
            for item in sorted(vray_plugin_dir.rglob("*")):
                print(f"    {item.relative_to(vray_plugin_dir)}")
        install_ok = False

    if not install_ok:
        print("ERROR: V-Ray installation verification failed")
        sys.exit(1)

    # Cleanup
    run(
        ["powershell", "-Command", f"Remove-Item -Path '{vray_setup_dir}' -Recurse -Force"],
        check=False,
    )


def _register_pywin32():
    """Register pywin32 DLLs so child processes (3ds Max) can load win32file."""
    print("Running pywin32 post-install script...")
    env_root = Path(sys.executable).parent.parent
    postinstall = (
        env_root / "Lib" / "site-packages" / "win32" / "scripts" / "pywin32_postinstall.py"
    )

    if postinstall.exists():
        run([sys.executable, str(postinstall), "-install"])
        return

    # Fallback: copy DLLs manually
    print(f"pywin32_postinstall.py not found at {postinstall}, copying DLLs manually...")
    pywin32_system32 = env_root / "Lib" / "site-packages" / "pywin32_system32"
    if not pywin32_system32.exists():
        print("ERROR: pywin32_system32 directory not found")
        sys.exit(1)

    for dll in pywin32_system32.glob("*.dll"):
        dest = Path("C:/Windows/System32") / dll.name
        if not dest.exists():
            print(f"Copying {dll.name} to System32")
            shutil.copy2(str(dll), str(dest))


def setup_windows(max_versions):
    """Install 3ds Max, V-Ray, and register pywin32 for each version."""
    for version in max_versions:
        _install_3dsmax(version)
        _install_vray(version)

    _register_pywin32()
    print("3ds Max and V-Ray installation complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup 3ds Max test environment")
    parser.add_argument("--versions", nargs="+", required=True, help="3ds Max versions to install")
    args = parser.parse_args()

    max_versions = args.versions

    system = platform.system()
    print(f"Setting up {system} with 3ds Max {', '.join(max_versions)}")

    if system == "Windows":
        setup_windows(max_versions)
    else:
        print(f"Unsupported platform: {system}")
        print("3ds Max is only supported on Windows")
        sys.exit(1)
