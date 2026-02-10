# Output Filename Token Pattern System — Design Document

## Overview

This feature adds a Deadline 10-style output filename token pattern system to the Deadline Cloud for 3ds Max submitter. The pattern field replaces the existing "Output Filename" field — users type the full filename directly, with optional tokens that get resolved by the adaptor at render time.

**Supported tokens:**
- `<camera>` — Scene camera name (e.g., "Camera001", "RenderCam")
- `<stateset>` — State Set name (e.g., "DayLight", "NightTime")
- `<scene>` — Scene file name without extension (e.g., "myScene")

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

**Delimiter:** Hardcoded as `_` in a single constant (`OUTPUT_FILENAME_DELIMITER` in `data_const.py`). Used for cleanup of double delimiters after token resolution.

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

### 1.3 New utility function (shared, used by both adaptor and UI preview)

**File:** `src/deadline/max_shared/utilities/filename_utils.py` (new file)

```python
def format_output_filename(
    pattern: str,
    camera_name: str = "",
    state_set_name: str = "",
    scene_name: str = "",
    delimiter: str = "_",
) -> str:
    """
    Resolve an output filename from a token pattern.

    Replaces <camera>, <stateset>, and <scene> tokens with actual values,
    then cleans up double delimiters and leading/trailing delimiters
    that result from empty token values.
    """
    ...
```

See Appendix A.1 for full implementation.

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

The group box replaces the old "Output Filename" QLineEdit at Row 2. The Output File Extension dropdown stays at Row 3 (unchanged position). All rows below remain at their current indices.

**Controls:**

| Control | Type | Default | Sticky | Notes |
|---------|------|---------|--------|-------|
| Filename Pattern | `QLineEdit` | (built from render settings, see below) | Yes | Tooltip lists available tokens |
| Filename Preview | `QLabel` | (computed) | No | Read-only, updates live |

**Tooltip for Filename Pattern:**
```
Available tokens:
  <camera>   — Scene camera name (e.g., Camera001, RenderCam)
  <stateset> — State set name
  <scene>    — Scene file name (without extension)

Everything else is literal text.
Remove a token to exclude it from the filename.
Examples:
  <camera>_<stateset>_<scene>_###
  <camera>_<stateset>_myRender_###
  <scene>_###
  myScene_###
```

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

### 2.3 Preview update logic

The preview label updates whenever any of these change:
- `output_filename_pattern_txt` (pattern)
- `state_sets_box` (state set selection)
- `cameras_box` (camera selection)

The preview calls `format_output_filename()` with current UI values. For "All State Sets", the preview uses the first state set name as example. For "All Cameras", the preview uses the first camera name as example. For `<scene>`, the preview uses the current scene name.

### 2.4 `_configure_settings()` additions

```python
def _configure_settings(self, settings):
    ...existing settings...

    self.output_filename_pattern_txt.setText(settings.output_filename_pattern)
    self._update_filename_preview()
```

### 2.5 `update_settings()` additions

```python
def update_settings(self, settings):
    ...existing settings...

    settings.output_filename_pattern = self.output_filename_pattern_txt.text()
```

### 2.6 Removal of old "Output Filename" field

The existing `output_name_txt` QLineEdit and its label are removed from the UI. The `output_name` field on `RenderSubmitterUISettings` is kept for backward compatibility but no longer drives filename composition.

---

## 3. Job Template and Bundle Changes

### 3.1 No changes to `default_max_job_template.yaml`

The template stays as-is. The `OutputFileName` parameter now carries the raw pattern with unresolved tokens.

### 3.2 No changes to `init_data.schema.json`

No new fields. The existing `output_file_name` field carries the raw pattern string.

### 3.3 Changes to `max_render_submitter.py` — pass raw pattern through

**File:** `src/deadline/max_submitter/max_render_submitter.py`

In `on_create_job_bundle_callback()`, the ad-hoc filename logic is replaced in **both** code paths (all state sets and single state set). The raw pattern is passed as `output_file_name` for all cases:

```python
# ALL STATE SETS path — currently does: output_file_name = state_set[0] + "_" + settings.output_name
# SINGLE STATE SET path — currently does: output_file_name = settings.output_name
#
# Both are replaced with:
output_file_name = settings.output_filename_pattern
```

The output directory and extension logic stays the same (from `rendOutputFilename` or UI fields).

---

## 4. Adapter Changes

### 4.1 Changes to `DefaultMaxHandler.start_render()`

**File:** `src/deadline/max_adaptor/MaxClient/render_handlers/default_max_handler.py`

**Breaking change:** The current code appends the camera name with `_` when the camera comes from run-data (`output_name = self.output_name + "_" + camera`). This ad-hoc logic is removed — camera naming is now controlled entirely by the `<camera>` token in the pattern. Users who relied on the old implicit camera-appending behavior will need to include `<camera>` in their pattern.

