# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Functions for generating the job template and parameter values files
"""

import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from qtpy.QtCore import Qt  # type: ignore
from qtpy.QtWidgets import QApplication, QProgressDialog  # type: ignore

from data_classes import (
    RENDER_ELEMENT_PARAMS,
    RENDER_ELEMENT_PARAM_MAPPING,
    BatchRenderView,
    RenderSubmitterUISettings,
    StateSetData,
    StepData,
    SubmissionMode,
)
from data_const import ALL_CAMERAS_STR, ALL_STEREO_CAMERAS_STR
from deadline.client.exceptions import DeadlineOperationError
from deadline.max_shared.utilities.max_utils import get_batch_render_views, get_render_elements
from pymxs import runtime as rt
from utilities import max_utils

_logger = logging.getLogger(__name__)

# Maximum length for an OpenJD parameter definition name.
_OPENJD_PARAM_NAME_MAX_LENGTH: int = 64


def _make_param_name(step: "StepData", suffix: str) -> str:
    """Build an OpenJD parameter name from a step and suffix, truncating if needed.

    For batch views, prefixes the sanitized name with the view's index from the
    Batch Render Manager (e.g. ``B1_MyBatchView_Frames``). The name portion is
    truncated so the full parameter name fits within the OpenJD 64-character limit.

    For state sets (default mode), no index prefix is added.
    """
    base = step.name
    if step.batch_view is not None:
        prefix = f"B{step.batch_view.index}_"
        budget = _OPENJD_PARAM_NAME_MAX_LENGTH - len(prefix) - len("_") - len(suffix)
        return f"{prefix}{base[:budget]}_{suffix}"
    else:
        return f"{base}_{suffix}"


def get_job_template(
    default_job_template: dict[str, Any],
    settings: RenderSubmitterUISettings,
    state_sets: list[StateSetData],
    cameras_in_scene: list,
) -> dict[str, Any]:
    """
    Creates a job template based on the current UI settings.

    :param default_job_template: the default 3dsMax job template
    :param settings: a RenderSubmitterUISettings object containing the latest UI settings
    :param state_sets: a list of StateSetData for the submitted state sets
    :param cameras_in_scene: all cameras based on the UI selection
    """
    job_template = _create_param_definitions(
        default_job_template, settings, state_sets, cameras_in_scene
    )
    job_template = _create_step_definitions(job_template, settings, state_sets, cameras_in_scene)

    # If this developer option is enabled, merge the adaptor_override_environment
    if settings.include_adaptor_wheels:
        override_environment = _merge_adaptor_override_environment()

        # There are no parameter conflicts between these two templates, so this works
        job_template["parameterDefinitions"].extend(override_environment["parameterDefinitions"])

        # Add the environment to the end of the template's job environments
        if "jobEnvironments" not in job_template:
            job_template["jobEnvironments"] = []
        job_template["jobEnvironments"].append(override_environment["environment"])

    return job_template


def _create_job_bundle_render_element_props(
    job_template: dict[str, Any], settings: RenderSubmitterUISettings
) -> None:
    """
    Creates render element parameter definitions and adds them to the job template.

    :param job_template: the job template to modify
    :param settings: a RenderSubmitterUISettings object containing the latest UI settings
    """
    render_elements = get_render_elements()
    if render_elements:
        # Enabled to modify RenderElement settings at render time.
        job_template["parameterDefinitions"].append(
            {
                "name": "RenderElementsModified",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Modify Render Elements",
                    "groupLabel": "Render Elements",
                },
                "description": "Enable or disable modification of render elements settings.",
                "default": "true" if settings.enabled_modify_render_elements else "false",
                "allowedValues": ["true", "false"],
            }
        )

        # RenderElements parameter - whether to output render elements
        job_template["parameterDefinitions"].append(
            {
                "name": "RenderElements",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Output Render Elements",
                    "groupLabel": "Render Elements",
                },
                "description": "Enable or disable render elements output.",
                "default": "true",
                "allowedValues": ["true", "false"],
            }
        )

        # RenderElementsUpdatePaths parameter - whether to update render element paths
        job_template["parameterDefinitions"].append(
            {
                "name": "RenderElementsUpdatePaths",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Update Render Element Paths",
                    "groupLabel": "Render Elements",
                },
                "description": "Automatically update render element output paths based on naming settings.",
                "default": "true",
                "allowedValues": ["true", "false"],
            }
        )

        # RenderElementsIncludeNameInPath parameter - include element name in path
        job_template["parameterDefinitions"].append(
            {
                "name": "RenderElementsIncludeNameInPath",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Include Render Element Name in Path",
                    "groupLabel": "Render Elements",
                },
                "description": "Add render element name as subdirectory in output path.",
                "default": "true",
                "allowedValues": ["true", "false"],
            }
        )

        # RenderElementsIncludeTypeInPath parameter - include element type in path
        job_template["parameterDefinitions"].append(
            {
                "name": "RenderElementsIncludeTypeInPath",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Include Render Element Type in Path",
                    "groupLabel": "Render Elements",
                },
                "description": "Add render element type as subdirectory in output path.",
                "default": "false",
                "allowedValues": ["true", "false"],
            }
        )

        # RenderElementsIncludeNameInFilename parameter - include element name in filename
        job_template["parameterDefinitions"].append(
            {
                "name": "RenderElementsIncludeNameInFilename",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Include Render Element Name in Filename",
                    "groupLabel": "Render Elements",
                },
                "description": "Add render element name to output filename.",
                "default": "true",
                "allowedValues": ["true", "false"],
            }
        )

        # RenderElementsIncludeTypeInFilename parameter - include element type in filename
        job_template["parameterDefinitions"].append(
            {
                "name": "RenderElementsIncludeTypeInFilename",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Include Render Element Type in Filename",
                    "groupLabel": "Render Elements",
                },
                "description": "Add render element type to output filename.",
                "default": "false",
                "allowedValues": ["true", "false"],
            }
        )

        # VRayRenderElementsVFBControl parameter - V-Ray VFB control
        job_template["parameterDefinitions"].append(
            {
                "name": "VRayRenderElementsVFBControl",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "V-Ray Render Elements VFB Control",
                    "groupLabel": "Render Elements",
                },
                "description": "Automatically control V-Ray VFB settings for render elements during rendering.",
                "default": "true",
                "allowedValues": ["true", "false"],
            }
        )

        # VRaySplitBufferSupport parameter - V-Ray split buffer support
        job_template["parameterDefinitions"].append(
            {
                "name": "VRaySplitBufferSupport",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "V-Ray Split Buffer Support",
                    "groupLabel": "Render Elements",
                },
                "description": "Enable V-Ray split buffer support for render elements.",
                "default": "true",
                "allowedValues": ["true", "false"],
            }
        )

        # IgnoreRenderElementsByName parameter - list of render element names to ignore
        if any(elem.name for elem in render_elements):
            element_names = [""] + [elem.name for elem in render_elements if elem.name]
            job_template["parameterDefinitions"].append(
                {
                    "name": "IgnoreRenderElementsByName",
                    "type": "STRING",
                    "userInterface": {
                        "control": "DROPDOWN_LIST",
                        "label": "Ignore Render Elements by Name",
                        "groupLabel": "Render Elements",
                    },
                    "description": "List of render element names to ignore during rendering.",
                    "default": "",
                    "allowedValues": element_names,
                }
            )


def _create_param_definitions(
    default_job_template: dict[str, Any],
    settings: RenderSubmitterUISettings,
    state_sets: list[StateSetData],
    cameras_in_scene: list,
) -> dict[str, Any]:
    """
    Creates parameter definitions based on the current UI settings.

    :param default_job_template: the default 3dsMax job template
    :param settings: a RenderSubmitterUISettings object containing the latest UI settings
    :param state_sets: a list of StateSetData for the submitted state sets
    :param cameras_in_scene: all cameras based on the UI selection
    """
    job_template = deepcopy(default_job_template)
    # Set the job's name
    job_template["name"] = settings.name
    if settings.description:
        job_template["description"] = settings.description

    # Build StepData list based on submission mode (mutually exclusive)
    steps: list[StepData] = []
    if settings.submission_mode == SubmissionMode.BATCH_RENDER.value:
        # One step per enabled batch view, no state set
        if settings.batch_render.enabled_views:
            all_batch_views = get_batch_render_views()
            batch_views = [item for item in all_batch_views if item.enabled]
            steps = [StepData(batch_view=bv) for bv in batch_views]
    else:
        # DEFAULT — existing State Sets + Cameras workflow
        steps = [StepData(state_set=ss) for ss in state_sets]

    # Create step-specific parameter definitions
    step_params: list[dict[str, Any]] = []
    for step in steps:
        if step.batch_view and step.state_set is None:
            group_label = step.batch_view.name
        else:
            group_label = step.state_set.ui_group_label
        # Frames parameter
        step_params.append(
            {
                "name": _make_param_name(step, "Frames"),
                "type": "STRING",
                "userInterface": {
                    "control": "LINE_EDIT",
                    "label": "Frames",
                    "groupLabel": group_label,
                },
                "description": "The frames to render. E.g. 1-3,8,11-15",
                "minLength": 1,
            }
        )
        # OutputFilePath parameter
        step_params.append(
            {
                "name": _make_param_name(step, "OutputFilePath"),
                "type": "PATH",
                "objectType": "DIRECTORY",
                "dataFlow": "OUT",
                "userInterface": {
                    "control": "CHOOSE_DIRECTORY",
                    "label": "Output File Path",
                    "groupLabel": group_label,
                },
                "description": "The render output path.",
            }
        )
        # OutputFileName parameter
        step_params.append(
            {
                "name": _make_param_name(step, "OutputFileName"),
                "type": "STRING",
                "userInterface": {
                    "control": "LINE_EDIT",
                    "label": "Output File Name",
                    "groupLabel": group_label,
                },
                "description": "The output file name.",
            }
        )
        # OutputFileFormat parameter
        step_params.append(
            {
                "name": _make_param_name(step, "OutputFileFormat"),
                "type": "STRING",
                "userInterface": {
                    "control": "LINE_EDIT",
                    "label": "Output File Format",
                    "groupLabel": group_label,
                },
                "description": "The output file extension.",
            }
        )
        # ImageWidth parameter
        step_params.append(
            {
                "name": _make_param_name(step, "ImageWidth"),
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Image Width",
                    "groupLabel": group_label,
                },
                "minValue": 1,
                "description": "The image width of the output.",
            }
        )
        # ImageHeight parameter
        step_params.append(
            {
                "name": _make_param_name(step, "ImageHeight"),
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Image Height",
                    "groupLabel": group_label,
                },
                "minValue": 1,
                "description": "The image height of the output.",
            }
        )
        # Batch render step-specific parameters
        if step.batch_view is not None:
            # Camera parameter
            step_params.append(
                {
                    "name": _make_param_name(step, "Camera"),
                    "type": "STRING",
                    "userInterface": {
                        "control": "LINE_EDIT",
                        "label": "Camera",
                        "groupLabel": group_label,
                    },
                    "description": "The camera to render from.",
                    "default": "",
                }
            )
            # SceneState parameter
            step_params.append(
                {
                    "name": _make_param_name(step, "SceneState"),
                    "type": "STRING",
                    "userInterface": {
                        "control": "LINE_EDIT",
                        "label": "Scene State",
                        "groupLabel": group_label,
                    },
                    "description": "Scene state to restore before rendering.",
                    "default": "",
                }
            )
            # PresetFile parameter
            step_params.append(
                {
                    "name": _make_param_name(step, "PresetFile"),
                    "type": "STRING",
                    "userInterface": {
                        "control": "LINE_EDIT",
                        "label": "Preset File",
                        "groupLabel": group_label,
                    },
                    "description": "Render preset file (.rps) to load before rendering.",
                    "default": "",
                }
            )
            # PixelAspect parameter
            step_params.append(
                {
                    "name": _make_param_name(step, "PixelAspect"),
                    "type": "STRING",
                    "userInterface": {
                        "control": "LINE_EDIT",
                        "label": "Pixel Aspect",
                        "groupLabel": group_label,
                    },
                    "description": "Pixel aspect ratio override.",
                    "default": "",
                }
            )

    # Add sorted step-specific parameters
    job_template["parameterDefinitions"].extend(sorted(step_params, key=lambda p: str(p["name"])))

    # Only add camera parameter to template when a specific camera is selected
    if (
        settings.camera_selection != ALL_CAMERAS_STR
        and settings.camera_selection != ALL_STEREO_CAMERAS_STR
    ):
        job_template["parameterDefinitions"].append(
            {
                "name": "Camera",
                "type": "STRING",
                "userInterface": {
                    "control": "DROPDOWN_LIST",
                    "groupLabel": "3dsMax Settings",
                },
                "description": "The camera to render from.",
                "allowedValues": cameras_in_scene,
            }
        )

    # Add render elements parameters if render elements are present in the scene
    _create_job_bundle_render_element_props(job_template, settings)

    return job_template


def _create_step_definitions(
    job_template: dict[str, Any],
    settings: RenderSubmitterUISettings,
    state_sets: list[StateSetData],
    cameras_in_scene: list,
) -> dict[str, Any]:
    """
    Creates steps for state sets and/or batch render views.

    :param job_template: the job template with updated parameter definitions for the job bundle
    :param settings: a RenderSubmitterUISettings object containing the latest UI settings
    :param state_sets: a list of StateSetData for the submitted state sets
    :param cameras_in_scene: all cameras based on the UI selection
    """
    # Replicate default step per state set
    default_step = job_template["steps"][0]
    job_template["steps"] = []

    # Mapping from job template parameter names to init-data keys
    param_to_init_data_key = {
        "OutputFilePath": "output_file_path",
        "OutputFileName": "output_file_name",
        "OutputFileFormat": "output_file_format",
        "ImageWidth": "image_width",
        "ImageHeight": "image_height",
    }

    # Build StepData list based on submission mode (mutually exclusive)
    steps: list[StepData] = []
    if settings.submission_mode == SubmissionMode.BATCH_RENDER.value:
        # One step per enabled batch view, no state set
        if settings.batch_render.enabled_views:
            all_batch_views = get_batch_render_views()
            batch_views = [item for item in all_batch_views if item.enabled]
            steps = [StepData(batch_view=bv) for bv in batch_views]
    else:
        # DEFAULT — existing State Sets + Cameras workflow
        if len(state_sets) <= 0:
            raise ValueError("At least one state set is required.")
        steps = [StepData(state_set=ss) for ss in state_sets]

    # Create steps from StepData
    for step_data in steps:
        # Create the step
        step = deepcopy(default_step)
        step["name"] = step_data.name
        parameters_space = step["parameterSpace"]

        # Always use step-specific frame parameter
        parameters_space["taskParameterDefinitions"][0]["range"] = (
            "{{Param." + _make_param_name(step_data, "Frames") + "}}"
        )

        # init data of the step
        init_data = step["stepEnvironments"][0]["script"]["embeddedFiles"][0]

        # Renderer is always required by the adaptor schema
        init_data["data"] += f"renderer: {settings.renderer}\n"

        if settings.submission_mode == SubmissionMode.BATCH_RENDER.value:
            # Batch render mode: write individual settings from batch view
            # Camera: only if the batch view has one assigned
            if step_data.batch_view.camera:
                init_data[
                    "data"
                ] += f"camera: '{{{{Param.{_make_param_name(step_data, 'Camera')}}}}}'\n"

            # Scene state: only if assigned
            if step_data.batch_view.scene_state:
                init_data[
                    "data"
                ] += f"scene_state: '{{{{Param.{_make_param_name(step_data, 'SceneState')}}}}}'\n"

            # Preset file: only if assigned
            if step_data.batch_view.preset_file:
                init_data[
                    "data"
                ] += f"preset_file: '{{{{Param.{_make_param_name(step_data, 'PresetFile')}}}}}'\n"

            # Pixel aspect: only if override_preset is true and pixel_aspect is set
            if (
                step_data.batch_view.override_preset
                and step_data.batch_view.pixel_aspect is not None
            ):
                init_data[
                    "data"
                ] += f"pixel_aspect: '{{{{Param.{_make_param_name(step_data, 'PixelAspect')}}}}}'\n"
        else:
            # DEFAULT mode: preserve existing init-data logic

            # If submitting all cameras, add 'Camera' to task parameters
            if (
                settings.camera_selection == ALL_CAMERAS_STR
                or settings.camera_selection == ALL_STEREO_CAMERAS_STR
            ):
                parameters_space["taskParameterDefinitions"].append(
                    {"name": "Camera", "type": "STRING", "range": cameras_in_scene}
                )
                run_data = step["script"]["embeddedFiles"][0]
                run_data["data"] += "camera: '{{Task.Param.Camera}}'"

            init_data["data"] += f"state_set: {step_data.state_set.state_set}\n"

            # If a specific camera is selected, link to the Camera parameter
            if (
                settings.camera_selection != ALL_CAMERAS_STR
                and settings.camera_selection != ALL_STEREO_CAMERAS_STR
            ):
                init_data["data"] += "camera: '{{Param.Camera}}'\n"

        # Add step-specific output parameters (applies to both modes)
        for suffix, init_data_key in param_to_init_data_key.items():
            init_data[
                "data"
            ] += f"{init_data_key}: '{{{{Param.{_make_param_name(step_data, suffix)}}}}}'\n"

        # Add render element parameters to init data only if render elements exist
        render_elements = get_render_elements()
        if render_elements:
            for param in RENDER_ELEMENT_PARAMS:
                # Convert parameter name to snake_case for init data with proper mapping
                init_data_key = RENDER_ELEMENT_PARAM_MAPPING.get(param, param.lower())
                init_data["data"] += f"{init_data_key}: '{{{{Param.{param}}}}}'\n"

        # Inject per-task run timeout when the user has configured one.
        # The timeout field on onRun is enforced by the OpenJD session runtime;
        # no adaptor changes are needed.
        if settings.task_run_timeout_seconds > 0:
            on_run_action = step["script"]["actions"]["onRun"]
            on_run_action["timeout"] = settings.task_run_timeout_seconds

        job_template["steps"].append(step)

    return job_template


def _get_batch_view_settings(
    batch_view: BatchRenderView,
    default_frame_range: str,
    default_resolution: tuple[int, int],
) -> dict[str, Any]:
    """
    Get render settings for a single batch view.

    Extracts frame range and resolution from preset files, then applies any overrides.
    Falls back to state set defaults for any missing values.

    :param batch_view: BatchRenderView dataclass instance
    :param default_frame_range: default frame range to use
    :param default_resolution: default resolution to use (width, height)
    :return: dict with keys 'frame_range', 'width', 'height'
    """
    # Initialize with state set defaults
    settings = {
        "frame_range": default_frame_range,
        "width": default_resolution[0],
        "height": default_resolution[1],
    }

    # Load preset settings if available and not all overrides are provided
    if batch_view.preset_file and not batch_view.has_all_overrides:
        _logger.debug(f"Loading preset file for '{batch_view.name}': {batch_view.preset_file}")
        try:
            preset_settings = max_utils.extract_settings_from_preset(batch_view.preset_file)
            if preset_settings:
                if preset_settings.get("frame_range"):
                    settings["frame_range"] = preset_settings["frame_range"]
                    _logger.debug(
                        f"Using preset frame range for '{batch_view.name}': {settings['frame_range']}"
                    )
                if preset_settings.get("width"):
                    settings["width"] = preset_settings["width"]
                    _logger.debug(
                        f"Using preset width for '{batch_view.name}': {settings['width']}"
                    )
                if preset_settings.get("height"):
                    settings["height"] = preset_settings["height"]
                    _logger.debug(
                        f"Using preset height for '{batch_view.name}': {settings['height']}"
                    )
        except Exception as e:
            _logger.warning(
                f"Failed to extract settings from preset file {batch_view.preset_file}: {e}. "
                f"Falling back to state set settings."
            )

    # Apply overrides on top of current settings
    if batch_view.override_preset:
        if batch_view.frame_start is not None and batch_view.frame_end is not None:
            settings["frame_range"] = f"{batch_view.frame_start}-{batch_view.frame_end}"
            _logger.debug(
                f"Using override frame range for '{batch_view.name}': {settings['frame_range']}"
            )
        if batch_view.width is not None:
            settings["width"] = batch_view.width
            _logger.debug(f"Using override width for '{batch_view.name}': {settings['width']}")
        if batch_view.height is not None:
            settings["height"] = batch_view.height
            _logger.debug(f"Using override height for '{batch_view.name}': {settings['height']}")

    _logger.debug(f"Final settings for '{batch_view.name}': {settings}")
    return settings


def _merge_adaptor_override_environment() -> dict[str, Any]:
    """
    Create template for the adaptor override environment.

    Loads the adaptor_override_environment.yaml file, validates the wheels directory,
    and configures the OverrideAdaptorName parameter with the default value.

    :return: The override environment dictionary loaded from YAML
    :raises RuntimeError: If the YAML file is invalid or wheels directory is missing/incorrect
    """
    with open(Path(__file__).parent / "adaptor_override_environment.yaml") as f:
        override_environment = yaml.safe_load(f)

    if override_environment is None:
        raise RuntimeError(
            "Failed to load adaptor_override_environment.yaml - file is empty or invalid"
        )

    if "parameterDefinitions" not in override_environment:
        raise RuntimeError(
            f"adaptor_override_environment.yaml is missing 'parameterDefinitions'. Keys found: {list(override_environment.keys())}"
        )

    # Validate wheels directory exists and contains the correct packages
    wheels_path = Path(__file__).parent.parent.parent.parent / "wheels"
    _logger.info(f"Validating wheels directory: {wheels_path}")

    if not wheels_path.exists() or not wheels_path.is_dir():
        raise RuntimeError(
            "The Developer Option 'Include Adaptor Wheels' is enabled, "
            f"but the wheels directory does not exist: {wheels_path}"
        )

    wheel_files = [f for f in os.listdir(wheels_path) if f.endswith(".whl")]
    wheels_path_package_names = {path.split("-", 1)[0] for path in wheel_files}

    # Check for duplicate packages (multiple versions of the same package)
    package_counts: dict[str, int] = {}
    for wheel_file in wheel_files:
        package_name = wheel_file.split("-", 1)[0]
        package_counts[package_name] = package_counts.get(package_name, 0) + 1

    duplicates = {pkg: count for pkg, count in package_counts.items() if count > 1}
    if duplicates:
        duplicate_details = []
        for pkg in duplicates:
            matching_wheels = [f for f in wheel_files if f.startswith(pkg + "-")]
            duplicate_details.append(f"  {pkg}: {len(matching_wheels)} versions found")
            for wheel in matching_wheels:
                duplicate_details.append(f"    - {wheel}")
        raise RuntimeError(
            "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels directory contains "
            "multiple versions of the same package(s):\n"
            + "\n".join(duplicate_details)
            + "\n\nPlease ensure only one version of each package is present. "
            + "Run 'scripts/build_wheels.ps1 -Clean' to rebuild with a clean directory."
        )

    expected_packages = {"openjd_adaptor_runtime", "deadline", "deadline_cloud_for_3ds_max"}
    if wheels_path_package_names != expected_packages:
        raise RuntimeError(
            "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels directory contains the "
            "wrong wheels:\n"
            + f"Expected: {', '.join(sorted(expected_packages))}\n"
            + f"Actual: {', '.join(sorted(wheels_path_package_names))}"
        )

    _logger.info(f"Found required wheel packages: {', '.join(sorted(wheels_path_package_names))}")

    # Find and validate OverrideAdaptorWheels parameter
    override_adaptor_wheels_params = [
        param
        for param in override_environment["parameterDefinitions"]
        if param and param.get("name") == "OverrideAdaptorWheels"
    ]

    if not override_adaptor_wheels_params:
        raise RuntimeError(
            "Could not find 'OverrideAdaptorWheels' parameter in adaptor_override_environment.yaml"
        )

    # Find and configure OverrideAdaptorName parameter
    override_adaptor_name_params = [
        param
        for param in override_environment["parameterDefinitions"]
        if param and param.get("name") == "OverrideAdaptorName"
    ]

    if not override_adaptor_name_params:
        raise RuntimeError(
            "Could not find 'OverrideAdaptorName' parameter in adaptor_override_environment.yaml"
        )

    override_adaptor_name_param = override_adaptor_name_params[0]
    override_adaptor_name_param["default"] = "3dsmax-openjd"
    _logger.info("Configured adaptor override environment with adaptor name: 3dsmax-openjd")

    # Load the setup script from external file and inject it into the embedded files
    setup_script_path = Path(__file__).parent / "setup_adaptor_wheels.py"
    with open(setup_script_path, "r", encoding="utf8") as f:
        setup_script_content = f.read()

    # Find the SetupAdaptor embedded file and update its data
    embedded_files = override_environment["environment"]["script"]["embeddedFiles"]
    for embedded_file in embedded_files:
        if embedded_file.get("name") == "SetupAdaptor":
            embedded_file["data"] = setup_script_content
            _logger.info(f"Loaded setup script from {setup_script_path}")
            break
    else:
        raise RuntimeError(
            "Could not find 'SetupAdaptor' embedded file in adaptor_override_environment.yaml"
        )

    return override_environment


def get_parameters_values(
    settings: RenderSubmitterUISettings,
    state_sets: list[StateSetData],
    queue_parameters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Creates parameter values based on the current UI settings.

    :param settings: a RenderSubmitterUISettings object containing the latest UI settings
    :param state_sets: a list of StateSetData for the submitted state sets
    :param queue_parameters: the settings from the shared job settings tab
    """
    # Validate render elements parameter consistency
    _validate_render_elements_parameters(settings)

    parameter_values = _get_job_parameters(settings, state_sets)
    queue_parameters = _get_queue_parameters_for_bundle(
        settings, parameter_values, queue_parameters
    )
    parameter_values.extend(
        {"name": param["name"], "value": param["value"]} for param in queue_parameters
    )

    return parameter_values


