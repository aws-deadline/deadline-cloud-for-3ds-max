# 3ds Max Dev Setup Guide

Complete automated setup workflow for deadline-cloud-for-3ds-max development environment.

## Setup Workflow

### Step 1: Prompt for 3ds Max Version
Ask the user which version of 3ds Max to set up for:
- Default: 2026
- Supported: 2024, 2025, 2026

Example prompt:
```
Which version of 3ds Max would you like to set up for? (default: 2026)
```

### Step 2: Verify 3ds Max Installation
Check if 3ds Max is installed at the expected location:
```powershell
Test-Path "C:\Program Files\Autodesk\3ds Max {VERSION}"
Test-Path "C:\Program Files\Autodesk\3ds Max {VERSION}\3dsmax.exe"
Test-Path "C:\Program Files\Autodesk\3ds Max {VERSION}\3dsmaxbatch.exe"
Test-Path "C:\Program Files\Autodesk\3ds Max {VERSION}\Python\python.exe"
```

**If 3ds Max is NOT found:**
- Abort the setup
- Display error message: "3ds Max {VERSION} is not installed at the expected location. Please install 3ds Max {VERSION} first."
- Provide installation link or instructions

**If 3ds Max IS found:**
- Display confirmation: "Found 3ds Max {VERSION} at C:\Program Files\Autodesk\3ds Max {VERSION}"
- Check Python version
- Continue with setup

### Step 3: Read Project Documentation
Read and summarize key information from:
1. `README.md` - Project overview, compatibility, requirements
2. `DEVELOPMENT.md` - Development workflow, build instructions

Extract important details:
- Python version requirements
- 3ds Max version compatibility
- Required dependencies
- Build commands

### Step 4: Install Hatch
Check if hatch is already installed:
```powershell
hatch --version
```

If not installed:
```powershell
python -m pip install hatch
```

Add hatch to PATH:
```powershell
$scriptsPath = "C:\Users\$env:USERNAME\AppData\Roaming\Python\Python311\Scripts"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$scriptsPath", [EnvironmentVariableTarget]::User)
```

Verify installation:
```powershell
hatch --version
hatch env show
```

### Step 5: Build the Package
Build wheel and source distributions:
```powershell
hatch build
```

Expected output:
- `dist/deadline_cloud_for_3ds_max-{VERSION}-py3-none-any.whl`
- `dist/deadline_cloud_for_3ds_max-{VERSION}.tar.gz`

Verify build artifacts exist.

### Step 6: Build the Installer (Optional)
Check if InstallBuilder is available:
```powershell
Test-Path "C:\Program Files\InstallBuilder*"
```

If available, build installer:
```powershell
hatch run installer:build-installer --local-dev
```

Expected output:
- `DeadlineCloudFor3dsMaxSubmitter-windows-x64-installer.exe`

If InstallBuilder is not found, skip this step and note it in the summary.

### Step 7: Install pip to 3ds Max Python
Ensure pip is installed in 3ds Max Python:
```powershell
& "C:\Program Files\Autodesk\3ds Max {VERSION}\Python\python.exe" -m ensurepip
```

### Step 8: Install the Wheel to 3ds Max Python
Install the built wheel:
```powershell
$wheelFile = Get-ChildItem "dist\deadline_cloud_for_3ds_max-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
& "C:\Program Files\Autodesk\3ds Max {VERSION}\Python\python.exe" -m pip install --force-reinstall $wheelFile.FullName
```

Verify installation:
```powershell
& "C:\Program Files\Autodesk\3ds Max {VERSION}\Python\python.exe" -m pip show deadline-cloud-for-3ds-max
```

### Step 9: Install OpenJD CLI
Install openjd-cli for running integration tests:
```powershell
& "C:\Program Files\Autodesk\3ds Max {VERSION}\Python\python.exe" -m pip install openjd-cli
```

Verify installation:
```powershell
& "C:\Program Files\Autodesk\3ds Max {VERSION}\Python\python.exe" -m openjd run --help
```

### Step 10: Install Test Packages
Install pytest and related test packages required for running tests:
```powershell
& "C:\Program Files\Autodesk\3ds Max {VERSION}\Python\python.exe" -m pip install pytest pytest-cov pytest-xdist coverage pillow flaky "numpy<2"
```

**Important:** Use `numpy<2` to avoid compatibility issues with 3ds Max.

Verify pytest installation:
```powershell
& "C:\Program Files\Autodesk\3ds Max {VERSION}\Python\python.exe" -m pytest --version
```

**Installed Test Packages:**
- `pytest` - Test framework
- `pytest-cov` - Coverage plugin for pytest
- `pytest-xdist` - Parallel test execution
- `coverage` - Code coverage measurement
- `pillow` - Image processing (for comparing render outputs)
- `flaky` - Retry flaky tests
- `numpy<2` - Numerical operations (version <2 for 3ds Max compatibility)