The adaptor resolves all tokens in `start_render()` before building the output path:

```python
from deadline.max_shared.utilities.filename_utils import format_output_filename

def start_render(self, data: dict) -> None:
    ...existing frame/output validation...

    camera = data.get("camera")
    if camera is not None:
        logger.debug("Setting camera with run data")
        camera = self.get_camera_to_render(camera)
        self.camera_node = rt.getNodeByName(camera)

    ...existing camera_node None check...

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

    ...rest of function unchanged...
```

### 4.2 New instance variable for state set name

The adaptor needs to store the state set name from init-data so it's available in `start_render()`.

**File:** `src/deadline/max_adaptor/MaxClient/render_handlers/default_max_handler.py` — in `__init__()`

```python
class DefaultMaxHandler:
    def __init__(self):
        ...existing action_dict, camera_node, output_dir, etc...

        # NEW: Store state set name for token resolution in start_render()
        self.state_set_name: str = ""
```

**File:** `src/deadline/max_adaptor/MaxClient/render_handlers/default_max_handler.py` — in `set_state_set()`

In `set_state_set()`, store the name before the existing state set switching logic:

```python
def set_state_set(self, data: dict) -> None:
    state_set_name = data.get("state_set")
    self.state_set_name = state_set_name or ""
    ...existing state set logic...
```

### 4.3 No changes to `MaxAdaptor._populate_action_queue()`

No new init-data keys needed. The adaptor already receives `state_set`, `scene_file`, and `camera` — all the data needed to resolve every token.

---

---

## 5. Render Settings Override & Smart Sticky Settings

### 5.1 Focus-change detection (mid-session render settings updates)

**File:** `src/deadline/max_submitter/ui/scene_settings_tab.py`

When the user switches focus back to the submitter dialog after changing `rt.rendOutputFilename` in 3ds Max Render Setup, the submitter detects the change and updates the pattern accordingly.

The `SceneSettingsWidget` tracks `_last_rend_output_filename` and hooks into `QApplication.instance().focusChanged`. On focus change, `on_focus_changed()` compares the current `rt.rendOutputFilename` to the tracked value. If different, it:
1. Extracts the new stem, output path, and extension
2. Rebuilds the pattern as `<camera>_<stateset>_{new_stem}`
3. Updates the pattern field, output path, and extension in the UI
4. Updates `_last_rend_output_filename` to the new value

### 5.2 Smart sticky override on submitter open

**File:** `src/deadline/max_submitter/max_render_submitter.py` — in `show_job_bundle_submitter()`

After `load_sticky_settings()`, the submitter compares the current `rt.rendOutputFilename` to `last_rend_output_filename` (a sticky field). If they differ, the render settings have changed since the last submission, so the pattern is rebuilt from the current render settings — overriding the sticky pattern.

```python
# Only override sticky pattern if render output changed since last save
current_rend_output = str(rt.rendOutputFilename or "")
if current_rend_output and current_rend_output != render_settings.last_rend_output_filename:
    output_path, output_name, output_ext = max_utils.get_render_output_info()
    render_settings.output_path = output_path
    render_settings.output_filename_pattern = f"<camera>_<stateset>_{output_name}"
    if output_ext:
        render_settings.output_ext = output_ext
```

### 5.3 Save tracking on submission

**File:** `src/deadline/max_submitter/max_render_submitter.py` — in `on_create_job_bundle_callback()`

Before `save_sticky_settings()`, the current `rt.rendOutputFilename` is stored into `settings.last_rend_output_filename`. This becomes the baseline for the next smart sticky override check.

```python
settings.last_rend_output_filename = str(rt.rendOutputFilename or "")
settings.save_sticky_settings()
```

### 5.4 New sticky field: `last_rend_output_filename`

**File:** `src/deadline/max_submitter/data_classes.py`

```python
# Tracks rt.rendOutputFilename at last save, used to detect external changes
last_rend_output_filename: str = field(default="", metadata={"sticky": True})
```

---

## 6. Automatic Frame Padding

### 6.1 Submitter-side frame padding adjustment

**File:** `src/deadline/max_shared/utilities/filename_utils.py`

Two utility functions handle automatic frame padding:

- `is_single_frame(frame_range)` — returns `True` if the frame range string has no `-` or `,` (i.e., a single frame like `"5"`)
- `ensure_frame_padding(pattern, frame_range)` — adjusts the pattern based on frame count:
  - Single frame: strips any existing `#` padding and trailing delimiter
  - Multi-frame: appends `_####` if no `#` padding exists

