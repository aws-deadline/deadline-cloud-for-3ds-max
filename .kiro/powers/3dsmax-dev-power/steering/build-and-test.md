# Build and Test Workflow

Complete build and test workflow for deadline-cloud-for-3ds-max.

## Step 1: Build the Wheel

Always build a fresh wheel before testing:

```powershell
hatch build -t wheel
```

This creates a wheel in `dist/deadline_cloud_for_3ds_max-*.whl`

## Step 2: Run Linting and Formatting

Before committing, ensure code passes all checks:

```powershell
# Format code
hatch run fmt

# Run linter
hatch run lint

# Run type checker
hatch run typing
```

## Step 3: Run Unit Tests

Run the full unit test suite:

```powershell
hatch run test
```

For faster iteration, run specific tests:

```powershell
# Run tests for a specific module
hatch run test test/unit/deadline_adaptor_for_3ds_max/MaxClient/

# Run a single test file
hatch run test test/unit/deadline_adaptor_for_3ds_max/MaxClient/render_handlers/test_vray_handler.py

# Run tests matching a pattern
hatch run test -k "test_vray"
```

## Step 4: Run Integration Tests

Integration tests require 3ds Max to be installed.

### Basic V-Ray Test

```powershell
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/vray_simple_test/expected_job_bundle"
```

### Test with Path Mapping

**Important**: Use `test-3dsmax-adapter-run.ps1` for path mapping tests:

```powershell
.\scripts\test-3dsmax-adapter-run.ps1 `
    -JobBundleDir "test/integ/test_scripts/vray_vrmesh_test_remap/expected_job_bundle" `
    -PathMappingFile "test/integ/test_scripts/vray_vrmesh_test_remap/path_mapping_rules.json"
```

### Skip Wheel Installation (faster iteration)

```powershell
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/vray_simple_test/expected_job_bundle" -SkipInstall
```

## Step 5: Build Adaptor Wheels (Developer Option)

For testing adaptor changes on a live Deadline Cloud farm, build wheels for all dependencies:

```powershell
# Build wheels for openjd-adaptor-runtime, deadline, and deadline-cloud-for-3ds-max
.\scripts\build_wheels.ps1

# Or clean and rebuild
.\scripts\build_wheels.ps1 -Clean
```

This creates wheels in the `wheels/` directory:
- `openjd_adaptor_runtime-*.whl`
- `deadline-*.whl`
- `deadline_cloud_for_3ds_max-*.whl`

### Testing Adaptor Wheels on Workers

1. **Enable developer options** before launching 3ds Max:
   ```powershell
   $env:DEADLINE_ENABLE_DEVELOPER_OPTIONS = "true"
   & "D:\ProgramFiles\Autodesk\3ds Max 2025\3dsmax.exe"
   ```

2. **Open the submitter** and go to Scene Settings tab

3. **Enable "Override Adaptor Wheels"** checkbox (only visible with developer options)

4. **Add wheels directory** to Job Attachments tab:
   - Click "Add Directory"
   - Browse to `D:\workspace\3dsmax\deadline-cloud-for-3ds-max\wheels`

5. **Submit the job** - The worker will:
   - Create a Python virtual environment
   - Install your development wheels
   - Use your modified adaptor to run the job

### Prerequisites for Building Wheels

The sibling repositories must be cloned:
```
workspace/
├── openjd-adaptor-runtime-for-python/
├── deadline-cloud/
└── deadline-cloud-for-3ds-max/
```

Clone missing repositories:
```powershell
cd D:\workspace\3dsmax
git clone https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python.git
git clone https://github.com/aws-deadline/deadline-cloud.git
```

## Step 6: Check Logs

After running integration tests:

```powershell
# View last 100 lines
Get-Content 'C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log' -Tail 100

# Search for errors
Select-String -Path 'C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log' -Pattern "error|exception" -CaseSensitive:$false | Select-Object -Last 20
```

## Common Issues

### Wrong Python Version
Ensure 3ds Max Python is being used:
```powershell
& "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" --version
```

### Wheel Not Found
Build the wheel first: `hatch build -t wheel`

### Path Mapping Not Working
- Use `test-3dsmax-adapter-run.ps1` for path mapping tests
- Path mapping rules only work with absolute paths
- `test-3dsmax-openjd-run.ps1` does NOT pass rules to adaptor's `map_path()`