### Step 11: Install PowerShell YAML Module
Install the PowerShell YAML module required by test scripts:
```powershell
Install-Module powershell-yaml -Force -Scope CurrentUser
```

This module is required for parsing YAML job bundle files in the test scripts.

### Step 12: Configure Environment Variables
Create and run environment configuration script.

**Create verification script:**
`verify_3dsmax_{VERSION}_paths.ps1` - Checks all required paths

**Create configuration script:**
`configure_3dsmax_{VERSION}_env.ps1` - Sets environment variables

Environment variables to set (Machine level):
1. **PATH** - Add 3ds Max and Python directories
   ```powershell
   [Environment]::SetEnvironmentVariable('Path', 'C:\Program Files\Autodesk\3ds Max {VERSION};' + [Environment]::GetEnvironmentVariable('Path', 'Machine'), 'Machine')
   [Environment]::SetEnvironmentVariable('Path', 'C:\Program Files\Autodesk\3ds Max {VERSION}\Python;' + [Environment]::GetEnvironmentVariable('Path', 'Machine'), 'Machine')
   ```

2. **3DSMAX_EXECUTABLE**
   ```powershell
   [Environment]::SetEnvironmentVariable('3DSMAX_EXECUTABLE', 'C:\Program Files\Autodesk\3ds Max {VERSION}\3dsmaxbatch.exe', 'Machine')
   ```

3. **PYTHONPATH**
   ```powershell
   [Environment]::SetEnvironmentVariable('PYTHONPATH', 'C:\Program Files\Autodesk\3ds Max {VERSION}\Python', 'Machine')
   ```

4. **V-Ray Variables (if V-Ray is detected)**
   Check for V-Ray:
   ```powershell
   Test-Path "C:\ProgramData\Autodesk\ApplicationPlugins\VRay3dsMax{VERSION}"
   ```
   
   If found, set:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('VRAY_FOR_3DSMAX{VERSION}_MAIN', 'C:\ProgramData\Autodesk\ApplicationPlugins\VRay3dsMax{VERSION}\bin\', 'Machine')
   [System.Environment]::SetEnvironmentVariable('VRAY_FOR_3DSMAX{VERSION}_PLUGINS', 'C:\ProgramData\Autodesk\ApplicationPlugins\VRay3dsMax{VERSION}\bin\plugins\', 'Machine')
   ```

**Note:** Setting machine-level environment variables requires Administrator privileges.

### Step 13: Create Documentation Files
Generate reference documentation:

1. **HATCH_SETUP.md** - Hatch commands and usage
2. **INSTALLATION_SUMMARY.md** - Complete setup summary with versions
3. **OPENJD_SETUP_COMPLETE.md** - OpenJD usage guide with examples

### Step 14: Display Setup Summary
Show a summary of what was installed and configured:
- Hatch version
- Built packages (wheel, installer)
- Installed Python packages and versions
- Environment variables set
- Next steps for the user

## Example Summary Output

```
=== 3ds Max 2026 Dev Setup Complete ===

✅ Hatch 1.16.3 installed
✅ Package built: deadline_cloud_for_3ds_max-0.1.7.post18+g04b6260de
✅ Wheel installed to 3ds Max 2026 Python
✅ OpenJD CLI 0.7.4 installed
✅ Test packages installed (pytest, coverage, pillow, etc.)
✅ PowerShell YAML module installed
✅ Environment variables configured

Installed Packages:
- deadline-cloud-for-3ds-max 0.1.7.post18+g04b6260de
- deadline 0.52.1
- openjd-adaptor-runtime 0.9.3
- openjd-cli 0.7.4
- pytest 9.0.2
- pytest-cov 7.0.0
- pytest-xdist 3.8.0
- coverage 7.13.2
- pillow 12.1.0
- flaky 3.8.1
- numpy 1.26.4

Environment Variables Set:
- PATH (added 3ds Max and Python)
- 3DSMAX_EXECUTABLE
- PYTHONPATH
- VRAY_FOR_3DSMAX2026_* (V-Ray detected)

Documentation Created:
- HATCH_SETUP.md
- INSTALLATION_SUMMARY.md
- OPENJD_SETUP_COMPLETE.md
- configure_3dsmax_2026_env.ps1
- verify_3dsmax_2026_paths.ps1

Next Steps:
1. Restart your terminal for environment variables to take effect
2. Run unit tests: hatch run test
3. Run integration test: .\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/re_disabled_test/expected_job_bundle" -SkipInstall

For more information, see INSTALLATION_SUMMARY.md
```

## Important Notes

- Always verify 3ds Max installation before proceeding
- Use the correct Python executable for the 3ds Max version
- Environment variables require terminal restart to take effect
- Administrator privileges needed for machine-level environment variables
- V-Ray configuration is automatic if detected
- InstallBuilder is optional - setup continues without it
