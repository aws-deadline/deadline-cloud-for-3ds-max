# Integration Testing Guide

How to run and create integration tests for the 3ds Max adaptor using OpenJD run or adaptor run scripts.

## Running Integration Tests

### Prerequisites

1. 3ds Max 2025 or 2026 installed
2. V-Ray installed (for V-Ray tests)
3. Built wheel in `dist/` directory

### Choosing the Right Test Script

| Script | Use Case |
|--------|----------|
| `test-3dsmax-openjd-run.ps1` | General testing via OpenJD CLI |
| `test-3dsmax-adapter-run.ps1` | **Path mapping tests** - runs adaptor directly |

**Important**: For path mapping tests, use `test-3dsmax-adapter-run.ps1`. The OpenJD CLI script does NOT pass rules to `map_path()`.

### Script Parameters

```powershell
.\scripts\test-3dsmax-adapter-run.ps1 `
    -JobBundleDir "path/to/job_bundle" `
    -WheelPath "dist/deadline_cloud_for_3ds_max-*.whl" `
    -MaxVersion "2026" `
    -Step 0 `
    -PathMappingFile "path/to/path_mapping_rules.json" `
    -SkipInstall `
    -ShowOutput
```

## Ready-to-Run Test Commands

### VRMesh Path Mapping Test (V-Ray with path remapping)
```powershell
Remove-Item "test/integ/test_scripts/vray_vrmesh_remap_test/output/*" -Force -ErrorAction SilentlyContinue
$env:PATH = "C:\Users\RDP\AppData\Roaming\Python\Python311\Scripts;$env:PATH"
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/vray_vrmesh_remap_test/expected_job_bundle" -PathMappingFile "test/integ/test_scripts/vray_vrmesh_remap_test/path_mapping_rules.json" -SkipInstall 2>&1 | Out-File -FilePath "tmp/vrmesh_remap_test_output.txt" -Encoding utf8
```

### V-Ray Render Elements Test (V-Ray CPU or GPU)
```powershell
Remove-Item "test/integ/test_scripts/vray_re_test/output_images/*" -Force -ErrorAction SilentlyContinue
$env:PATH = "C:\Users\RDP\AppData\Roaming\Python\Python311\Scripts;$env:PATH"
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/vray_re_test/expected_job_bundle" -SkipInstall 2>&1 | Out-File -FilePath "tmp/vray_test_output.txt" -Encoding utf8
```

### LightMix Test (V-Ray GPU)
```powershell
Remove-Item "test/integ/test_scripts/lightmix/output_images/*" -Force -ErrorAction SilentlyContinue
$env:PATH = "C:\Users\RDP\AppData\Roaming\Python\Python311\Scripts;$env:PATH"
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/lightmix/expected_job_bundle" -SkipInstall 2>&1 | Out-File -FilePath "tmp/lightmix_test_output.txt" -Encoding utf8
```

### RE Enabled Test (Standard 3dsMax renderer)
```powershell
Remove-Item "test/integ/test_scripts/re_enabled_test/output_images/*" -Force -ErrorAction SilentlyContinue
$env:PATH = "C:\Users\RDP\AppData\Roaming\Python\Python311\Scripts;$env:PATH"
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/re_enabled_test/expected_job_bundle" -SkipInstall 2>&1 | Out-File -FilePath "tmp/re_enabled_test_output.txt" -Encoding utf8
```

### RE Disabled Test (Standard 3dsMax renderer)
```powershell
Remove-Item "test/integ/test_scripts/re_disabled_test/output_images/*" -Force -ErrorAction SilentlyContinue
$env:PATH = "C:\Users\RDP\AppData\Roaming\Python\Python311\Scripts;$env:PATH"
.\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir "test/integ/test_scripts/re_disabled_test/expected_job_bundle" -SkipInstall 2>&1 | Out-File -FilePath "tmp/re_disabled_test_output.txt" -Encoding utf8
```

## Output Locations and Expected Results

| Test | Output Folder | Expected Files |
|------|---------------|----------------|
| vray_vrmesh_remap_test | `test/integ/test_scripts/vray_vrmesh_remap_test/output/` | 1 |
| vray_re_test (CPU) | `test/integ/test_scripts/vray_re_test/output_images/` | ~64 |
| vray_re_test (GPU) | `test/integ/test_scripts/vray_re_test/output_images/` | ~85 |
| lightmix | `test/integ/test_scripts/lightmix/output_images/` | 7 |
| re_enabled_test | `test/integ/test_scripts/re_enabled_test/output_images/` | 23 |
| re_disabled_test | `test/integ/test_scripts/re_disabled_test/output_images/` | 1 |

## Test Configuration Parameters

Key parameters in `parameter_values.yaml`:
- `VRayRenderElementsVFBControl: 'false'` - V-Ray VFB handles output (vray_re_test, lightmix)
- `VRayRenderElementsVFBControl: 'true'` - 3dsMax framebuffer handles output
- `VRaySplitBufferSupport: 'true'` - Enable split buffer for render elements

Key parameters in `template.yaml`:
- `renderer: V_Ray_7_Hotfix_2` - V-Ray CPU renderer
- `renderer: V_Ray_GPU_7_Hotfix_2` - V-Ray GPU renderer

## Available Test Bundles

| Bundle | Description |
|--------|-------------|
| `vray_simple_test` | Basic V-Ray render |
| `vray_vrmesh_test` | V-Ray with VRayProxy |
| `vray_vrmesh_test_remap` | VRMesh with path mapping |
| `vray_vrmesh_remap_test` | VRMesh path remapping test |
| `vray_re_test` | V-Ray render elements (CPU/GPU) |
| `lightmix` | V-Ray LightMix (GPU) |
| `re_enabled_test` | Standard renderer with render elements |
| `re_disabled_test` | Standard renderer without render elements |
| `scanline_simple_test` | Scanline renderer |
| `arnold_simple_test` | Arnold renderer |

## Creating New Test Bundles

### Job Bundle Structure

```
test/integ/test_scripts/my_test/
├── expected_job_bundle/
│   ├── template.yaml          # OpenJD job template
│   └── parameter_values.yaml  # Job parameters
├── scene/
│   └── my_scene.max          # 3ds Max scene file
├── expected_images/          # Expected outputs (optional)
└── tempout/                  # Render output directory
```

### Parameter Values Example

```yaml
parameterValues:
  - name: MaxSceneFile
    value: C:/path/to/scene.max
  - name: Frames
    value: "0"
  - name: OutputFilePath
    value: C:/path/to/output/
  - name: OutputFileFormat
    value: ".jpg"
  - name: ImageWidth
    value: "320"
  - name: ImageHeight
    value: "240"
