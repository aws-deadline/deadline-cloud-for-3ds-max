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

### Inspecting V-Ray Renderer Properties

To list all available properties on the current V-Ray renderer, run this in the MAXScript Listener:

```maxscript
vr = renderers.current
showproperties vr
```

This is the authoritative source for valid V-Ray property names. Always check this before using `_set_vray_property()` — don't guess property names from naming patterns.

### V-Ray Output Properties Reference (V-Ray 7)

These are the output-related properties on the V-Ray renderer object. Use `_set_vray_property(name, value, warnings)` to set them from Python.

| Property | Type | Description |
|----------|------|-------------|
| `output_on` | boolean | Master switch — enables/disables V-Ray's own output pipeline |
| `output_saveFile` | boolean | Enables V-Ray file saving (main beauty output) |
| `output_fileName` | string | Main output file path for V-Ray's direct file output |
| `output_fileOnly` | boolean | Render to file only (skip VFB display) |
| `output_splitgbuffer` | boolean | Enable split buffer (separate files per render element) |
| `output_splitfilename` | filename | Base filename for split buffer output |
| `output_splitRGB` | boolean | Save RGB channels in split buffer mode |
| `output_splitAlpha` | boolean | Save Alpha channel in split buffer mode |
| `output_splitbitmap` | bitmap | Split buffer bitmap object |
| `output_saveRawFile` | boolean | Enable raw file output (.vrimg/.exr multichannel) |
| `output_rawFileName` | filename | Output path for raw file |
| `output_rawExrUseHalf` | boolean | Use half-precision floats in raw EXR |
| `output_rawExrDeep` | boolean | Enable deep EXR output |
| `output_rawSaveColorCorrections` | boolean | Save color corrections in raw file |
| `output_rawSaveColorCorrectionsRE` | boolean | Save color corrections for render elements |
| `output_separateFolders` | boolean | Save render elements in separate folders |
| `output_saveCryptomattesSeparately` | boolean | Save Cryptomatte passes as separate files |
| `output_userigbe` | boolean | Enable V-Ray Frame Buffer (VFB) |
| `output_resumableRendering` | boolean | Enable resumable rendering |
| `output_progressiveAutoSave` | float | Auto-save interval for progressive rendering |
| `output_force32bit_3dsmax_vfb` | boolean | Force 32-bit in 3ds Max VFB |
| `output_width` | integer | Output image width |
| `output_height` | integer | Output image height |
| `output_aspect` | float | Output pixel aspect ratio |

### V-Ray Output Modes

V-Ray ignores `rt.rendOutputFilename` / `rt.rendSaveFile` — it uses its own output properties instead. There are three output modes:

1. **Direct file output**: `output_on=True` + `output_saveFile=True` + `output_fileName=path` — writes the beauty pass to a single file
2. **Split buffer**: `output_splitgbuffer=True` + `output_splitRGB=True` + `output_splitfilename=path` — writes render elements to separate files
3. **Raw output**: `output_saveRawFile=True` + `output_rawFileName=path` — writes all channels into a single multichannel .vrimg or .exr

For non-raw formats without render elements, use direct file output (mode 1). The split buffer (mode 2) is for render elements. Raw output (mode 3) is for .exr and .vrimg.

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

### V-Ray render completes but no output file is saved
V-Ray ignores 3ds Max's `rt.rendOutputFilename` — it uses its own output properties. If `_configure_renderer_output` returns `False` for V-Ray, `start_render` sets the 3ds Max output path, but V-Ray won't write anything.

For non-raw formats (.jpg, .png, .tga, etc.), you must explicitly enable V-Ray's output:
```python
_set_vray_property("output_on", True, warnings)
_set_vray_property("output_saveFile", True, warnings)
_set_vray_property("output_fileName", filepath, warnings)
```
See "V-Ray Output Modes" above for the full explanation.

### Render elements not saved
```powershell
Select-String -Path 'C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log' -Pattern "render_element_manager" | Select-Object -Last 20
```