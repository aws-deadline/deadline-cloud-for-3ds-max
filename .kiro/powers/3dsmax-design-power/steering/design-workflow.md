---
inclusion: manual
---

# 3ds Max Design Workflow Guide

This guide walks through creating a comprehensive design document for a new 3ds Max / V-Ray feature.

## Step 1: Understand the Feature Request

Before starting the design:
1. Clarify the user's goal and expected outcome
2. Identify which renderers are affected (V-Ray Standard, V-Ray RT, Arnold, etc.)
3. Determine if this is a new feature or modification to existing behavior
4. Ask clarifying questions if the scope is unclear

## Step 2: Research Phase

### 2.1 Search 3ds Max / V-Ray Documentation

Look up relevant MAXScript and pymxs APIs:
- Property names and types
- Method signatures
- Class IDs for renderer detection
- Version-specific differences

Key search terms:
- "MAXScript [property name]"
- "pymxs [object type]"
- "V-Ray MAXScript [feature]"
- "3ds Max Python API [topic]"

### 2.2 Check Deadline 10 Implementation

If the feature existed in Deadline 10, review:
- How was it implemented in `3dsmax.py`?
- What MAXScript was used in `customize.ms`?
- How was submission handled in `SubmitMaxToDeadline_Functions.ms`?

**If Deadline 10 code is not available, ask the user:**
> "I need to reference the Deadline 10 implementation for [feature]. Could you provide the relevant code from [specific file]?"

### 2.3 Internet Research

Search for:
- Community solutions and workarounds
- Known issues and limitations
- Version compatibility notes
- Best practices

## Step 3: Design the Data Structures

Data structures anchor the design - **always include full definitions** for new types:

```python
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum

class FeatureMode(Enum):
    """Mode options for Feature X."""
    OPTION_A = "option_a"
    OPTION_B = "option_b"

@dataclass
class FeatureSettings:
    """Settings for Feature X workflow."""
    
    enabled: bool = False
    mode: FeatureMode = FeatureMode.OPTION_A
    output_path: Optional[str] = None
    
    # Processing options
    compress_output: bool = True
    verbose_level: int = 3
```

Consider:
- What data flows from submitter to adapter?
- What state needs to be maintained during rendering?
- What types should be used (use `Any` for pymxs objects)?

**Note:** Data structures are the exception to the "concise snippets" rule - show them in full since they anchor the entire design.

## Step 4: Design the UX

Sketch out the submitter dialog changes:

1. **Control Type**: Dropdown, checkbox, text field, etc.
2. **Placement**: Which group/section does it belong to?
3. **Default Value**: What's the sensible default?
4. **Validation**: What values are valid?
5. **Dependencies**: Does it depend on other settings?

Example:
```
Group: V-Ray Settings
├── [Checkbox] Enable Feature X (default: unchecked)
│   └── [Dropdown] Feature X Mode (visible when enabled)
│       ├── Option A
│       └── Option B
└── [Text Field] Custom Path (optional)
```

## Step 5: Design Job Template Changes

Define the job bundle modifications:

```yaml
parameterDefinitions:
  - name: FeatureXEnabled
    type: STRING
    default: "false"
    allowedValues: ["true", "false"]
    
  - name: FeatureXMode
    type: STRING
    default: "option_a"
    allowedValues: ["option_a", "option_b"]
    userInterface:
      control: DROPDOWN
      label: "Feature X Mode"
```

Consider:
- Parameter types and constraints
- Conditional parameters
- Asset references

## Step 6: Design Adapter Changes

Plan the runtime implementation using **concise inline snippets** that show what changes:

### Handler Changes (Inline)
```python
class VrayHandler(DefaultMaxHandler):
    def __init__(self, gpu: bool) -> None:
        super().__init__()
        ...existing init...
        
        # NEW: Register feature X action
        self.action_dict["feature_x"] = self.configure_feature_x

    def configure_feature_x(self, data: dict[str, Any]) -> None:
        """Configure Feature X before rendering."""
        # See Appendix A.1 for full implementation
        ...
```

### pymxs Implementation (Inline)
```python
def _apply_feature_x(self, mode: str) -> None:
    vray = rt.renderers.current
    if is_vray_rt():
        vray = rt.renderers.current.V_Ray_settings
    
    # NEW: Set feature X property
    vray.feature_x_mode = mode
```

Put full implementations in the **Appendix** section with review flags.

## Step 7: Plan Testing

Define unit tests with mocked pymxs:

```python
@patch('deadline.max_adaptor.MaxClient.render_handlers.vray_handler.rt')
def test_feature_x_configuration(self, mock_rt):
    """Test Feature X is correctly configured."""
    # Setup
    handler = VrayHandler(gpu=False)
    
    # Execute
    handler.configure_feature_x({"feature_x_enabled": True, "feature_x_mode": "option_a"})
    
    # Verify
    assert mock_rt.renderers.current.some_property == expected_value
```

## Step 8: Document Files to Modify

Create a summary table:

| File | Changes |
|------|---------|
| `src/deadline/max_submitter/ui/...` | Add UI controls |
| `src/deadline/max_submitter/job_bundle/template.yaml` | Add parameters |
| `src/deadline/max_adaptor/MaxClient/render_handlers/vray_handler.py` | Add handler method |
| `src/deadline/max_shared/utilities/max_utils.py` | Add utility functions |
| `test/unit/.../test_vray_handler.py` | Add unit tests |

## Common Pitfalls

1. **Forgetting V-Ray RT**: Always handle both standard V-Ray and V-Ray RT
2. **Missing type annotations**: All non-pymxs code needs proper types
3. **Hardcoded paths**: Use path mapping for cross-platform support
4. **No error handling**: pymxs operations can fail silently
5. **Untested edge cases**: Test with missing/invalid data

## Step 9: Create the Appendix

Put all full code implementations in a clearly marked appendix at the end of the design document.

### Appendix Format

```markdown
---

## Appendix: Full Code Implementations

<!-- REVIEW: Brief description of what's new -->

### A.1 ClassName.method_name (Full Implementation)

**File:** `src/deadline/max_adaptor/...`

\`\`\`python
def method_name(self, data: dict) -> None:
    """
    Full docstring here.
    """
    # Complete implementation
    ...
\`\`\`

### A.2 New Utility Module

**File:** `src/deadline/max_shared/utilities/new_utils.py` (new file)

\`\`\`python
"""
Module docstring.
"""
# Full module code
\`\`\`
```

### Guidelines

1. **Flag sections for review** with `<!-- REVIEW: description -->` HTML comments
2. **Include file paths** for each code block
3. **Number appendix sections** (A.1, A.2, etc.) for easy reference
4. **Don't include review tags** in final generated code - they're for design review only
5. **Reference appendix from main sections** with "See Appendix A.X for full implementation"