```python
def ensure_frame_padding(pattern: str, frame_range: str) -> str:
    has_padding = "#" in pattern
    if is_single_frame(frame_range):
        if has_padding:
            pattern = pattern.rstrip("#").rstrip(_DELIMITER)
        return pattern
    else:
        if not has_padding:
            return f"{pattern}{_DELIMITER}{_DEFAULT_FRAME_PADDING}"
        return pattern
```

### 6.2 Applied at submission time

**File:** `src/deadline/max_submitter/max_render_submitter.py` — in `on_create_job_bundle_callback()`

After frame override is applied, the submitter loops over all state sets and adjusts `output_file_name`:

```python
# Auto-adjust frame padding: strip for single frame, add for multi-frame
for state_set in state_sets_to_submit:
    state_set.output_file_name = ensure_frame_padding(
        state_set.output_file_name, state_set.frame_range
    )
```

The pattern field in the UI stays untouched — padding adjustment only happens on the submitted data.

### 6.3 Adaptor-side: no frame number appended when no padding

**File:** `src/deadline/max_adaptor/MaxClient/render_handlers/default_max_handler.py`

The `reformat_framenumber_padding()` method was updated: when there are no `#` characters in the filename (because the submitter stripped them for a single-frame render), it returns the name as-is instead of appending the raw frame number.

```python
def reformat_framenumber_padding(self, name: str, number: int) -> str:
    padding_amount = name.count("#")
    # If there are no hashes, the submitter decided no frame numbering is needed
    if not padding_amount:
        return name
    ...
```

This ensures single-frame renders produce clean filenames like `RenderCam_myScene_State01_KIRBY.png` without a trailing `0`.

---

## 7. Integration Test Updates

### 7.1 Multi-camera support in openjd test script

**File:** `scripts/test-3dsmax-openjd-run.ps1`

The integration test script was updated to run all cameras × all frames instead of just the first camera. It:
1. Extracts all cameras from `taskParameterDefinitions` in the template
2. Expands the frame range into individual frame numbers
3. Builds camera × frame task parameter combinations
4. Passes all tasks to `openjd run` via `--tasks file://` JSON

### 7.2 Console output cleanup in both test scripts

**Files:** `scripts/test-3dsmax-openjd-run.ps1`, `scripts/test-3dsmax-adapter-run.ps1`

Updated console output to show cameras, frames, and total task count instead of referencing removed variables.

---

## Files to Modify Summary

| File | Changes |
|------|---------|
| `src/deadline/max_shared/utilities/filename_utils.py` | **New file** — `format_output_filename()`, `ensure_frame_padding()`, `is_single_frame()` utilities |
| `src/deadline/max_submitter/data_classes.py` | Add `output_filename_pattern` and `last_rend_output_filename` sticky fields |
| `src/deadline/max_submitter/data_const.py` | No changes needed |
| `src/deadline/max_submitter/ui/scene_settings_tab.py` | Replace "Output Filename" with "Output Filename Settings" group box (pattern + preview); focus-change detection for render settings updates |
| `src/deadline/max_submitter/max_render_submitter.py` | Build default pattern from render settings; pass raw pattern as `output_file_name`; smart sticky override; frame padding adjustment at submission; save `last_rend_output_filename` |
| `src/deadline/max_adaptor/MaxClient/render_handlers/default_max_handler.py` | Resolve all tokens in `start_render()`, store `state_set_name`, no-padding = no frame number appended |
| `scripts/test-3dsmax-openjd-run.ps1` | Multi-camera × multi-frame task execution |
| `scripts/test-3dsmax-adapter-run.ps1` | Console output cleanup |
| `test/unit/...` | Unit tests for `format_output_filename()`, `ensure_frame_padding()`, `is_single_frame()` |



---

## Appendix: Full Code Implementations

### A.1 `format_output_filename()` — Full Implementation

**File:** `src/deadline/max_shared/utilities/filename_utils.py` (new file)

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Shared output filename utilities for Deadline Cloud 3ds Max integration.

Provides token-based output filename formatting.

Supported tokens:
    <camera>   — Scene camera name (e.g., "Camera001", "RenderCam")
    <stateset> — State Set name (e.g., "DayLight", "NightTime")
    <scene>    — Scene file name without extension (e.g., "myScene")

