---
name: 3dsmax-dev-setup
version: 1.0.0
displayName: 3ds Max Dev Setup
description: Automated development environment setup for deadline-cloud-for-3ds-max - builds packages, installs dependencies, and configures environment variables
keywords:
  - 3dsmax
  - deadline
  - setup
  - build
  - install
  - environment
  - development
  - hatch
  - openjd
author: AWS Deadline Cloud
---

# 3ds Max Dev Setup Power

Automated development environment setup for deadline-cloud-for-3ds-max project.

## What This Power Does

This power automates the complete development environment setup for working on the deadline-cloud-for-3ds-max project. It handles everything from reading documentation to building packages, installing dependencies, and configuring environment variables.

## Setup Steps Performed

1. **Documentation Review** - Reads README.md and DEVELOPMENT.md to understand project requirements
2. **Hatch Installation** - Installs and configures Hatch build tool
3. **Package Build** - Builds wheel and source distributions
4. **Installer Build** - Builds the Windows installer (if InstallBuilder is available)
5. **3ds Max Detection** - Verifies 3ds Max installation
6. **Wheel Installation** - Installs the built wheel to 3ds Max Python
7. **OpenJD CLI Installation** - Installs openjd-cli for running integration tests
8. **Test Packages Installation** - Installs pytest, coverage, pillow, flaky, numpy
9. **PowerShell YAML Module** - Installs powershell-yaml for test scripts
10. **Environment Configuration** - Sets up required environment variables

## Prerequisites

- Python 3.9+ installed on system
- 3ds Max 2024, 2025, or 2026 installed
- Windows operating system
- (Optional) InstallBuilder for building installers

## Usage

The power will prompt you for:
- **3ds Max Version** (default: 2026)

If 3ds Max is not found at the expected location, the setup will abort with instructions to install 3ds Max first.

## What Gets Installed

### System Python Packages
- `hatch` - Build tool and environment manager

### 3ds Max Python Packages
- `deadline-cloud-for-3ds-max` - The built wheel from dist/
- `deadline` - AWS Deadline Cloud client library
- `openjd-adaptor-runtime` - OpenJD adaptor runtime
- `openjd-cli` - OpenJD command-line interface
- `pytest` - Test framework
- `pytest-cov` - Coverage plugin for pytest
- `pytest-xdist` - Parallel test execution
- `coverage` - Code coverage measurement
- `pillow` - Image processing for render output comparison
- `flaky` - Retry flaky tests
- `numpy<2` - Numerical operations (version <2 for 3ds Max compatibility)
- All required dependencies

### PowerShell Modules
- `powershell-yaml` - YAML parsing for test scripts

### Environment Variables (Machine-level)
- `PATH` - Adds 3ds Max and Python directories
- `3DSMAX_EXECUTABLE` - Points to 3dsmaxbatch.exe
- `PYTHONPATH` - Configures Python module search paths
- `VRAY_FOR_3DSMAX{VERSION}_*` - V-Ray configuration (if installed)

## Output Files

The power creates several reference documents:
- `HATCH_SETUP.md` - Hatch usage guide
- `configure_3dsmax_{version}_env.ps1` - Environment configuration script
- `verify_3dsmax_{version}_paths.ps1` - Path verification script
- `INSTALLATION_SUMMARY.md` - Complete installation summary
- `OPENJD_SETUP_COMPLETE.md` - OpenJD usage guide

## After Setup

Once setup is complete, you can:

### Run Unit Tests
```powershell
hatch run test
```

### Run Integration Tests
```powershell
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/vray_re_test/expected_job_bundle" -SkipInstall
```

### Build Package
```powershell
hatch build
```

### Format and Lint Code
```powershell
hatch run fmt
hatch run lint
```

## Troubleshooting

### Hatch Not Found
If hatch is not found after installation, restart your terminal or add to PATH:
```powershell
$env:PATH = "C:\Users\$env:USERNAME\AppData\Roaming\Python\Python311\Scripts;$env:PATH"
```

### 3ds Max Python Issues
Verify the correct Python is being used:
```powershell
& "C:\Program Files\Autodesk\3ds Max {VERSION}\Python\python.exe" --version
```

### Environment Variables Not Applied
Environment variables are set at machine level. You may need to:
1. Restart your terminal
2. Or run the generated `configure_3dsmax_{version}_env.ps1` script as Administrator

### Integration Tests Failing
Check 3ds Max logs:
```powershell
Get-Content "C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\{VERSION} - 64bit\ENU\Network\Max.log" -Tail 100
```

## Notes

- Setup requires Administrator privileges for setting machine-level environment variables
- The power skips S3 upload steps (those are for release workflows)
- InstallBuilder is optional - installer build will be skipped if not found
- V-Ray configuration is automatic if V-Ray is detected
