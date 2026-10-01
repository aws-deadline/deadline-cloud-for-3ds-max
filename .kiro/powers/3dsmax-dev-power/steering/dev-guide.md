# Dev Guide

## Python Environment

**IMPORTANT**: Use 3ds Max's Python for running integration tests and adaptor code:
- 3ds Max 2026: `C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe`
- 3ds Max 2025: `C:\Program Files\Autodesk\3ds Max 2025\Python\python.exe`

The system Python may not have the required dependencies (pytest, pyyaml, etc.) installed. The test scripts automatically use 3ds Max Python.

## Build & Install Workflow

### Build

```powershell
hatch build
```

This creates a wheel file in `dist/` folder.

### Install to 3ds Max Python

```powershell
$wheel = (Get-ChildItem dist\*.whl | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
& "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip install $wheel --force-reinstall --no-deps 2>&1 | Out-File -FilePath "tmp/pip_install.txt" -Encoding utf8
Select-String -Path "tmp/pip_install.txt" -Pattern "Successfully installed"
```

### Code Quality

```powershell
hatch run fmt      # Format code
hatch run lint     # Run linter
hatch run typing   # Type checking
```

### Unit Tests

```powershell
hatch run test                              # All tests
hatch run test test/unit/path/to/test.py   # Specific file
hatch run test -k "test_vray"              # Pattern match
```

## Integration Tests

See **integration-testing.md** for full details on running tests with OpenJD run or adaptor run scripts.

**Scripts**: `test-3dsmax-openjd-run.ps1` (general) | `test-3dsmax-adapter-run.ps1` (path mapping)

```powershell
# Parameters
-JobBundleDir "path/to/bundle"
-PathMappingFile "path/to/rules.json"  # adapter script only
-MaxVersion "2026"
-SkipInstall                           # Skip wheel reinstall
-ShowOutput
```

## Creating Test Bundles

```
test/integ/test_scripts/my_test/
├── expected_job_bundle/
│   ├── template.yaml
│   └── parameter_values.yaml
├── scene/my_scene.max
└── tempout/
```

**parameter_values.yaml**:
```yaml
parameterValues:
  - name: MaxSceneFile
    value: C:/path/to/scene.max
  - name: Frames
    value: "0"
  - name: OutputFilePath
    value: C:/path/to/output/
```

**path_mapping_rules.json**:
```json
{"version":"pathmapping-1.0","path_mapping_rules":[{"source_path_format":"WINDOWS","source_path":"C:/original","destination_path":"C:/remapped"}]}
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No wheel found | `hatch build -t wheel` |
| Hatch not found | `pip install hatch` |
| Import errors | `pip install -r requirements-testing.txt` |
| Test hangs | `Get-Process 3dsmax* \| Stop-Process -Force` |
| Path mapping fails | Use `test-3dsmax-adapter-run.ps1`, not openjd script |
| VRayProxy not found | V-Ray not loaded |
| Log not appearing | Use `self.log_to_console()` not `print()` |

**Logs**: `C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log`

```powershell
Select-String -Path '...\Max.log' -Pattern "error|VRMesh" -CaseSensitive:$false
```
