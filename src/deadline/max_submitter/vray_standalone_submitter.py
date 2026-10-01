# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - V-Ray Standalone Workflow
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import pymxs  # noqa
import qtmax
from deadline.client.dataclasses import SubmitterInfo
from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.ui.dialogs._types import JobBundlePurpose
from deadline.max_shared.utilities.max_utils import get_max_version_year
from pymxs import runtime as rt
from qtpy.QtCore import Qt  # type: ignore
from ui.submit_dialog import SubmitMaxJobToDeadlineDialog
from ui.vray_standalone_tab import VRayStandaloneSettingsWidget
from utilities import max_utils
from utilities.vrscene_job_submission import (
    _inject_embedded_script,
    _load_job_template,
    create_tile_rendering_job_template,
    create_vrscene_render_job_parameters,
    get_frame_range_from_string,
)
from utilities.vrscene_utils import (
    export_vrscene_local,
    get_output_format_from_scene,
    get_vrscene_filename,
    normalize_output_format,
    validate_vrscene_export_settings,
)
from utilities.vray_executable_utils import (
    get_vray_executable_path,
    get_3dsmax_executable_path,
)
from vrscene_settings import VRSceneRenderSubmitterUISettings

from _version import version

_logger = logging.getLogger(__name__)


def _get_fix_vrscene_paths_script() -> str:
    """
    Reads the fix_vrscene_paths.py script from the scripts directory.
    This script exports vrscene via 3dsmaxcmd, then reverses
    session-specific paths back to originals so render -remapPath works.
    """
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "fix_vrscene_paths.py")
    with open(script_path, "r") as f:
        return f.read()


def _get_path_mapping_script() -> str:
    """
    Reads the path_mapping_render.py script from the scripts directory.
    This script reads path mapping rules and executes V-Ray with -remapPath arguments.
    """
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "path_mapping_render.py")
    with open(script_path, "r") as f:
        return f.read()


def on_create_vrscene_job_bundle_callback(
    widget: SubmitMaxJobToDeadlineDialog,
    job_bundle_dir: str,
    settings: VRSceneRenderSubmitterUISettings,
    queue_parameters: list[dict[str, Any]],
    asset_references: AssetReferences,
    host_requirements: Optional[dict[str, Any]] = None,
    purpose: JobBundlePurpose = JobBundlePurpose.SUBMISSION,
) -> None:
    """Callback for creating V-Ray Standalone job bundle (local or farm export)."""
    _logger.debug("Start on_create_vrscene_job_bundle_callback")

    # Validate settings
    validation_errors = validate_vrscene_export_settings(settings)
    if validation_errors:
        error_msg = "Validation failed:\n" + "\n".join(validation_errors)
        _logger.error(error_msg)
        raise ValueError(error_msg)

    # Get frame range
    start_frame, end_frame = get_frame_range_from_string(settings.frame_list)

    # Generate vrscene filename
    scene_name = max_utils.get_scene_name()
    vrscene_path = get_vrscene_filename(scene_name, settings.output_path)

    job_bundle_path = Path(job_bundle_dir)

    if settings.export_mode == 1:
        # ===== LOCAL EXPORT MODE =====
        _logger.info("Exporting vrscene locally...")

        success, message = export_vrscene_local(
            vrscene_path,
            start_frame,
            end_frame,
            settings.export_animation_mode,
        )

        if not success:
            raise RuntimeError(f"Failed to export vrscene: {message}")

        _logger.info(f"Successfully exported vrscene to: {message}")

        # Add vrscene file(s) to asset references
        if settings.export_animation_mode == 1:
            # Single file
            asset_references.input_filenames.add(vrscene_path)
        elif settings.export_animation_mode == 2:
            # File per frame - add all frame files
            dir_path = os.path.dirname(vrscene_path)
            base_name = os.path.splitext(os.path.basename(vrscene_path))[0]
            for frame in range(start_frame, end_frame + 1):
                frame_file = os.path.join(dir_path, f"{base_name}.{frame:04d}.vrscene")
                if os.path.exists(frame_file):
                    asset_references.input_filenames.add(frame_file)
        else:
            # Incremental - add master file and all frame files
            asset_references.input_filenames.add(vrscene_path)
            dir_path = os.path.dirname(vrscene_path)
            base_name = os.path.splitext(os.path.basename(vrscene_path))[0]
            for frame in range(start_frame, end_frame + 1):
                frame_file = os.path.join(dir_path, f"{base_name}.{frame:04d}.vrscene")
                if os.path.exists(frame_file):
                    asset_references.input_filenames.add(frame_file)

        # Create render job bundle using vrscene template
        _create_vrscene_render_job_bundle(
            job_bundle_path,
            settings,
            vrscene_path,
            start_frame,
            end_frame,
            queue_parameters,
            asset_references,
        )

    else:
        # ===== FARM EXPORT MODE =====
        _logger.info("Creating combined export and render job bundle...")

        # Create a single job bundle with both export and render steps
        _create_combined_export_render_job_bundle(
            job_bundle_path,
            settings,
            vrscene_path,
            start_frame,
            end_frame,
            queue_parameters,
            asset_references,
        )

    # Save sticky settings
    settings.save_sticky_settings()


