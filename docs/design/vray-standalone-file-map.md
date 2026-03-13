# V-Ray Standalone Submitter — File Map

Overview of all files added for the V-Ray Standalone workflow.

```
src/deadline/max_submitter/
├── vray_standalone_submitter.py        — Main submitter logic: job bundle creation for
│                                         local export and farm export modes, path mapping
│                                         script loading, vrscene path fix script loading,
│                                         tile rendering integration
├── vrscene_settings.py                 — Settings dataclass with sticky persistence (export
│                                         mode, region grid, output format, movie settings)
├── ui/
│   └── vray_standalone_tab.py          — Qt UI tab: export mode radios, job options, region
│                                         grid spinners, output format dropdown, browse button
├── utilities/
│   ├── vrscene_job_submission.py       — Job template loading and parameter builders:
│   │                                     tile coordinate calculation, script injection,
│   │                                     parameter value builders for all job types
│   ├── vrscene_utils.py                — V-Ray helpers: renderer detection, vrscene export
│   │                                     (local), settings validation, output format detection
│   └── vray_executable_utils.py        — Executable path resolution for vray.exe and
│                                         3dsmaxcmd.exe (env vars + install path fallback)
├── scripts/
│   ├── fix_vrscene_paths.py            — Farm script: runs 3dsmaxcmd export then reverses
│   │                                     session paths so render -remapPath works correctly
│   ├── path_mapping_render.py          — Farm script: reads path mapping rules and calls
│   │                                     vray.exe with -remapPath arguments
│   ├── tile_render.py                  — Farm script: renders a single tile region with vray.exe
│   ├── tile_merge.py                   — Farm script: merges tile images into complete frames
│   │                                     using Pillow (PNG/JPEG/TIFF) or OpenEXR
│   ├── create_movie.py                 — Farm script: creates MP4 from frames (future release)
│   └── export_vrscene_farm.ms          — MAXScript: exports vrscene on the farm worker via
│                                         3dsmaxcmd, called by fix_vrscene_paths.py
└── job_templates/
    ├── vray_render_job_template.yaml   — OpenJD template: single-step vray.exe render
    ├── vray_export_job_template.yaml   — OpenJD template: vrscene export step (farm mode)
    ├── vray_tile_render_job_template.yaml — OpenJD template: RenderRegions + MergeRegions steps
    └── vray_combined_job_template.yaml — OpenJD template: export + render combined (farm mode)

install_files/
└── AWSDeadline-SubmitToDeadlineCloud-VRayStandalone.mcr  — 3ds Max macro for menu entry
                                                             (installer bundling: follow-up PR)

force_reload.ms                         — Dev helper: reloads Python modules in 3ds Max
```

## Architecture Integration

How the V-Ray Standalone feature relates to the existing submitter/adaptor architecture.

### Existing Architecture Flow

```
run_ui.py
  → show_job_bundle_submitter()
    → SubmitMaxJobToDeadlineDialog(
        job_setup_widget_type = SceneSettingsWidget,
        on_create_job_bundle_callback = on_create_job_bundle_callback
      )
```

The existing callback builds an OpenJD job template that uses the `3dsmax-openjd` adaptor.
The farm worker launches 3ds Max and renders inside it.

### V-Ray Hook Points

The V-Ray feature hooks into the existing architecture at exactly two points:

1. **`submit_dialog.py`** — `SubmitMaxJobToDeadlineDialog.__init__()` intercepts the original
   callback, wraps it in `_on_create_job_bundle_wrapper()`, and calls
   `_add_vray_export_tab_if_available()`. When V-Ray is the active renderer, a "V-Ray Export"
   tab appears in the dialog.

2. **Submit-time routing** — The wrapper checks `vray_export_widget.is_vray_export_enabled()`:
   - Enabled → routes to `on_create_vrscene_job_bundle_callback` with `VRSceneRenderSubmitterUISettings`
   - Disabled → passes through to the original `on_create_job_bundle_callback` with `RenderSubmitterUISettings`

No other existing files are modified (except `data_const.py` for the settings file extension constant).

### Adaptor vs Adaptor-Free

| | Existing 3ds Max Workflow | V-Ray Standalone Workflow |
|---|---|---|
| Rendering | `3dsmax-openjd` adaptor launches 3ds Max on the farm | Farm scripts call `vray.exe` directly |
| Job template | Loaded from `default_max_job_template.yaml` | Loaded from YAML files in `job_templates/` |
| Path mapping | Handled by the adaptor | `path_mapping_render.py` reads `Session.PathMappingRulesFile` |
| Settings class | `RenderSubmitterUISettings` | `VRSceneRenderSubmitterUISettings` |
| UI tab | `SceneSettingsWidget` | `VRayStandaloneSettingsWidget` |
| Sticky settings ext | `.deadline_render_settings.json` | `.deadline_vrscene_settings.json` |

### Executable Path Resolution

Farm workers need `vray.exe` (Windows) on the `PATH` or via environment variable.
Set `VRAY_EXECUTABLE` to the full path of `vray.exe` on each worker — this is the recommended
approach and should be configured in the fleet host configuration or worker environment.
The fallback derives the path from `VRAY_FOR_3DSMAX{version}_MAIN` (set by the V-Ray installer).

Similarly, farm export mode requires `3dsmaxcmd.exe`. Set `MAXCMD_EXECUTABLE` to its full path,
or the submitter will derive it from the current 3ds Max installation at submit time.

### Coupling Summary

The V-Ray feature is a parallel workflow that shares the dialog shell but has its own:
- Settings dataclass (`vrscene_settings.py`)
- UI tab (`vray_standalone_tab.py`)
- Submit callback (`vray_standalone_submitter.py`)
- Job templates (`job_templates/`)
- Farm scripts (`scripts/`)

Everything is additive. The only modified existing files are `submit_dialog.py` (callback wrapper + tab injection) and `data_const.py` (one constant).
