# Shared Utilities for 3ds Max Deadline Cloud Integration

This module contains utilities that are shared between the submitter and adaptor components to ensure consistent behavior and avoid code duplication.

## Purpose

The shared utilities module was created to address the need for consistent render elements functionality between:

1. **Submitter Components** - GUI submission, job template generation, validation
2. **Adaptor Components** - Render execution, scene manipulation, validation

## Architecture

```
deadline/
├── max_submitter/         # GUI submission components
├── max_adaptor/           # Render execution components  
└── max_shared/            # Shared utilities
    └── utilities/
        └── max_utils.py   # Shared pymxs utilities
```

## Shared Functions

### Render Elements Detection
- `get_render_elements()` - Render element detection with V-Ray VFB support
- `get_render_element_by_name()` - Find specific render element by name
- `get_render_elements_output_directories()` - Get unique output directories

### Validation
- `validate_render_element_paths()` - Path validation matching Deadline 10's sanity checks
- `validate_render_element_configuration()` - Configuration consistency validation

### Utilities  
- `purify_render_element_name()` - Name purification for file path safety

## Usage

### In Submitter Components
```python
# Import through submitter's max_utils for backward compatibility
from deadline.max_submitter.utilities.max_utils import get_render_elements

render_elements = get_render_elements()
```

### In Adaptor Components  
```python
# Import directly from shared utilities
from deadline.max_shared.utilities.max_utils import get_render_elements

render_elements = get_render_elements()
```

### In MaxClient Actions
The MaxClient now includes render elements actions that use shared utilities:
- `get_render_elements` - Get all render elements in scene
- `validate_render_elements` - Validate render elements paths and configuration  
- `get_render_element_directories` - Get output directories

## Implementation Details

### Enhanced Render Elements Detection
The shared `get_render_elements()` function provides detection matching Deadline 10:
- Skips `Missing_Render_Element_Plug_in` elements
- Includes element index for manipulation
- Detects V-Ray VFB properties
- Stores element object references

### Consistent Validation
All validation functions use the same logic between GUI submission and render execution:
- Path accessibility checks
- Directory existence validation
- Configuration consistency checks
- Missing element detection

### Error Handling
All shared functions include comprehensive error handling:
- Graceful fallbacks for missing pymxs objects
- Detailed logging for debugging
- Consistent error message formats

## Testing

Shared utilities include comprehensive tests in:
- `test/unit/deadline_shared_for_3ds_max/test_shared_max_utils.py`

Tests cover:
- Import functionality from both submitter and shared modules
- Function behavior with mocked pymxs objects
- Edge cases and error conditions
- Name purification logic