<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. -->

# Output Filename Token Pattern System — Design Document

## Overview

This feature adds a Deadline 10-style output filename token pattern system to the Deadline Cloud for 3ds Max submitter. The pattern field replaces the existing "Output Filename" field — users type the full filename directly, with optional tokens that get resolved by the adaptor at render time.

**WYSIWYG principle:** The pattern is passed through exactly as the user types it. No automatic cleanup of delimiters, no automatic frame padding adjustment. What you see is what you get.

**Supported tokens:**
- `<camera>` — Scene camera name (e.g., "Camera001", "RenderCam")
- `<stateset>` — State Set name (e.g., "DayLight", "NightTime")
- `<scene>` — Scene file name without extension (e.g., "myScene")

Token definitions are maintained in a single source of truth: `SUPPORTED_TOKENS` dict in `filename_utils.py`. The UI tooltip is generated from this dict via `get_tokens_tooltip()`, so adding a new token only requires updating one place.

Everything else in the pattern is literal text (the base name, frame padding, delimiters).

**All tokens are resolved by the adaptor at render time.** The submitter passes the raw pattern through to init-data. The adaptor already has all the data it needs: camera from run-data/init-data, state set from init-data, scene name from the scene file path in init-data.

**Example patterns and results:**

| Pattern | Camera=RenderCam, StateSet=DayLight, Scene=myScene |
|---------|-----------------------------------------------------|
| `<camera>_<stateset>_<scene>_###` | `RenderCam_DayLight_myScene_###` |
| `<camera>_<stateset>_myRender_###` | `RenderCam_DayLight_myRender_###` |
| `<stateset>_<scene>_###` | `DayLight_myScene_###` |
| `<scene>_###` | `myScene_###` |
| `myRender_###` | `myRender_###` |

**Default pattern initialization:**
1. If `rt.rendOutputFilename` is set in 3ds Max Render Setup → pattern is built as `<camera>_<stateset>_{stem from rendOutputFilename}`
2. If not set → pattern is built as `<camera>_<stateset>_<scene>_###`
3. Sticky settings always take precedence over both — if the user previously saved a pattern, that's what loads

---

## 1. Data Structures to Change or Add

### 1.1 New field on `RenderSubmitterUISettings`

**File:** `src/deadline/max_submitter/data_classes.py`

```python
@dataclass
class RenderSubmitterUISettings:
    ...existing fields...

    # Output Filename Pattern (replaces output_name for filename composition)
    # The full output filename with optional <camera>, <stateset>, and <scene> tokens.
    # Everything else is literal text (base name, frame padding, delimiters).
    output_filename_pattern: str = field(
        default="<camera>_<stateset>_<scene>_###", metadata={"sticky": True}
    )
```

The existing `output_name` field is kept for backward compatibility with sticky settings files but is no longer used for filename composition.

### 1.2 No changes to `StateSetData`

The `output_file_name` field on `StateSetData` now carries the raw pattern string (with unresolved tokens). The adaptor resolves all tokens at render time.

### 1.3 Shared utility functions

**File:** `src/deadline/max_shared/utilities/filename_utils.py`

This file contains:
- `SUPPORTED_TOKENS` — single source of truth dict mapping token strings to descriptions
- `get_tokens_tooltip()` — builds the UI tooltip string from `SUPPORTED_TOKENS`
- `format_output_filename()` — pure token replacement, no cleanup

```python
SUPPORTED_TOKENS: dict[str, str] = {
    "<camera>": "Scene camera name (e.g., Camera001, RenderCam)",
    "<stateset>": "State set name",
    "<scene>": "Scene file name (without extension)",
}

def format_output_filename(
    pattern: str,
    camera_name: str = "",
    state_set_name: str = "",
    scene_name: str = "",
) -> str:
    """
    Resolve an output filename from a token pattern.
    Pure token replacement — no delimiter cleanup, no padding adjustment.
    """
    if not pattern:
        return ""
    result = pattern
    result = result.replace("<camera>", camera_name)
    result = result.replace("<stateset>", state_set_name)
    result = result.replace("<scene>", scene_name)
    return result
```

---

## 2. UX Changes (Submitter Dialog)

### 2.1 Replace "Output Filename" with pattern-based fields

**File:** `src/deadline/max_submitter/ui/scene_settings_tab.py`

The existing "Output Filename" `QLineEdit` (row 2) is replaced by an "Output Filename Settings" group box containing the pattern and live preview:

```
Row 0: Project Path       [C:/Projects/MyProject        ] (read-only)
Row 1: Output Path        [C:/Output                    ] [...]
Row 2: ┌─ Output Filename Settings ──────────────────────────────────┐
       │  Filename Pattern    [<camera>_<stateset>_<scene>_###    ]  │
       │  Filename Preview    RenderCam_DayLight_myScene_###         │
       └─────────────────────────────────────────────────────────────┘
Row 3: Output File Ext    [OpenEXR Image File (*.exr)   ▼]
Row 4: State Sets          [All State Sets               ▼]
...
```

**Controls:**

| Control | Type | Default | Sticky | Notes |
|---------|------|---------|--------|-------|
| Filename Pattern | `QLineEdit` | (built from render settings, see below) | Yes | Tooltip generated from `SUPPORTED_TOKENS` via `get_tokens_tooltip()` |
| Filename Preview | `QLabel` | (computed) | No | Read-only, updates live. Tooltip says "Example preview of the resolved output filename" |

**Tooltip for Filename Pattern** is generated dynamically from `get_tokens_tooltip()` in `filename_utils.py`. Adding a new token to `SUPPORTED_TOKENS` automatically updates the tooltip.

### 2.2 Default pattern initialization