Everything else in the pattern is literal text (base name, frame padding, delimiters).
"""

# Hardcoded delimiter for cleanup
_DELIMITER = "_"


def format_output_filename(
    pattern: str,
    camera_name: str = "",
    state_set_name: str = "",
    scene_name: str = "",
) -> str:
    """
    Resolve an output filename from a token pattern.

    Replaces <camera>, <stateset>, and <scene> tokens with actual values,
    then cleans up double underscores and leading/trailing underscores
    that result from empty token values.

    Examples:
        >>> format_output_filename(
        ...     "<camera>_<stateset>_<scene>_###",
        ...     camera_name="RenderCam", state_set_name="DayLight", scene_name="myScene")
        'RenderCam_DayLight_myScene_###'

        >>> format_output_filename(
        ...     "<camera>_<stateset>_<scene>_###",
        ...     camera_name="", state_set_name="", scene_name="myScene")
        'myScene_###'

        >>> format_output_filename(
        ...     "<camera>_<stateset>_myRender_###",
        ...     camera_name="RenderCam", state_set_name="DayLight")
        'RenderCam_DayLight_myRender_###'

        >>> format_output_filename("myRender_###")
        'myRender_###'

    :param pattern: the full filename pattern with optional tokens
    :param camera_name: the scene camera name, or "" if not applicable
    :param state_set_name: the state set name, or "" if not applicable
    :param scene_name: the scene file name (no extension), or "" if not applicable
    :returns: the resolved filename string
    """
    if not pattern:
        return ""

    result = pattern
    result = result.replace("<camera>", camera_name)
    result = result.replace("<stateset>", state_set_name)
    result = result.replace("<scene>", scene_name)

    # Collapse runs of the delimiter into a single delimiter
    double = _DELIMITER + _DELIMITER
    while double in result:
        result = result.replace(double, _DELIMITER)

    # Strip leading/trailing delimiters
    result = result.strip(_DELIMITER)

    return result
```

### A.2 `_build_output_filename_settings_ui()` — Full Implementation

**File:** `src/deadline/max_submitter/ui/scene_settings_tab.py`

```python
def _build_output_filename_settings_ui(self):
    """
    Create a QGroupBox for the output filename pattern settings.
    Replaces the old "Output Filename" QLineEdit.
    """
    self.output_filename_grp_box = QGroupBox()
    self.output_filename_grp_box.setTitle("Output Filename Settings")
    fn_lyt = QGridLayout(self)
    self.output_filename_grp_box.setLayout(fn_lyt)

    # Filename Pattern
    self.output_filename_pattern_txt = QLineEdit(self)
    self.output_filename_pattern_txt.setToolTip(
        "Available tokens:\n"
        "  <camera>   — Scene camera name (e.g., Camera001, RenderCam)\n"
        "  <stateset> — State set name\n"
        "  <scene>    — Scene file name (without extension)\n\n"
        "Everything else is literal text.\n"
        "Remove a token to exclude it from the filename.\n"
        "Examples:\n"
        "  <camera>_<stateset>_<scene>_###\n"
        "  <camera>_<stateset>_myRender_###\n"
        "  <scene>_###\n"
        "  myScene_###"
    )
    fn_lyt.addWidget(QLabel("Filename Pattern"), 0, 0)
    fn_lyt.addWidget(self.output_filename_pattern_txt, 0, 1)
    self.output_filename_pattern_txt.textChanged.connect(self._update_filename_preview)

    # Filename Preview
    self.filename_preview_label = QLabel(self)
    self.filename_preview_label.setStyleSheet("color: gray; font-style: italic;")
    self.filename_preview_label.setToolTip("Preview of the resolved output filename")
    fn_lyt.addWidget(QLabel("Filename Preview"), 1, 0)
    fn_lyt.addWidget(self.filename_preview_label, 1, 1)
```

### A.3 `_update_filename_preview()` — Full Implementation

**File:** `src/deadline/max_submitter/ui/scene_settings_tab.py`

```python
def _update_filename_preview(self):
    """
    Update the filename preview label based on current UI values.
    """
    from deadline.max_shared.utilities.filename_utils import format_output_filename
    from data_const import ALL_CAMERAS_STR, ALL_STEREO_CAMERAS_STR

    pattern = self.output_filename_pattern_txt.text()

    # Get state set name from current selection
    state_set_text = self.state_sets_box.currentText()
    state_set_name = "" if state_set_text == "All State Sets" else state_set_text

    # For "All State Sets", show first state set as example if available
    if state_set_text == "All State Sets" and self.state_sets:
        state_set_name = self.state_sets[0][0]

    # Get camera name from current selection
    camera_data = self.cameras_box.currentData()
    is_all_cameras = camera_data in (ALL_CAMERAS_STR, ALL_STEREO_CAMERAS_STR)

    if is_all_cameras and hasattr(self, "cameras") and self.cameras:
        camera_name = self.cameras[0]
    elif not is_all_cameras and camera_data:
        camera_name = camera_data
    else:
        camera_name = ""

    # Get scene name
    scene_name = max_utils.get_scene_name()

    preview = format_output_filename(
        pattern=pattern,
        camera_name=camera_name,
        state_set_name=state_set_name,
        scene_name=scene_name,
    )

    self.filename_preview_label.setText(preview)
```
