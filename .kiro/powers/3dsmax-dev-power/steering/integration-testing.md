# Integration Testing Guide

How to run integration tests for the 3ds Max adaptor and submitter.

## Prerequisites

1. Windows machine with 3ds Max 2025 or 2026 installed
2. V-Ray installed (for V-Ray tests)
3. 3ds Max Python and executable on PATH
4. Test dependencies installed

## Setup

First, determine which version of 3ds Max is installed. Check `C:\Program Files\Autodesk\` for directories like `3ds Max 2025` or `3ds Max 2026`. Use the `MAX_VERSION` variable below to match your installation.

```powershell
# Set this to your installed version (2025, 2026, etc.)
$MAX_VERSION = "2026"

# Add 3ds Max to PATH
$env:PATH = "C:\Program Files\Autodesk\3ds Max $MAX_VERSION;C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python;" + $env:PATH

# Set executable
$env:3DSMAX_EXECUTABLE = "3dsmaxbatch"
$env:MAX_VERSION = $MAX_VERSION

# Install pip if needed
python -m ensurepip

# Install test dependencies
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pip install -r requirements-integ-testing.txt
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pip install "numpy<2"
```

## Running Tests (pytest — primary method)

Use 3ds Max's Python to run pytest directly. This is the standard way to run integration tests. Replace `$MAX_VERSION` with your installed version if not already set.

### Run all integration tests
```powershell
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pytest test/integ -o addopts="" -v --color=no
```

### Run submitter tests only
```powershell
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pytest test/integ -m submitter -o addopts="" -v --color=no
```

### Run adaptor tests only
```powershell
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pytest test/integ -m adaptor -o addopts="" -v --color=no
```

### Run path mapping tests only
```powershell
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pytest test/integ -m pathmapping -o addopts="" -v --color=no
```

### Run a specific test
```powershell
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" -m pytest test/integ/test_3dsmax_adaptors.py::TestAdaptors::test_minimal_scene_adaptor -o addopts="" -v --color=no
```

## Running Tests (hatch — alternative)

Not recommended. Hatch uses Python 3.12 which conflicts with 3ds Max's Python 3.11.

```powershell
hatch run integ:test              # All integ tests
hatch run integ:test_submitters   # Submitter tests
hatch run integ:test_adaptors     # Adaptor tests
```

## Manual Debugging (PowerShell scripts)

For ad-hoc debugging of individual test bundles outside of pytest. These scripts call `openjd run` directly with a specific job bundle.

```powershell
# General test via OpenJD CLI
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/minimal_test/expected_job_bundle"

# Path mapping test (must use adapter script for map_path() support)
.\scripts\test-3dsmax-adapter-run.ps1 `
    -JobBundleDir "test/integ/test_scripts/vray_vrmesh_remap_test/expected_job_bundle" `
    -PathMappingFile "test/integ/test_scripts/vray_vrmesh_remap_test/path_mapping_rules.json"

# Skip wheel installation for faster iteration
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "..." -SkipInstall
```

## Test Bundles

These are the test bundles that exist in `test/integ/test_scripts/`:

| Bundle | Renderer | Description | Pytest Marker |
|--------|----------|-------------|---------------|
| `minimal_test` | Scanline (V-Ray active) | Basic render with state sets and cameras | `adaptor`, `submitter` |
| `re_enabled_test` | Scanline | Render elements enabled | `adaptor` |
| `re_disabled_test` | Scanline | Render elements disabled | `adaptor` |
| `vray_re_test` | V-Ray CPU | V-Ray render elements (xfail — known flaky) | `adaptor` |
| `lightmix` | V-Ray GPU | V-Ray LightMix render elements | `adaptor` |
| `vray_vrmesh_remap_test` | V-Ray | VRMesh path mapping | `adaptor`, `pathmapping` |
| `batch_render_test` | Scanline | Batch render with scene states, presets, and overrides | `adaptor` |

## Test Bundle Structure

```
test/integ/test_scripts/{test_name}/
├── scene/                      # .max scene file + assets
├── expected_job_bundle/        # Expected submitter output
│   ├── template.yaml
│   ├── parameter_values.yaml
│   └── asset_references.yaml
├── expected_images/            # Expected render output (adaptor tests)
├── _test_max.py                # Submitter test script (submitter tests only)
└── path_mapping_rules.json     # Path mapping rules (path mapping tests only)
```

## Common Issues

### PyWin32 DLL registration
```powershell
# Run in elevated shell
python -m pywin32_postinstall -install
```

### Wrong Python version
Ensure 3ds Max Python is being used, not system Python:
```powershell
& "C:\Program Files\Autodesk\3ds Max $MAX_VERSION\Python\python.exe" --version
# Should show Python 3.11.x for Max 2026, Python 3.10.x for Max 2025
```

### Checking 3ds Max logs
```powershell
Get-Content "C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\$MAX_VERSION - 64bit\ENU\Network\Max.log" -Tail 100
```
