# Troubleshooting Guide

Common issues and solutions for 3ds Max dev setup.

## 3ds Max Not Found

**Problem:** Setup aborts with "3ds Max {VERSION} is not installed"

**Solutions:**
1. Verify 3ds Max is installed at the standard location:
   ```
   C:\Program Files\Autodesk\3ds Max {VERSION}
   ```

2. If installed at a different location, create a symbolic link:
   ```powershell
   New-Item -ItemType SymbolicLink -Path "C:\Program Files\Autodesk\3ds Max 2026" -Target "D:\Your\Custom\Path\3dsMax2026"
   ```

3. Install 3ds Max from Autodesk website

4. Check if you have the correct version installed (2024, 2025, or 2026)

## Hatch Installation Issues

**Problem:** `hatch: The term 'hatch' is not recognized`

**Solutions:**
1. Verify hatch is installed:
   ```powershell
   python -m pip list | Select-String "hatch"
   ```

2. Add Scripts directory to PATH:
   ```powershell
   $env:PATH = "C:\Users\$env:USERNAME\AppData\Roaming\Python\Python311\Scripts;$env:PATH"
   ```

3. Restart terminal after installation

4. Set PATH permanently:
   ```powershell
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Users\$env:USERNAME\AppData\Roaming\Python\Python311\Scripts", [EnvironmentVariableTarget]::User)
   ```

## Build Failures

**Problem:** `hatch build` fails

**Solutions:**
1. Ensure you're in the repository root directory

2. Check if git is initialized (hatch-vcs requires git):
   ```powershell
   git status
   ```

3. Verify Python version:
   ```powershell
   python --version  # Should be 3.9+
   ```

4. Clean build artifacts and retry:
   ```powershell
   Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
   hatch build
   ```

## Wheel Installation Issues

**Problem:** Wheel installation fails or wrong packages installed

**Solutions:**
1. Verify using correct Python:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" --version
   ```

2. Check if pip is installed:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m ensurepip
   ```

3. Install with --force-reinstall:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip install --force-reinstall dist\deadline_cloud_for_3ds_max-*.whl
   ```

4. Check for conflicting packages:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip list | Select-String "deadline|openjd"
   ```

## OpenJD CLI Issues

**Problem:** `openjd run` command not found or fails

**Solutions:**
1. Verify openjd-cli is installed:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip show openjd-cli
   ```

2. Install if missing:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip install openjd-cli
   ```

3. Test with module syntax:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m openjd run --help
   ```

4. Check for dependency conflicts:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip check
   ```

## Environment Variables Not Applied

**Problem:** Environment variables not recognized after setup

**Solutions:**
1. Restart terminal/PowerShell session

2. Check if variables are set:
   ```powershell
   [Environment]::GetEnvironmentVariable('3DSMAX_EXECUTABLE', 'Machine')
   [Environment]::GetEnvironmentVariable('PYTHONPATH', 'Machine')
   ```

3. Run configuration script as Administrator:
   ```powershell
   # Right-click PowerShell -> Run as Administrator
   .\configure_3dsmax_2026_env.ps1
   ```

4. Set manually if needed:
   ```powershell
   [Environment]::SetEnvironmentVariable('3DSMAX_EXECUTABLE', 'C:\Program Files\Autodesk\3ds Max 2026\3dsmaxbatch.exe', 'Machine')
   ```

5. Restart computer for system-wide changes

## Integration Test Failures

**Problem:** Integration tests fail to run

**Solutions:**
1. Check 3ds Max logs:
   ```powershell
   Get-Content "C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log" -Tail 100
   ```

2. Verify 3DSMAX_EXECUTABLE is set:
   ```powershell
   $env:3DSMAX_EXECUTABLE
   ```

3. Check if scene files exist:
   ```powershell
   Test-Path "test/integ/test_scripts/*/scene/*.max"
   ```

4. Run with verbose output:
   ```powershell
   .\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/re_disabled_test/expected_job_bundle" -ShowOutput
   ```

5. Verify Python environment:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -c "import deadline.max_adaptor; print('OK')"
   ```

## V-Ray Not Detected

**Problem:** V-Ray environment variables not set

**Solutions:**
1. Check if V-Ray is installed:
   ```powershell
   Test-Path "C:\ProgramData\Autodesk\ApplicationPlugins\VRay3dsMax2026"
   ```

2. Install V-Ray for 3ds Max if needed

3. Manually set V-Ray variables:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('VRAY_FOR_3DSMAX2026_MAIN', 'C:\ProgramData\Autodesk\ApplicationPlugins\VRay3dsMax2026\bin\', 'Machine')
   ```

4. Verify V-Ray version matches 3ds Max version

## Permission Denied Errors

**Problem:** Access denied when setting environment variables

**Solutions:**
1. Run PowerShell as Administrator:
   - Right-click PowerShell
   - Select "Run as Administrator"

2. Check user permissions:
   ```powershell
   whoami /groups | Select-String "Administrators"
   ```

3. Use User-level variables instead of Machine-level:
   ```powershell
   [Environment]::SetEnvironmentVariable('3DSMAX_EXECUTABLE', 'C:\Program Files\Autodesk\3ds Max 2026\3dsmaxbatch.exe', 'User')
   ```

## Python Version Mismatch

**Problem:** Wrong Python version being used

**Solutions:**
1. Always use full path to 3ds Max Python:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe"
   ```

2. Check Python version:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" --version
   ```

3. Verify PATH priority:
   ```powershell
   (Get-Command python).Source
   ```

4. Update PATH to prioritize 3ds Max Python:
   ```powershell
   $env:PATH = "C:\Program Files\Autodesk\3ds Max 2026\Python;$env:PATH"
   ```

## Module Import Errors

**Problem:** `ModuleNotFoundError` when running tests

**Solutions:**
1. Verify package is installed:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip list | Select-String "deadline"
   ```

2. Check PYTHONPATH:
   ```powershell
   $env:PYTHONPATH
   ```

3. Reinstall the wheel:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip uninstall deadline-cloud-for-3ds-max -y
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip install dist\deadline_cloud_for_3ds_max-*.whl
   ```

4. Check for conflicting installations:
   ```powershell
   & "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -c "import deadline; print(deadline.__file__)"
   ```

## Getting Help

If issues persist:

1. Check the project documentation:
   - README.md
   - DEVELOPMENT.md
   - INSTALLATION_SUMMARY.md

2. Review generated documentation:
   - HATCH_SETUP.md
   - OPENJD_SETUP_COMPLETE.md

3. Check 3ds Max logs for detailed error messages

4. Verify all prerequisites are met:
   - Python 3.9+
   - 3ds Max 2024/2025/2026
   - Windows OS
   - Administrator privileges

5. Try a clean setup:
   - Uninstall all packages
   - Delete dist/ directory
   - Run setup again