def _get_export_maxscript(settings, start_frame: int, end_frame: int) -> str:
    """Read the farm export MAXScript template and fill in runtime values."""
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "export_vrscene_farm.ms")
    with open(script_path, "r") as f:
        template = f.read()
    return template.format(
        export_animation_mode=settings.export_animation_mode,
        start_frame=start_frame,
        end_frame=end_frame,
    )


def _create_combined_export_render_job_bundle(
    job_bundle_path: Path,
    settings: VRSceneRenderSubmitterUISettings,
    vrscene_path: str,
    start_frame: int,
    end_frame: int,
    queue_parameters: list[dict[str, Any]],
    asset_references: AssetReferences,
) -> None:
    """
    Create job bundle with export + render steps (farm mode).
    When tile rendering is enabled, adds RenderRegions/MergeRegions steps.
    """
    _logger.info("Creating combined export and render job bundle...")

    max_executable = get_3dsmax_executable_path()
    vray_executable = get_vray_executable_path()
    _logger.info(f"Using 3ds Max executable: {max_executable}")
    _logger.info(f"Using V-Ray executable: {vray_executable}")

    # Determine frame range string
    if start_frame == end_frame:
        frames = str(start_frame)
    else:
        frames = f"{start_frame}-{end_frame}"

    output_filename = _determine_output_filename(settings, vrscene_path)
    _logger.info(f"Output filename: {output_filename}")

    tile_rendering = _is_tile_rendering_enabled(settings)
    if tile_rendering:
        _logger.info(
            f"Tile rendering enabled: {settings.vrscene_render_region_columns}x"
            f"{settings.vrscene_render_region_rows}"
        )

    # Load base template (parameter definitions)
    job_template = _load_job_template("vray_combined_job_template.yaml")
    job_template["name"] = f"{settings.name} - VRay Export and Render"

    # Set dynamic parameter defaults
    defaults = {
        "Frames": frames,
        "ExportAnimationMode": str(settings.export_animation_mode),
        "OutputFileName": output_filename,
        "RegionColumns": str(settings.vrscene_render_region_columns),
        "RegionRows": str(settings.vrscene_render_region_rows),
    }
    for param in job_template.get("parameterDefinitions", []):
        if param["name"] in defaults:
            param["default"] = defaults[param["name"]]

    # Build the export step (dynamic MAXScript content)
    export_step = {
        "name": "ExportVRScene",
        "parameterSpace": {
            "taskParameterDefinitions": [
                {
                    "name": "Frame",
                    "type": "INT",
                    "range": "{{Param.Frames}}",
                }
            ]
        },
        "script": {
            "embeddedFiles": [
                {
                    "name": "ExportScript",
                    "type": "TEXT",
                    "filename": "export_vrscene.ms",
                    "data": _get_export_maxscript(settings, start_frame, end_frame),
                },
                {
                    "name": "FixVRScenePaths",
                    "type": "TEXT",
                    "filename": "fix_vrscene_paths.py",
                    "data": _get_fix_vrscene_paths_script(),
                },
            ],
            "actions": {
                "onRun": {
                    "command": "python",
                    "args": ["{{Task.File.FixVRScenePaths}}"],
                },
            },
        },
    }

    # Build parameter values
    parameter_values = [
        {"name": "MaxCmdExecutable", "value": max_executable},
        {"name": "VRayExecutable", "value": vray_executable},
        {"name": "SceneFile", "value": settings.scene_file},
        {"name": "VRSceneOutputPath", "value": vrscene_path},
        {"name": "OutputDir", "value": settings.output_path},
        {"name": "Frames", "value": frames},
        {"name": "ExportAnimationMode", "value": str(settings.export_animation_mode)},
        {"name": "OutputFileName", "value": output_filename},
        {"name": "RegionColumns", "value": str(settings.vrscene_render_region_columns)},
        {"name": "RegionRows", "value": str(settings.vrscene_render_region_rows)},
        {"name": "RenderEngine", "value": str(settings.vrscene_render_engine)},
        {"name": "RTTimeout", "value": str(settings.vrscene_rt_timeout)},
        {"name": "RTNoise", "value": str(settings.vrscene_rt_noise)},
        {"name": "RTSampleLevel", "value": str(settings.vrscene_rt_sample_level)},
    ]

    if tile_rendering:
        # Add tile rendering parameters
        tile_params = [
            {"name": "ImageWidth", "type": "INT", "default": str(settings.image_width)},
            {"name": "ImageHeight", "type": "INT", "default": str(settings.image_height)},
            {
                "name": "CreateMovie",
                "type": "STRING",
                "default": "true" if settings.vrscene_create_movie else "false",
                "allowedValues": ["true", "false"],
            },
            {"name": "MovieFilename", "type": "STRING", "default": settings.vrscene_movie_filename},
            {
                "name": "FrameRate",
                "type": "INT",
                "default": str(settings.vrscene_movie_framerate),
            },
        ]
        job_template["parameterDefinitions"].extend(tile_params)

        parameter_values.extend(
            [
                {"name": "ImageWidth", "value": str(settings.image_width)},
                {"name": "ImageHeight", "value": str(settings.image_height)},
                {
                    "name": "CreateMovie",
                    "value": "true" if settings.vrscene_create_movie else "false",
                },
                {"name": "MovieFilename", "value": settings.vrscene_movie_filename},
                {"name": "FrameRate", "value": str(settings.vrscene_movie_framerate)},
            ]
        )

        # Get tile rendering steps from the tile template
        tile_template = create_tile_rendering_job_template(
            settings, vrscene_path, output_filename, start_frame, end_frame
        )
        tile_steps = tile_template["steps"]
        tile_steps[0]["dependencies"] = [{"dependsOn": "ExportVRScene"}]

        job_template["steps"] = [export_step] + tile_steps
    else:
        # Load render step from the render template
        render_template = _load_job_template("vray_render_job_template.yaml")
        _inject_embedded_script(
            render_template, "INJECT_PATH_MAPPING_SCRIPT", _get_path_mapping_script()
        )
        render_step = render_template["steps"][0]
        render_step["dependencies"] = [{"dependsOn": "ExportVRScene"}]

        job_template["steps"] = [export_step, render_step]

    # Add queue parameters
    parameter_values.extend(queue_parameters)

    # Write template
    with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(job_template, f, indent=1)

    # Write parameter values
    with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump({"parameterValues": parameter_values}, f, indent=1)

    # Write asset references
    with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

    _logger.info(f"Combined export and render job bundle created at: {job_bundle_path}")