def _get_job_parameters(
    settings: RenderSubmitterUISettings,
    state_sets: list[StateSetData],
) -> list[dict[str, Any]]:
    """
    Creates all the job parameters on the current UI settings.

    :param settings: a RenderSubmitterUISettings object containing the latest UI settings
    :param state_sets: a list of StateSetData for the submitted state sets
    """
    parameter_values: list[dict[str, Any]] = []

    parameter_values.append({"name": "MaxSceneFile", "value": max_utils.get_scene_path()})

    # Build step data list based on submission mode (mutually exclusive)
    steps: list[StepData] = []

    if settings.submission_mode == SubmissionMode.BATCH_RENDER.value:
        # Batch render mode: one step per enabled batch view, no state set.
        # Read scene defaults from pymxs API and submitter UI settings as fallbacks.
        scene_frame_range = max_utils.get_frames()
        scene_width = int(rt.renderWidth)
        scene_height = int(rt.renderHeight)

        batch_views: list[BatchRenderView] = []
        if settings.batch_render.enabled_views:
            all_batch_views = get_batch_render_views()
            batch_views = [item for item in all_batch_views if item.enabled]

        for bv in batch_views:
            steps.append(
                StepData(
                    batch_view=bv,
                    frame_range=scene_frame_range,
                    width=scene_width,
                    height=scene_height,
                )
            )

        # Process batch views to extract preset/override settings
        if steps:
            progress = QProgressDialog()
            progress.setLabelText(f"Generating {len(steps)} steps...")
            progress.setCancelButton(None)
            progress.setMinimum(0)
            progress.setMaximum(len(steps))
            progress.setWindowTitle("Processing batch Render views")
            progress.setWindowModality(Qt.ApplicationModal)
            progress.setMinimumDuration(0)
            progress.setAutoClose(False)
            progress.setAutoReset(False)
            progress.setValue(0)
            progress.show()
            QApplication.processEvents()

            try:
                for i, step in enumerate(steps):
                    progress.setValue(i)
                    QApplication.processEvents()

                    settings_dict = _get_batch_view_settings(
                        batch_view=step.batch_view,
                        default_frame_range=scene_frame_range,
                        default_resolution=(scene_width, scene_height),
                    )

                    # Validate batch view settings before creating parameters.
                    # Note: preset file existence is NOT checked here because the
                    # path stored in the scene may be from a different machine and
                    # will be resolved via path mapping at render time.
                    bv = step.batch_view
                    if bv.camera:
                        scene_cameras = [
                            cam.name for cam in rt.cameras if "$Target:" not in str(cam)
                        ]
                        if bv.camera not in scene_cameras:
                            raise ValueError(
                                f"Batch view '{bv.name}' references camera '{bv.camera}' "
                                f"which does not exist in the scene"
                            )
                    if bv.scene_state:
                        if rt.sceneStateMgr.FindSceneState(bv.scene_state) < 0:
                            raise ValueError(
                                f"Batch view '{bv.name}' references scene state "
                                f"'{bv.scene_state}' which does not exist"
                            )
                    if bv.preset_file:
                        if not os.path.exists(bv.preset_file):
                            _logger.warning(
                                f"Batch view '{bv.name}' references preset file "
                                f"'{bv.preset_file}' which does not exist locally. "
                                f"It will be resolved via path mapping at render time."
                            )
                    if bv.override_preset and bv.pixel_aspect is not None:
                        if bv.pixel_aspect <= 0:
                            raise ValueError(
                                f"Batch view '{bv.name}' has invalid pixel aspect: "
                                f"{bv.pixel_aspect} (must be a positive number)"
                            )

                    # If the user has enabled Override Frame Range, it takes highest
                    # priority over all batch view frame ranges (preset and override alike).
                    if settings.override_frame_range and settings.frame_list:
                        step.frame_range = settings.frame_list
                    else:
                        step.frame_range = settings_dict["frame_range"]
                    step.width = settings_dict["width"]
                    step.height = settings_dict["height"]
            finally:
                progress.close()

    else:
        # DEFAULT mode: existing State Sets + Cameras workflow, no batch views
        for state_set in state_sets:
            steps.append(
                StepData(
                    state_set=state_set,
                    frame_range=state_set.frame_range,
                    width=state_set.image_resolution[0],
                    height=state_set.image_resolution[1],
                )
            )

    # Create parameters for all steps
    for step in steps:
        # For default mode, use state set data for output settings.
        # For batch render mode, extract output dir/name/format from the batch view's
        # output_filename configured in the scene.
        if step.state_set is not None:
            step_output_file_dir = step.state_set.output_file_dir
            step_output_file_name = step.state_set.output_file_name
            step_output_file_format = step.state_set.output_file_format
        else:
            # Batch render mode: output comes entirely from the batch view's scene data
            if not step.batch_view.output_filename:
                raise ValueError(
                    f"Batch view '{step.batch_view.name}' has no output filename configured "
                    f"in the Batch Render Manager."
                )
            bv_output = step.batch_view.output_filename
            step_output_file_dir = os.path.dirname(bv_output)
            bv_basename = os.path.basename(bv_output)
            bv_name, bv_ext = os.path.splitext(bv_basename)
            step_output_file_name = bv_name
            step_output_file_format = bv_ext if bv_ext else ""
            if not step_output_file_format:
                raise ValueError(
                    f"Batch view '{step.batch_view.name}' output filename "
                    f"'{bv_basename}' has no file extension."
                )

        parameter_values.extend(
            [
                {"name": _make_param_name(step, "Frames"), "value": step.frame_range},
                {
                    "name": _make_param_name(step, "OutputFilePath"),
                    "value": step_output_file_dir,
                },
                {
                    "name": _make_param_name(step, "OutputFileName"),
                    "value": step_output_file_name,
                },
                {
                    "name": _make_param_name(step, "OutputFileFormat"),
                    "value": step_output_file_format,
                },
                {"name": _make_param_name(step, "ImageWidth"), "value": step.width},
                {"name": _make_param_name(step, "ImageHeight"), "value": step.height},
            ]
        )

        # Add batch render view-specific parameter values
        if step.batch_view is not None:
            if step.batch_view.camera:
                parameter_values.append(
                    {"name": _make_param_name(step, "Camera"), "value": step.batch_view.camera}
                )
            if step.batch_view.scene_state:
                parameter_values.append(
                    {
                        "name": _make_param_name(step, "SceneState"),
                        "value": step.batch_view.scene_state,
                    }
                )
            if step.batch_view.preset_file:
                parameter_values.append(
                    {
                        "name": _make_param_name(step, "PresetFile"),
                        "value": step.batch_view.preset_file,
                    }
                )
            if step.batch_view.override_preset and step.batch_view.pixel_aspect is not None:
                parameter_values.append(
                    {
                        "name": _make_param_name(step, "PixelAspect"),
                        "value": str(step.batch_view.pixel_aspect),
                    }
                )

    # Only add camera parameter when a specific camera is selected
    if (
        settings.camera_selection != ALL_CAMERAS_STR
        and settings.camera_selection != ALL_STEREO_CAMERAS_STR
    ):
        parameter_values.append({"name": "Camera", "value": settings.camera_selection})

    # Add render elements parameters if render elements are present in the scene
    render_elements = get_render_elements()
    if render_elements:
        # Enabled to modify RenderElement settings at render time.
        parameter_values.append(
            {
                "name": "RenderElementsModified",
                "value": "true" if settings.enabled_modify_render_elements else "false",
            }
        )

        # RenderElements parameter
        parameter_values.append(
            {"name": "RenderElements", "value": "true" if settings.render_elements else "false"}
        )

        # Enhanced Render Elements Parameter Values (Authentic Deadline 10 features)

        # RenderElementsUpdatePaths parameter
        parameter_values.append(
            {
                "name": "RenderElementsUpdatePaths",
                "value": "true" if settings.render_elements_update_paths else "false",
            }
        )

        # RenderElementsIncludeNameInPath parameter
        parameter_values.append(
            {
                "name": "RenderElementsIncludeNameInPath",
                "value": "true" if settings.render_elements_include_name_in_path else "false",
            }
        )

        # RenderElementsIncludeTypeInPath parameter
        parameter_values.append(
            {
                "name": "RenderElementsIncludeTypeInPath",
                "value": "true" if settings.render_elements_include_type_in_path else "false",
            }
        )

        # RenderElementsIncludeNameInFilename parameter
        parameter_values.append(
            {
                "name": "RenderElementsIncludeNameInFilename",
                "value": "true" if settings.render_elements_include_name_in_filename else "false",
            }
        )

        # RenderElementsIncludeTypeInFilename parameter
        parameter_values.append(
            {
                "name": "RenderElementsIncludeTypeInFilename",
                "value": "true" if settings.render_elements_include_type_in_filename else "false",
            }
        )

        # VRayRenderElementsVFBControl parameter
        parameter_values.append(
            {
                "name": "VRayRenderElementsVFBControl",
                "value": "true" if settings.vray_render_elements_vfb_control else "false",
            }
        )

        # VRaySplitBufferSupport parameter
        parameter_values.append(
            {
                "name": "VRaySplitBufferSupport",
                "value": "true" if settings.vray_split_buffer_support else "false",
            }
        )

        # IgnoreRenderElementsByName parameter
        if settings.ignore_render_elements_by_name:
            # Convert list to comma-separated string for OpenJD
            ignore_names_str = ",".join(settings.ignore_render_elements_by_name)
            parameter_values.append(
                {"name": "IgnoreRenderElementsByName", "value": ignore_names_str}
            )
        elif any(elem.name for elem in render_elements):
            # Add empty parameter if render elements exist but none are ignored
            parameter_values.append({"name": "IgnoreRenderElementsByName", "value": ""})

    # If we're overriding the adaptor with wheels, set the OverrideAdaptorWheels parameter
    if settings.include_adaptor_wheels:
        wheels_path = str(Path(__file__).parent.parent.parent.parent / "wheels")
        parameter_values.append({"name": "OverrideAdaptorWheels", "value": wheels_path})

    return parameter_values


