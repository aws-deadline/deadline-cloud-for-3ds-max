# Troubleshooting Guide

Common issues and solutions when developing deadline-cloud-for-3ds-max.

## Build Issues

### "No wheel files found in dist directory"
```powershell
hatch build -t wheel
```

### Hatch not found
```powershell
pip install hatch
```

## Test Issues

### Unit tests fail with import errors
```powershell
pip install -r requirements-testing.txt
# Or use hatch environment
hatch run test
```

### Integration test hangs
3ds Max may be waiting for user input. Kill stuck processes:
```powershell
Get-Process 3dsmax* | Stop-Process -Force
```

### "3ds Max Python not found"
```powershell
Test-Path "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe"
```
Use `-MaxVersion` parameter if using a different version.

## V-Ray Issues

### "VRayProxy class not found"
V-Ray is not loaded. Ensure V-Ray is installed and environment is set up.

### VRMesh path not remapped

**Solutions**:
1. Use `test-3dsmax-adapter-run.ps1` (not openjd script)
2. Ensure VRayProxy uses absolute paths
3. Check path mapping rules match source path exactly

**Why OpenJD CLI doesn't work**:
- Applies path mapping to job parameters only
- Adaptor receives empty rules
- `map_path()` returns paths unchanged

## Logging Issues

### Can't find log messages
```powershell
Get-ChildItem 'C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\' -Filter "*.log" | Sort-Object LastWriteTime -Descending
```

### Log messages not appearing
Use `self.log_to_console()` instead of `print()`:
```python
self.log_to_console("My debug message")
```

## Path Issues

### Scene file not found
1. Verify file exists: `Test-Path "C:/path/to/scene.max"`
2. Use forward slashes in YAML/JSON
3. Check `parameter_values.yaml` paths

### Output directory doesn't exist
```powershell
New-Item -ItemType Directory -Path "test/integ/test_scripts/my_test/tempout" -Force
```

## Python Environment Issues

### Wrong Python interpreter
```powershell
& "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -c "import sys; print(sys.executable)"
```

### Module not found in 3ds Max
```powershell
& "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip install dist\deadline_cloud_for_3ds_max-*.whl --force-reinstall --no-deps
```

## Render Issues

### Render produces black image
- Check camera name in job parameters
- Verify scene renders in 3ds Max UI first
- Check lights are enabled

### Render elements not saved
```powershell
Select-String -Path 'C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log' -Pattern "render_element_manager" | Select-Object -Last 20
```