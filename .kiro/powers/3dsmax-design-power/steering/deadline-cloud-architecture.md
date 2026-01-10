---
inclusion: manual
---

# Deadline Cloud for 3ds Max Architecture Guide

This guide explains the architecture of the Deadline Cloud for 3ds Max integration to help with design decisions.

## High-Level Architecture

```
+------------------------------------------------------------------+
|                        3ds Max (Artist Workstation)              |
|  +------------------------------------------------------------+  |
|  |                    Submitter Dialog                        |  |
|  |  - Collects job settings from user                         |  |
|  |  - Reads scene information                                 |  |
|  |  - Creates job bundle                                      |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
                              | Job Bundle (YAML + assets)
                              v
+------------------------------------------------------------------+
|                      AWS Deadline Cloud                          |
|  - Schedules jobs                                                |
|  - Distributes tasks to workers                                  |
|  - Manages job queues                                            |
+------------------------------------------------------------------+
                              |
                              | Task assignment
                              v
+------------------------------------------------------------------+
|                    Worker (Render Node)                          |
|  +------------------------------------------------------------+  |
|  |                   Adaptor Server                           |  |
|  |  - Receives tasks from Deadline Cloud                      |  |
|  |  - Manages 3ds Max process lifecycle                       |  |
|  |  - Sends actions to MaxClient                              |  |
|  +------------------------------------------------------------+  |
|                              |                                   |
|                              | Actions (JSON)                    |
|                              v                                   |
|  +------------------------------------------------------------+  |
|  |                      MaxClient                             |  |
|  |  - Runs inside 3ds Max process                             |  |
|  |  - Executes actions via render handlers                    |  |
|  |  - Uses pymxs to control 3ds Max                           |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## Component Details

### 1. Submitter (`src/deadline/max_submitter/`)

The submitter runs inside 3ds Max on the artist's workstation.

**Key Files:**
- `ui/` - Dialog UI components
- `job_bundle/` - Job template and bundle creation
- `scene_utils.py` - Scene analysis utilities

**Responsibilities:**
- Display job submission dialog
- Collect user settings
- Analyze scene (cameras, renderers, frame range)
- Create job bundle with template and assets
- Submit to Deadline Cloud

### 2. Job Bundle

The job bundle is a directory containing:
- `template.yaml` - Job template with parameters and steps
- `parameter_values.yaml` - User-provided parameter values
- Asset references (scene file, textures, etc.)

**Template Structure:**
```yaml
specificationVersion: jobtemplate-2023-09
name: "3ds Max Render"
parameterDefinitions:
  - name: MaxSceneFile
    type: PATH
    objectType: FILE
  - name: Frames
    type: STRING
  # ... more parameters

steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - name: Frame
          type: INT
          range: "{{Param.Frames}}"
    script:
      actions:
        onRun:
          command: "{{Task.Attachment.runScript.Path}}"
```

### 3. Adaptor Server (`src/deadline/max_adaptor/`)

The adaptor server runs on the worker node and manages the 3ds Max process.

**Key Files:**
- `MaxAdaptor/adaptor.py` - Main adaptor class
- `MaxAdaptor/` - Server-side logic

**Responsibilities:**
- Start/stop 3ds Max process
- Send initialization actions (scene file, renderer, etc.)
- Send per-task actions (frame number, output path)
- Handle errors and logging

### 4. MaxClient (`src/deadline/max_adaptor/MaxClient/`)

The MaxClient runs inside the 3ds Max process and executes actions.

**Key Files:**
- `max_client.py` - Main client class
- `render_handlers/` - Renderer-specific handlers
  - `default_max_handler.py` - Base handler
  - `vray_handler.py` - V-Ray specific
  - `arnold_handler.py` - Arnold specific

**Responsibilities:**
- Receive actions from adaptor server
- Route actions to appropriate handler
- Execute pymxs commands
- Report progress and errors

### 5. Shared Utilities (`src/deadline/max_shared/`)

Shared code used by both submitter and adaptor.

**Key Files:**
- `utilities/max_utils.py` - Common 3ds Max utilities
- `utilities/vray_utils.py` - V-Ray specific utilities

## Data Flow: Submitter to Render

### 1. Job Submission

```
User fills dialog -> Submitter creates bundle -> Submit to Deadline Cloud
                         |
                         +-- template.yaml (job definition)
                         +-- parameter_values.yaml (user settings)
                         +-- asset references
```

### 2. Task Execution

```
Deadline Cloud assigns task to worker
         |
         v
Adaptor Server receives task
         |
         +-- Init actions (once per job):
         |   +-- scene_file: Load the .max file
         |   +-- renderer: Set up render handler
         |   +-- state_set: Configure state sets
         |   +-- camera: Set camera (if single camera)
         |
         +-- Run actions (per frame):
             +-- frame: Set frame number
             +-- output_file_path: Set output directory
             +-- output_file_name: Set output filename
             +-- camera: Set camera (if per-task)
             +-- start_render: Execute render
```

### 3. Action Execution in MaxClient

```
MaxClient receives action
         |
         v