def _determine_output_filename(
    settings: VRSceneRenderSubmitterUISettings, vrscene_path: str
) -> str:
    """Determine output filename from user override or auto-detect + format."""
    if settings.output_filename_override and settings.output_filename_override.strip():
        return settings.output_filename_override.strip()

    # Determine format: use configured format or auto-detect
    if settings.output_format and settings.output_format.lower() != "auto":
        fmt = normalize_output_format(settings.output_format)
    else:
        fmt = get_output_format_from_scene()

    if not fmt:
        fmt = "png"

    vrscene_name = Path(vrscene_path).stem
    return f"{vrscene_name}.{fmt}"


def _is_tile_rendering_enabled(settings: VRSceneRenderSubmitterUISettings) -> bool:
    """Check if tile rendering is enabled (more than 1 column or 1 row)."""
    return settings.vrscene_render_region_columns > 1 or settings.vrscene_render_region_rows > 1


def _create_vrscene_render_job_bundle(
    job_bundle_path: Path,
    settings: VRSceneRenderSubmitterUISettings,
    vrscene_path: str,
    start_frame: int,
    end_frame: int,
    queue_parameters: list[dict[str, Any]],
    asset_references: AssetReferences,
    export_job_dependency: bool = False,
) -> None:
    """
    Create job bundle for vrscene render job (local export mode).
    Uses tile rendering template when columns > 1 or rows > 1.
    """
    _logger.info("Creating vrscene render job bundle...")

    vray_executable = get_vray_executable_path()
    _logger.info(f"Using V-Ray executable: {vray_executable}")

    output_filename = _determine_output_filename(settings, vrscene_path)
    _logger.info(f"Output filename: {output_filename}")

    if _is_tile_rendering_enabled(settings):
        # Tile rendering: use the multi-step tile template
        _logger.info(
            f"Tile rendering enabled: {settings.vrscene_render_region_columns}x"
            f"{settings.vrscene_render_region_rows}"
        )
        job_template = create_tile_rendering_job_template(
            settings,
            vrscene_path,
            output_filename,
            start_frame,
            end_frame,
        )

        # Build parameter values for tile rendering
        if start_frame == end_frame:
            frames = str(start_frame)
        else:
            frames = f"{start_frame}-{end_frame}"

        parameter_values = [
            {"name": "VRayExecutable", "value": vray_executable},
            {"name": "VRSceneOutputPath", "value": vrscene_path},
            {"name": "OutputDir", "value": settings.output_path},
            {"name": "OutputFileName", "value": output_filename},
            {"name": "Frames", "value": frames},
            {"name": "ImageWidth", "value": str(settings.image_width)},
            {"name": "ImageHeight", "value": str(settings.image_height)},
            {"name": "RegionColumns", "value": str(settings.vrscene_render_region_columns)},
            {"name": "RegionRows", "value": str(settings.vrscene_render_region_rows)},
            {"name": "RenderEngine", "value": str(settings.vrscene_render_engine)},
            {"name": "RTTimeout", "value": str(settings.vrscene_rt_timeout)},
            {"name": "RTNoise", "value": str(settings.vrscene_rt_noise)},
            {"name": "RTSampleLevel", "value": str(settings.vrscene_rt_sample_level)},
            {"name": "CreateMovie", "value": "true" if settings.vrscene_create_movie else "false"},
            {"name": "MovieFilename", "value": settings.vrscene_movie_filename},
            {"name": "FrameRate", "value": str(settings.vrscene_movie_framerate)},
        ]
    else:
        # Standard single-step render (no tiling) — load from YAML template
        job_template = _load_job_template("vray_render_job_template.yaml")
        job_template["name"] = f"{settings.name} - VRay Standalone Render"
        _inject_embedded_script(
            job_template, "INJECT_PATH_MAPPING_SCRIPT", _get_path_mapping_script()
        )

        parameter_values = create_vrscene_render_job_parameters(
            settings,
            vrscene_path,
            settings.output_path,
            output_filename,
            start_frame,
            end_frame,
            vray_executable,
        )

    # Add queue parameters
    parameter_values.extend(queue_parameters)

    # Write template
    with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(job_template, f, indent=1)

    # Write parameter values
    with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump({"parameterValues": parameter_values}, f, indent=1)

    # Write asset references
    with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

    _logger.info(f"Render job bundle created at: {job_bundle_path}")