```

## Testing Path Mapping

### Path Mapping Rules File

```json
{
  "version": "pathmapping-1.0",
  "path_mapping_rules": [
    {
      "source_path_format": "WINDOWS",
      "source_path": "C:/original/assets",
      "destination_path": "C:/remapped/assets"
    }
  ]
}
```

### Running with Path Mapping

```powershell
.\scripts\test-3dsmax-adapter-run.ps1 `
    -JobBundleDir "test/integ/test_scripts/vray_vrmesh_test_remap/expected_job_bundle" `
    -PathMappingFile "test/integ/test_scripts/vray_vrmesh_test_remap/path_mapping_rules.json"
```

### Important Notes

1. **Absolute paths required**: Path mapping only works with absolute paths
2. **Use correct script**: `test-3dsmax-adapter-run.ps1` passes rules to adaptor
3. **On Deadline Cloud**: Worker agent provides actual path mapping rules

## Debugging

### Check 3ds Max Logs

```powershell
# View recent logs
Get-Content 'C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log' -Tail 100

# Search for patterns
Select-String -Path 'C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\2026 - 64bit\ENU\Network\Max.log' -Pattern "VRMesh|VRayProxy|path mapping" -CaseSensitive:$false
```

### Common Log Patterns

| Pattern | Description |
|---------|-------------|
| `LoadFromFile` | Scene file loading |
| `VRMesh path mapping` | VRayProxy path mapping |
| `Remapped VRayProxy` | Successfully remapped proxy |
| `render_element_manager` | Render element config |