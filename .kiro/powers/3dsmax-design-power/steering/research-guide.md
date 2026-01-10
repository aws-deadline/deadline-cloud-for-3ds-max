---
inclusion: manual
---

# Research Guide for 3ds Max Designs

This guide covers how to research and validate design decisions for 3ds Max and V-Ray features.

## Key Insight: MAXScript = pymxs

**All MAXScript methods documented for 3ds Max work in pymxs!**

The Autodesk documentation doesn't clearly explain the binding, but testing confirms that ALL MAXScript methods are available in pymxs. For example:

```python
from pymxs import runtime as rt

# MAXScript: maxOps.GetCurRenderElementMgr()
# Works identically in pymxs:
re_mgr = rt.maxOps.GetCurRenderElementMgr()
re_mgr.AddRenderElement(rt.VRayLightSelect())
```

Reference: [GitHub Discussion #164](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/discussions/164)

## 3ds Max Documentation Sources

### Official Autodesk Documentation

1. **MAXScript Reference**
   - Search: "3ds Max MAXScript [topic]"
   - URL pattern: `help.autodesk.com/view/3DSMAX/[version]/ENU/?guid=...`
   - Covers: All MAXScript functions, objects, and properties

2. **pymxs Python API**
   - Search: "3ds Max pymxs [topic]"
   - Key concepts:
     - `pymxs.runtime` (aliased as `rt`) provides MAXScript access
     - Most MAXScript translates directly to pymxs
     - Use `rt.execute()` for complex MAXScript strings

3. **3ds Max Python API**
   - Search: "3ds Max Python API [topic]"
   - Covers: Native Python bindings (separate from pymxs)

### V-Ray Documentation

1. **V-Ray MAXScript Reference**
   - URL: `docs.chaos.com/display/VMAX/MAXScript`
   - Covers: All V-Ray-specific properties and methods

2. **V-Ray Render Elements**
   - URL: `docs.chaos.com/display/VMAX/Render+Elements`
   - Covers: LightMix, cryptomatte, AOVs, etc.

3. **V-Ray Frame Buffer (VFB)**
   - URL: `docs.chaos.com/display/VMAX/V-Ray+Frame+Buffer`
   - Covers: VFB settings, output options

## Key MAXScript/pymxs Patterns

### Accessing the Current Renderer

```python
from pymxs import runtime as rt

renderer = rt.renderers.current
renderer_name = str(renderer)
renderer_class_id = str(renderer.classid)
```

### V-Ray Renderer Detection

```python
# Class IDs (may have L suffix for 64-bit)
VRAY_STANDARD = ["#(1941615238, 2012806412)", "#(1941615238L, 2012806412L)"]
VRAY_RT = ["#(1770671000, 1323107829)", "#(1770671000L, 1323107829L)"]

def get_renderer_type() -> str:
    class_id = str(rt.renderers.current.classid)
    if any(cid in class_id for cid in VRAY_STANDARD):
        return "vray"
    elif any(cid in class_id for cid in VRAY_RT):
        return "vrayrt"
    return "unknown"
```

### V-Ray Settings Access Pattern

```python
def get_vray_settings():
    """Get V-Ray settings object, handling RT nested structure."""
    if get_renderer_type() == "vrayrt":
        return rt.renderers.current.V_Ray_settings
    return rt.renderers.current
```

### Common V-Ray Properties

| Property | Type | Description |
|----------|------|-------------|
| `output_on` | bool | Enable V-Ray VFB |
| `output_splitgbuffer` | bool | Enable split render channels |
| `output_splitfilename` | str | Output path for split channels |
| `output_splitbitmap` | bitmap | Required for render elements |
| `output_splitRGB` | bool | Include RGB channel |
| `output_splitAlpha` | bool | Include Alpha channel |
| `output_rawFileName` | str | Raw .vrimg file path |
| `output_saveRawFile` | bool | Enable raw file saving |
| `output_separateFolders` | bool | Separate folders per element |

### Scene Object Access

```python
# All objects
for obj in rt.objects:
    print(obj.name, rt.classOf(obj))

# Specific class
proxies = [obj for obj in rt.objects if rt.classOf(obj) == rt.VRayProxy]

# By name
node = rt.getNodeByName("ObjectName")

# Cameras
for cam in rt.cameras:
    print(cam.name)
```

### Render Elements Access

```python
# Get render element manager
re_mgr = rt.maxOps.GetCurRenderElementMgr()

# Iterate render elements
for i in range(re_mgr.NumRenderElements()):
    element = re_mgr.GetRenderElement(i)
    print(f"{element.elementName}: enabled={element.enabled}")

# Add a render element
re_mgr.AddRenderElement(rt.VRayLightSelect())

# V-Ray element properties (all have 'enabled' and 'vrayVFB')
element.enabled = False
element.vrayVFB = False
```

## Deadline 10 Code Reference

### Key Files to Reference

1. **Plugin Execution**: `3dsmax/plugins/3dsmax/3dsmax.py`
   - `SetVraySplitBufferFile()` - Split buffer path setting
   - `SetVrayRawBufferFile()` - Raw buffer path setting
   - `IsVrayRT()` - V-Ray RT detection

2. **MAXScript Customization**: `3dsmax/plugins/3dsmax/customize.ms`
   - `getRendererIdString()` - Renderer detection
   - V-Ray settings schema (lines 1780-1890)
   - Settings access pattern (lines 1476-1479)

3. **Submission Logic**: `3dsmax/submission/3dsmax/Main/SubmitMaxToDeadline_Functions.ms`
   - Job info parameter writing
   - Scene analysis and validation

### If Code Not Available

Ask the user:
> "I need to reference the Deadline 10 implementation for [specific feature]. Could you provide the relevant code from:
> - `3dsmax/plugins/3dsmax/3dsmax.py` (lines X-Y)
> - `3dsmax/plugins/3dsmax/customize.ms` (function name)
> 
> Specifically, I'm looking for how [feature] was implemented."

## Internet Research Guidelines

### When to Search

1. Documentation is unclear or incomplete
2. Looking for version-specific behavior
3. Finding community workarounds
4. Verifying API behavior

### Effective Search Queries

- `"MAXScript" "[property name]" site:forums.autodesk.com`
- `"V-Ray" "MAXScript" "[feature]" site:forums.chaosgroup.com`
- `"pymxs" "[topic]" site:stackoverflow.com`
- `"3ds Max" "[error message]"`

### Evaluating Sources

**Prefer:**
- Official documentation
- Autodesk/Chaos Group forums (official responses)
- Stack Overflow (high-voted answers)
- Recent posts (within 2-3 years)

**Be cautious with:**
- Old forum posts (API may have changed)
- Unofficial tutorials (may have errors)
- AI-generated content (may hallucinate)

## Knowledge Gap Protocol

When you encounter a knowledge gap:

1. **Document what you know**
   - What API/feature is involved?
   - What have you found so far?
   - What specific information is missing?

2. **Ask the user clearly**
   > "I need clarification on [topic]. Specifically:
   > - [Question 1]
   > - [Question 2]
   > 
   > Do you have documentation or code examples for this?"

3. **Propose alternatives if possible**
   > "I'm not certain about [X], but based on [Y], I believe we could:
   > - Option A: [description]
   > - Option B: [description]
   > 
   > Which approach would you prefer, or do you have more information?"

## Version Compatibility Notes

### V-Ray Version Differences

- Property names may change between versions (e.g., `output_rawFileName` vs `output_rawFilename`)
- New features may not exist in older versions
- Class IDs are generally stable

### 3ds Max Version Differences

- pymxs availability (2017+)
- Python version (3.7+ in recent versions)
- API changes between major versions

Always note which versions your design targets and any version-specific handling needed.