def _get_queue_parameters_for_bundle(
    settings: RenderSubmitterUISettings,
    parameter_values: list[dict[str, Any]],
    queue_parameters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Checks for any overlap between the job parameters we've defined and the queue parameters.
    Removes the deadline_cloud_for_3ds_max from the RezPackages if adaptor wheels are included.

    :param settings: a RenderSubmitterUISettings object containing the latest UI settings
    :param parameter_values: the job parameters we've defined
    :param queue_parameters: the settings from the shared job settings tab

    :raises: a DeadlineOperationError if there is overlap between the job parameters and the queue parameters.
    This is an error, as we weren't synchronizing the values between the two different tabs where they came from.
    """
    parameter_names = {param["name"] for param in parameter_values}
    queue_parameter_names = {param["name"] for param in queue_parameters}
    parameter_overlap = parameter_names.intersection(queue_parameter_names)
    if parameter_overlap:
        raise DeadlineOperationError(
            "The following queue parameters conflict with the "
            "Max job parameters:\n" + f"{', '.join(parameter_overlap)}"
        )

    # If we're overriding the adaptor with wheels, remove deadline_cloud_for_3ds_max from the RezPackages
    if settings.include_adaptor_wheels:
        conda_param: dict[str, str] = {}
        # Find the RezPackages parameter definition
        for param in queue_parameters:
            if param["name"] == "CondaPackages":
                conda_param = param
                break
        # Remove the deadline_cloud_for_3ds_max rez package
        if conda_param:
            conda_param["value"] = " ".join(
                pkg for pkg in conda_param["value"].split() if not pkg.startswith("3dsmax-openjd")
            )

    return queue_parameters


def _validate_render_elements_parameters(settings: RenderSubmitterUISettings) -> None:
    """
    Validates render elements parameter consistency to ensure settings are coherent.

    :param settings: a RenderSubmitterUISettings object containing the latest UI settings
    :raises DeadlineOperationError: if render elements parameters are inconsistent
    """
    # If render elements are disabled, ignore other settings
    if not settings.render_elements:
        return

    # Validate that ignored render element names exist in the scene
    if settings.ignore_render_elements_by_name:
        try:
            # Get current render elements from scene to validate ignore list
            render_elements = get_render_elements()
            scene_element_names = {elem.name for elem in render_elements if elem.name}

            invalid_names = [
                name
                for name in settings.ignore_render_elements_by_name
                if name not in scene_element_names
            ]

            if invalid_names:
                raise DeadlineOperationError(
                    f"The following render element names to ignore do not exist in the scene: "
                    f"{', '.join(invalid_names)}"
                )
        except Exception as e:
            # If validation fails, log warning but don't fail submission
            _logger.warning(f"Could not validate render element names: {e}")