Route to handler method
         |
         v
Execute pymxs commands
         |
         v
Report result to adaptor
```

## Adding a New Feature

### Step 1: Submitter Changes

1. Add UI controls to collect user input
2. Add parameters to job template
3. Write parameter values to bundle

### Step 2: Adaptor Changes

1. Read parameters from job bundle
2. Create actions to send to MaxClient
3. Add to init_data or run_data as appropriate

### Step 3: MaxClient Changes

1. Add handler method for new action
2. Register action in handler's action_dict
3. Implement pymxs logic

### Step 4: Shared Utilities (if needed)

1. Add utility functions used by both submitter and adaptor
2. Keep renderer-specific code in appropriate modules

## Action Types

### Init Actions (once per job)

| Action | Handler Method | Purpose |
|--------|---------------|---------|
| `scene_file` | `set_scene_file()` | Load .max scene |
| `renderer` | `set_renderer()` | Initialize render handler |
| `state_set` | `set_state_set()` | Configure state sets |
| `camera` | `set_camera()` | Set camera (single) |
| `output_file_path` | `set_output_file_path()` | Set output directory |
| `output_file_name` | `set_output_file_name()` | Set output filename |
| `output_file_format` | `set_output_file_format()` | Set output format |

### Run Actions (per task/frame)

| Action | Handler Method | Purpose |
|--------|---------------|---------|
| `frame` | `set_frame()` | Set frame to render |
| `camera` | `set_camera()` | Set camera (per-task) |
| `start_render` | `start_render()` | Execute render |

## Path Mapping

Assets may be at different paths on worker vs. artist workstation.

**OpenJD provides:**
- `ClientInterface.map_path(path)` - Map a single path
- `ClientInterface.path_mapping_rules()` - Get mapping rules

**Usage in handlers:**
```python
# In handler (map_path injected by MaxClient)
if self.map_path:
    mapped_path = self.map_path(original_path)
```

## Error Handling

1. **Submitter**: Validate inputs before submission
2. **Adaptor**: Catch and report errors to Deadline Cloud
3. **MaxClient**: Log errors and raise exceptions
4. **Handlers**: Use try/except and return warnings list

## Testing Strategy

1. **Unit tests**: Mock pymxs, test handler logic
2. **Integration tests**: Test with real 3ds Max (manual)
3. **Job bundle tests**: Validate generated YAML

Test files location: `test/unit/`

## External References

- [GitHub Discussion #163 - Render Elements Design Document](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/discussions/163) - Comprehensive design example with full data flow
- [GitHub Discussion #164 - MAXScript and pymxs Integration](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/discussions/164) - Understanding pymxs API bindings
- [OpenJD Sessions for Python](https://github.com/OpenJobDescription/openjd-sessions-for-python) - Core library for running Jobs in Sessions

## OpenJD Sessions Overview

The `openjd-sessions-for-python` library provides the runtime for executing Jobs defined by Open Job Description. Key concepts:

### Session Lifecycle
```python
from openjd.sessions import Session, ActionStatus, ActionState

with Session(
    session_id="demo",
    job_parameter_values=job_parameters,
    callback=action_complete_callback
) as session:
    # Enter environments (job → step)
    session.enter_environment(environment=env)
    
    # Run tasks
    session.run_task(
        step_script=step.script,
        task_parameter_values=task_parameters
    )
    
    # Exit environments (reverse order)
    session.exit_environment(identifier=env_id)
```

### Action States
- `ActionState.RUNNING` - Action in progress
- `ActionState.SUCCEEDED` - Action completed successfully
- `ActionState.FAILED` - Action failed
- `ActionState.CANCELED` - Action was canceled

### Parameter Flow
```
Job Template → decode_job_template() → preprocess_job_parameters()
    → create_job() → Session → run_task(task_parameter_values)
```

For deep code analysis, clone the repository:
```bash
git clone https://github.com/OpenJobDescription/openjd-sessions-for-python /context/openjd-sessions
```

## Design Document Example: Render Elements

The Render Elements implementation (Discussion #163) demonstrates the complete design pattern:

### Three-Tier Architecture
1. **Submitter**: UI widget + data class properties
2. **Shared Utilities**: pymxs operations for detection/validation/configuration
3. **Adaptor**: Manager class + handler integration

### Parameter Flow
```
UI Settings → RenderSubmitterUISettings → Job Template Parameters
    → OpenJD Parameter Values → Adaptor init_data → RenderElementManager
    → pymxs Operations
```

### Key Components
- `RenderElementsWidget` - Authentic Deadline 10 UI
- `RenderSubmitterUISettings` - 8 new properties for configuration
- `RenderElementManager` - Comprehensive pymxs operations
- `DefaultMaxHandler` - Automatic workflow integration

### Parameter Naming Convention
```python
# OpenJD (PascalCase) → Adaptor (snake_case)
param_mapping = {
    "RenderElements": "render_elements",
    "VRayRenderElementsVFBControl": "vray_render_elements_vfb_control",
    "IgnoreRenderElementsByName": "ignore_render_elements_by_name",
}
```