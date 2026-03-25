---
name: "3dsmax-dev-power"
displayName: "3ds Max Dev Power"
description: "Development power for deadline-cloud-for-3ds-max - build, lint, test, and run integration tests with 3ds Max and V-Ray."
keywords: ["3dsmax", "deadline", "build", "test", "lint", "integration", "vray", "adaptor"]
author: "AWS Deadline Cloud Team"
---

# 3ds Max Dev Power

Development power for building, testing, and debugging the deadline-cloud-for-3ds-max project.

## Overview

This project is a Python package that provides:
- **3ds Max Adaptor**: Runs 3ds Max renders on Deadline Cloud workers
- **3ds Max Submitter**: UI for submitting jobs from 3ds Max to Deadline Cloud

## Available Steering Files

- **build-and-test.md** - Complete build and test workflow
- **integration-testing.md** - Guide for running and creating integration tests
- **troubleshooting.md** - Common issues and solutions

## Prerequisites

- Python 3.9+ (3ds Max 2026 uses Python 3.11)
- 3ds Max 2025 or 2026 with V-Ray (for integration tests)
- Hatch (Python build tool): `pip install hatch`

## Quick Commands

### Build
```powershell
hatch build -t wheel
```

### Lint & Format
```powershell
hatch run fmt    # Format code
hatch run lint   # Run linter
hatch run typing # Type checking
```

### Unit Tests
```powershell
hatch run test                              # All tests
hatch run test test/unit/path/to/test.py   # Specific file
hatch run test -k "test_vray"              # Pattern match
```

### Integration Tests

Run with 3ds Max's Python (requires Windows + 3ds Max installed). Set `$MAX_VERSION` to your installed version (2025, 2026, etc.):

```powershell
$MAX_VERSION = "2026"

# All integration tests
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pytest test/integ -o addopts="" -v --color=no

# Submitter tests only
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pytest test/integ -m submitter -o addopts="" -v --color=no

# Adaptor tests only
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pytest test/integ -m adaptor -o addopts="" -v --color=no
```

For ad-hoc debugging of individual bundles, PowerShell scripts are also available:

```powershell
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/minimal_test/expected_job_bundle" -SkipInstall
```

## Test Bundles

| Bundle | Renderer | Description |
|--------|----------|-------------|
| `minimal_test` | Scanline (V-Ray active) | Basic render with state sets and cameras |
| `re_enabled_test` | Scanline | Render elements enabled |
| `re_disabled_test` | Scanline | Render elements disabled |
| `vray_re_test` | V-Ray CPU | V-Ray render elements |
| `lightmix` | V-Ray GPU | V-Ray LightMix render elements |
| `vray_vrmesh_remap_test` | V-Ray | VRMesh path mapping |
| `batch_render_test` | Scanline | Batch render with scene states, presets, and overrides |

## Checking Logs

```powershell
# View recent logs
Get-Content "C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\$MAX_VERSION - 64bit\ENU\Network\Max.log" -Tail 100

# Search for errors
Select-String -Path "C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\$MAX_VERSION - 64bit\ENU\Network\Max.log" -Pattern "error|exception" -CaseSensitive:$false
```

## Project Structure

```
src/deadline/
├── max_adaptor/      # Adaptor (runs on worker)
│   └── MaxClient/    # 3ds Max client and render handlers
└── max_submitter/    # Submitter UI (runs in 3ds Max)
test/
├── unit/             # Unit tests
└── integ/            # Integration tests
scripts/              # Test runner scripts
```