---
name: "3dsmax-design-power"
displayName: "3ds Max Design Power"
description: "Structured design assistant for 3ds Max and V-Ray features in Deadline Cloud. Creates comprehensive design documents covering data structures, UX changes, job templates, and adapter modifications."
keywords: ["3dsmax", "vray", "design", "maxscript", "pymxs", "deadline", "render"]
author: "AWS Deadline Cloud Team"
---

# 3ds Max Design Power

## Overview

A structured design assistant for creating comprehensive feature designs for 3ds Max and V-Ray integration with AWS Deadline Cloud. This power helps create well-structured design documents following a consistent four-section format that covers all aspects of implementation.

## Code Snippet Style Guide

When including code in design documents, use **concise inline snippets** in the main sections and put **full implementations in an appendix**.

### Inline Code Format

Show only the relevant changes with context:

```python
def existing_function():
    ...existing logic...
    
    # NEW: Add feature X support
    if feature_x_enabled:
        self._configure_feature_x(data)
    
    ...rest of function...
```

### Appendix Format

Put complete implementations in a clearly marked appendix section:

```markdown
---

## Appendix: Full Code Implementations

<!-- REVIEW: New export_vrscene implementation -->

### A.1 VrayHandler.export_vrscene (Full Implementation)

\`\`\`python
def export_vrscene(self, data: dict) -> None:
    """Full implementation here..."""
    # Complete code
\`\`\`
```

### Guidelines

1. **Data structures are the exception**: Always show full definitions - they anchor the design
2. **Other sections**: Show what changes and where, not full implementations
3. **Use `...` or comments** to indicate existing/unchanged code
4. **Flag new sections** with `<!-- REVIEW: description -->` comments in the appendix
5. **Don't include review tags** in final generated code

## Available Steering Files

This power has three steering files for detailed workflows:

- **design-workflow.md** - Step-by-step guide for creating design documents
- **research-guide.md** - How to research MAXScript/pymxs APIs and V-Ray documentation
- **deadline-cloud-architecture.md** - Architecture overview of submitter → adaptor → MaxClient flow

## Design Document Structure

Every design document MUST follow this four-section structure:

### 1. Data Structures to Change or Add

Define all data model changes including:
- New dataclasses or TypedDicts
- Modifications to existing data structures
- Job parameter schemas
- Configuration objects
- Type annotations (use `Any` for pymxs objects)

### 2. UX Changes (Submitter Dialog)

Document all user-facing changes:
- New UI controls (dropdowns, checkboxes, text fields)
- Control placement and grouping
- Default values and validation
- Tooltips and help text
- Conditional visibility logic

### 3. Job Template and Bundle Changes

Specify modifications to:
- Job template YAML structure
- New parameters and their types
- Parameter dependencies and conditions
- Asset references and attachments

### 4. Adapter Server-Client Changes

Detail the runtime implementation:
- Handler modifications (DefaultMaxHandler, VrayHandler, etc.)
- New action handlers
- MaxClient changes
- Path mapping considerations
- pymxs/MAXScript API usage

## Research Requirements

Before finalizing any design, perform this research:

### 1. 3ds Max and V-Ray Documentation
- MAXScript API reference
- pymxs Python bindings
- V-Ray MAXScript properties
- Renderer class IDs and detection

### 2. Deadline 10 Historical Implementation
If Deadline 10 code is not available, ASK THE USER to provide relevant code snippets.

### 3. Internet Research
Query the internet when documentation is unclear or incomplete.

## Key Technical Patterns

### pymxs and MAXScript Integration

**Key Insight**: All MAXScript methods documented for 3ds Max will work in pymxs!

```python
from pymxs import runtime as rt

# MAXScript methods work identically in pymxs:
re_mgr = rt.maxOps.GetCurRenderElementMgr()
re_mgr.AddRenderElement(rt.VRayLightSelect())
```

### V-Ray Renderer Detection

```python
VRAY_STANDARD_CLASS_IDS = ["#(1941615238, 2012806412)", "#(1941615238L, 2012806412L)"]
VRAY_RT_CLASS_IDS = ["#(1770671000, 1323107829)", "#(1770671000L, 1323107829L)"]

def is_vray_rt() -> bool:
    renderer_class_id = str(rt.renderers.current.classid)
    return any(cid in renderer_class_id for cid in VRAY_RT_CLASS_IDS)
```

### V-Ray Settings Access

```python
# Standard V-Ray: direct access
rt.renderers.current.output_splitfilename = path

# V-Ray RT: nested V_Ray_settings object
rt.renderers.current.V_Ray_settings.output_splitfilename = path
```

## Example Designs

Reference these existing design documents:
- `design/vray_output_paths_design.md` - V-Ray output path handling
- `design/vray_out_buffer.md` - VFB output filename handling
- `design/vrmesh.md` - VRMesh path mapping

## External References

- [GitHub Discussion #163 - Render Elements Design](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/discussions/163)
- [GitHub Discussion #164 - MAXScript/pymxs Integration](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/discussions/164)
- [OpenJD Sessions for Python](https://github.com/OpenJobDescription/openjd-sessions-for-python)