def show_vray_standalone_submitter():
    """Show the V-Ray Standalone submitter UI."""
    _logger.info("Opening Deadline Cloud V-Ray Standalone Submitter interface")

    # Get main max window
    main_window = qtmax.GetQMaxMainWindow()

    # Create settings
    vrscene_settings = VRSceneRenderSubmitterUISettings()

    # Set settings dependent on scene
    vrscene_settings.name = max_utils.get_scene_name()
    vrscene_settings.frame_list = max_utils.get_frames()
    vrscene_settings.scene_file = rt.maxFilePath + rt.maxFileName
    vrscene_settings.output_path = max_utils.get_scene_dir()
    vrscene_settings.vrscene_filename = max_utils.get_scene_name()

    # Get image resolution for tile coordinate calculation
    vrscene_settings.image_width = rt.renderWidth
    vrscene_settings.image_height = rt.renderHeight

    # Read RT settings from V-Ray render settings if available.
    # V-Ray CPU uses V_Ray_settings.progressive_* properties.
    # V-Ray GPU uses renderers.current.max_render_time and max_paths_per_pixel directly.
    try:
        renderer = rt.renderers.current
        renderer_class = str(rt.classof(renderer))
        if "GPU" in renderer_class:
            vrscene_settings.vrscene_rt_timeout = float(renderer.max_render_time)
            vrscene_settings.vrscene_rt_sample_level = int(renderer.max_paths_per_pixel)
            # GPU noise threshold not directly exposed — keep default
        else:
            vray_settings = renderer.V_Ray_settings
            vrscene_settings.vrscene_rt_noise = float(vray_settings.progressive_noise_threshold)
            vrscene_settings.vrscene_rt_timeout = float(vray_settings.progressive_max_render_time)
            vrscene_settings.vrscene_rt_sample_level = int(vray_settings.progressive_maxSamples)
    except Exception as e:
        _logger.debug(f"Could not read RT settings from scene, using defaults: {e}")

    # Load sticky settings
    vrscene_settings.load_sticky_settings()

    # Set output directories
    output_directories: set[str] = {vrscene_settings.output_path}
    vrscene_settings.output_directories = list(output_directories)

    # Fill in auto-detected input files
    auto_detected_attachments = AssetReferences()
    relative_dir_base = rt.maxFilePath
    input_files: set[str] = {
        os.path.abspath(os.path.normpath(os.path.join(relative_dir_base, path)))
        for path in max_utils.get_referenced_files()
    }
    auto_detected_attachments.input_filenames = input_files

    attachments = AssetReferences(
        input_filenames=set(vrscene_settings.input_filenames),
        input_directories=set(vrscene_settings.input_directories),
        output_directories=set(vrscene_settings.output_directories),
    )

    # For V-Ray Standalone, we need vray package instead of 3dsmax
    conda_packages = "vray imagemagick ffmpeg"

    max_version = get_max_version_year()
    submitter_info = SubmitterInfo(
        submitter_name="VRayStandalone",
        submitter_package_name="deadline-cloud-for-3ds-max",
        submitter_package_version=version,
        host_application_name="3ds Max",
        host_application_version=str(max_version),
    )

    # Instantiate and show the Submitter UI
    window = SubmitMaxJobToDeadlineDialog(
        job_setup_widget_type=VRayStandaloneSettingsWidget,
        initial_job_settings=vrscene_settings,
        initial_shared_parameter_values={
            "CondaPackages": conda_packages,
        },
        auto_detected_attachments=auto_detected_attachments,
        attachments=attachments,
        on_create_job_bundle_callback=on_create_vrscene_job_bundle_callback,
        parent=main_window,
        f=Qt.Tool,
        show_host_requirements_tab=False,  # Not needed for vrscene rendering
        submitter_info=submitter_info,
    )
    window.show()
    return window
