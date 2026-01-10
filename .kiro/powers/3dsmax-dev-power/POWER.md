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

Two scripts available:

| Script | Use Case |
|--------|----------|
| `test-3dsmax-openjd-run.ps1` | General testing via OpenJD CLI |
| `test-3dsmax-adapter-run.ps1` | **Path mapping tests** - runs adaptor directly |

```powershell
# Basic V-Ray test
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/vray_simple_test/expected_job_bundle"

# Path mapping test (use adapter script!)
.\scripts\test-3dsmax-adapter-run.ps1 `
    -JobBundleDir "test/integ/test_scripts/vray_vrmesh_test_remap/expected_job_bundle" `
    -PathMappingFile "test/integ/test_scripts/vray_vrmesh_test_remap/path_mapping_rules.json"
```

## Test Bundles

| Bundle | Description |
|--------|-------------|
| `vray_simple_test` | Basic V-Ray render |
| `vray_vrmesh_test` | V-Ray with VRayProxy |
| `vray_vrmesh_test_remap` | VRMesh with path mapping |
| `scanline_simple_test` | Scanline renderer |
| `arnold_simple_test` | Arnold renderer |

## Checking Logs

```powershell
# View recent logs
Get-Content 'C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log' -Tail 100

# Search for errors
Select-String -Path 'C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log' -Pattern "error|exception" -CaseSensitive:$false
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