**File:** `src/deadline/max_submitter/max_render_submitter.py` — in `show_job_bundle_submitter()`

The default pattern is built before sticky settings load:

```python
# Build default pattern from render settings
output_path, output_name, output_ext = max_utils.get_render_output_info()
render_settings.output_path = output_path
render_settings.output_filename_pattern = f"<camera>_<stateset>_{output_name}"
if output_ext:
    render_settings.output_ext = output_ext

# Sticky settings override the pattern if previously saved
render_settings.load_sticky_settings()
```

This means:
- If `rendOutputFilename` = `C:\output\myScene_###.exr` → pattern = `<camera>_<stateset>_myScene_###`
- If `rendOutputFilename` is empty → pattern = `<camera>_<stateset>_<scene>_###`
- If sticky settings exist → pattern = whatever the user last saved

**No automatic override of sticky settings.** Once the user has saved a pattern via submission, it is always respected on next open. There is no tracking of `rendOutputFilename` changes between sessions.

### 2.3 Preview update logic

The preview label updates whenever any of these change:
- `output_filename_pattern_txt` (pattern)
- `state_sets_box` (state set selection)
- `cameras_box` (camera selection)

The preview calls `format_output_filename()` with current UI values. For "All State Sets", the preview uses the first state set name as example. For "All Cameras", the preview uses the first camera name as example. For `<scene>`, the preview uses the current scene name.

### 2.4 No focus-change render settings sync

The submitter does **not** auto-detect changes to `rt.rendOutputFilename` while the dialog is open. If the user changes render output in 3ds Max Render Setup, they must manually update the pattern in the submitter. This avoids silently overriding user input or sticky settings.

### 2.5 No automatic frame padding

The submitter does **not** add or strip frame padding (`#` characters). If the user renders multiple frames without padding in the filename, the output images will overwrite each other — but that's the user's explicit choice. The WYSIWYG principle applies: the pattern is submitted exactly as typed.

---

## 3. Job Template and Bundle Changes

### 3.1 No changes to `default_max_job_template.yaml`

The template stays as-is. The `OutputFileName` parameter now carries the raw pattern with unresolved tokens.

### 3.2 No changes to `init_data.schema.json`

No new fields. The existing `output_file_name` field carries the raw pattern string.

### 3.3 Changes to `max_render_submitter.py` — pass raw pattern through

**File:** `src/deadline/max_submitter/max_render_submitter.py`

In `on_create_job_bundle_callback()`, the raw pattern is passed as `output_file_name` for all cases. Output directory and extension are resolved using `max_utils.get_render_output_info()`:

```python
if rt.rendOutputFilename:
    output_dir, _, rend_ext = max_utils.get_render_output_info()
    output_file_name = settings.output_filename_pattern
    output_file_format = settings.output_ext if settings.output_ext else rend_ext
else:
    output_dir = settings.output_path
    output_file_name = settings.output_filename_pattern
    output_file_format = settings.output_ext
```

---

## 4. Adapter Changes

### 4.1 Changes to `DefaultMaxHandler.start_render()`

**File:** `src/deadline/max_adaptor/MaxClient/render_handlers/default_max_handler.py`

The adaptor resolves all tokens in `start_render()` before building the output path:

```python
from deadline.max_shared.utilities.filename_utils import format_output_filename

def start_render(self, data: dict) -> None:
    ...existing frame/output validation...

    # Resolve all tokens in the output filename
    scene_name = Path(rt.maxFileName).stem if rt.maxFileName else ""
    state_set_name = self.state_set_name or ""
    camera_name = camera or ""

    output_name = format_output_filename(
        pattern=self.output_name,
        camera_name=camera_name,
        state_set_name=state_set_name,
        scene_name=scene_name,
    )

    output_name = self.reformat_framenumber_padding(output_name, frame)
    output_file = output_name + self.output_format
    output_path = os.path.join(self.output_dir, output_file)
    ...
```

### 4.2 State set name stored from init-data

The adaptor stores the state set name from init-data so it's available in `start_render()`:

```python
def set_state_set(self, data: dict) -> None:
    state_set_name = data.get("state_set")
    self.state_set_name = state_set_name or ""
    ...existing state set logic...
```

---

## 5. Utility: `get_render_output_info()`

**File:** `src/deadline/max_submitter/utilities/max_utils.py`

Uses `pathlib.Path` for clean path decomposition:

```python
def get_render_output_info() -> tuple[str, str, str]:
    if rt.rendOutputFilename:
        output_path = Path(rt.rendOutputFilename)
        return str(output_path.parent), output_path.stem, output_path.suffix
    else:
        return get_scene_dir(), get_scene_name() + "_###", ""
```

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `src/deadline/max_shared/utilities/filename_utils.py` | `SUPPORTED_TOKENS` dict, `get_tokens_tooltip()`, `format_output_filename()` (pure token replacement, no cleanup) |
| `src/deadline/max_submitter/data_classes.py` | Add `output_filename_pattern` sticky field |
| `src/deadline/max_submitter/ui/scene_settings_tab.py` | "Output Filename Settings" group box (pattern + preview); tooltip from `get_tokens_tooltip()`; imports moved to top-level |
| `src/deadline/max_submitter/max_render_submitter.py` | Build default pattern; pass raw pattern as `output_file_name`; use `get_render_output_info()` helper |
| `src/deadline/max_submitter/utilities/max_utils.py` | `get_render_output_info()` simplified with `pathlib.Path` |
| `src/deadline/max_adaptor/MaxClient/render_handlers/default_max_handler.py` | Resolve all tokens in `start_render()`, store `state_set_name` |
| `test/unit/...` | Unit tests for `format_output_filename()` |
