# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Shared 3ds Max utilities for Deadline Cloud integration.

This module contains pymxs utilities that are shared between the submitter and adaptor
components to ensure consistent behavior for render elements detection, validation,
and management.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, TypedDict

import pymxs  # separate import to initialize  # noqa: F401
from pymxs import runtime as rt

_logger = logging.getLogger(__name__)


@dataclass
class RenderElementInfo:
    """
    Data class representing render element information.

    This class encapsulates all the properties of a render element
    that are used throughout the Deadline Cloud integration.
    """

    index: int
    name: str
    type: str
    enabled: bool
    output_filename: str
    has_output_path: bool
    vray_vfb: bool
    element_object: Any  # pymxs object reference


@dataclass
class VRayRenderElementSettings:
    """
    Data class representing V-Ray specific render element settings.

    This class encapsulates V-Ray render element configuration options
    that control VFB behavior and split buffer support.
    """

    vray_render_elements_vfb_control: bool = True
    vray_split_buffer_support: bool = False


@dataclass
class RenderElementConfigurationSettings:
    """
    Data class representing render element configuration settings.

    This class encapsulates all render element configuration options
    used for validation and path management.
    """

    ignore_render_elements_by_name: list[str] = field(default_factory=list)
    render_elements_update_paths: bool = True
    render_elements_include_name_in_path: bool = True
    render_elements_include_type_in_path: bool = False
    render_elements_include_name_in_filename: bool = True
    render_elements_include_type_in_filename: bool = False


@dataclass
class RenderElementState:
    """
    Data class representing the original state of render elements.

    This class stores the original state of render elements to enable
    restoration after rendering completes.
    """

    element_names: list[str]
    element_paths: list[str]
    element_enabled: list[bool]
    vray_vfb_states: list[bool]

    def __init__(self):
        """Initialize empty lists for all state data."""
        self.element_names = []
        self.element_paths = []
        self.element_enabled = []
        self.vray_vfb_states = []


@dataclass
class BatchRenderView:
    """
    Data class representing a view from 3ds Max's Batch Render dialog.
    """

    name: str
    index: int = 0
    enabled: bool = True
    camera: Optional[str] = None
    output_filename: str = ""
    scene_state: Optional[str] = None
    preset_file: Optional[str] = None
    override_preset: bool = False
    frame_start: Optional[int] = None
    frame_end: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    pixel_aspect: Optional[float] = None

    @property
    def has_all_overrides(self) -> bool:
        """Check if all override values are provided, allowing preset loading to be skipped."""
        return (
            self.override_preset
            and self.frame_start is not None
            and self.frame_end is not None
            and self.width is not None
            and self.height is not None
        )


def _view_to_batch_render_view(view, index: int) -> BatchRenderView:
    """
    Convert a pymxs batch render view to a BatchRenderView dataclass.

    :param view: pymxs batch render view object
    :param index: 1-based index of the view (used for fallback name)
    :returns: BatchRenderView dataclass instance
    """
    name = str(view.name) if view.name else f"View_{index}"
    enabled = bool(view.enabled)

    # Extract camera name
    camera = None
    if view.camera is not None and view.camera != rt.undefined:
        camera = str(view.camera.name)

    # Extract output filename
    output_filename = str(view.outputFilename) if view.outputFilename else ""

    # Extract scene state (note: attribute is sceneStateName in submitter context)
    scene_state = None
    if (
        hasattr(view, "sceneStateName")
        and view.sceneStateName
        and view.sceneStateName != rt.undefined
    ):
        scene_state = str(view.sceneStateName)
    elif (
        hasattr(view, "sceneState")
        and view.sceneState is not None
        and view.sceneState != rt.undefined
    ):
        scene_state = str(view.sceneState)

    # Extract preset file
    preset_file = str(view.presetFile) if view.presetFile else None

    # Extract override settings
    override_preset = bool(view.overridePreset)

    frame_start = int(view.startFrame) if override_preset and view.startFrame is not None else None
    frame_end = int(view.endFrame) if override_preset and view.endFrame is not None else None
    width = int(view.width) if override_preset and view.width is not None else None
    height = int(view.height) if override_preset and view.height is not None else None
    pixel_aspect = (
        float(view.pixelAspect) if override_preset and view.pixelAspect is not None else None
    )

    return BatchRenderView(
        name=name,
        index=index,
        enabled=enabled,
        camera=camera,
        output_filename=output_filename,
        scene_state=scene_state,
        preset_file=preset_file,
        override_preset=override_preset,
        frame_start=frame_start,
        frame_end=frame_end,
        width=width,
        height=height,
        pixel_aspect=pixel_aspect,
    )


def get_batch_render_views() -> list[BatchRenderView]:
    """
    Extract all batch render views from 3ds Max's Batch Render Manager.

    :returns: list of BatchRenderView dataclass instances
    :raises RuntimeError: if Batch Render Manager is not available
    """
    batch_mgr = rt.batchRenderMgr
    if not batch_mgr:
        raise RuntimeError("Batch Render Manager not available")

    batch_views: list[BatchRenderView] = []
    num_items = batch_mgr.numViews
    _logger.debug(f"Found {num_items} batch render views")

    for i in range(1, num_items + 1):
        view = batch_mgr.getView(i)
        if not view:
            raise RuntimeError(f"Could not get batch view at index {i}")

        batch_view = _view_to_batch_render_view(view, i)
        batch_views.append(batch_view)
        _logger.debug(
            f"Extracted batch render view: {batch_view.name} (enabled: {batch_view.enabled})"
        )

    return batch_views


# V-Ray RT class IDs (GPU renderer)
_VRAY_RT_CLASS_IDS: list[str] = [
    "#(1770671000, 1323107829)",
    "#(1770671000L, 1323107829L)",
]


def _is_vray_rt() -> bool:
    """
    Check if current renderer is V-Ray RT (GPU).

    Uses both class ID detection (reliable) and name-based detection (fallback).

    :returns: True if V-Ray RT, False otherwise
    """
    renderer: Any = rt.renderers.current
    renderer_class_id: str = str(renderer.classid)
    renderer_name: str = str(renderer)

    # Primary: Class ID detection (most reliable)
    class_id_match: bool = any(class_id in renderer_class_id for class_id in _VRAY_RT_CLASS_IDS)

    # Fallback: Name-based detection
    name_match: bool = "V_Ray_GPU" in renderer_name

    return class_id_match or name_match


def _get_vray_rt_settings() -> Optional[Any]:
    """
    Get the V-Ray RT settings object if current renderer is V-Ray RT.

    V-Ray RT (GPU) uses nested V_Ray_settings object.
    Standard V-Ray uses direct renderer access.

    :returns: V_Ray_settings object for V-Ray RT, None for standard V-Ray
    """
    if _is_vray_rt():
        renderer: Any = rt.renderers.current
        return renderer.V_Ray_settings
    return None


def _set_vray_property(prop_name: str, value: Any, warnings: list[str]) -> None:
    """
    Set a V-Ray property on the appropriate renderer object.

    V-Ray CPU and GPU have different property access patterns:
    - V-Ray GPU: Properties are set on vray_rt_settings first, then attempted on base renderer
    - V-Ray CPU: Properties are set on rt.renderers.current directly

    For V-Ray GPU, some properties (like output_splitfilename) only exist on vray_rt_settings,
    so we set on vray_rt_settings first, then try the base renderer but ignore failures.

    :param prop_name: name of the V-Ray property to set
    :param value: value to set for the property
    :param warnings: list to append warning messages to
    """
    vray_rt_settings = _get_vray_rt_settings()

    try:
        if vray_rt_settings is not None:
            # V-Ray GPU - set on vray_rt_settings first (required)
            setattr(vray_rt_settings, prop_name, value)
            _logger.debug(f"[_set_vray_property] Set vray_rt_settings.{prop_name} = {value}")
            # Also try to set on base renderer (some properties exist on both)
            try:
                setattr(rt.renderers.current, prop_name, value)
                _logger.debug(
                    f"[_set_vray_property] Set rt.renderers.current.{prop_name} = {value}"
                )
            except Exception:
                # Property may not exist on base renderer for V-Ray GPU - this is OK
                _logger.debug(
                    f"[_set_vray_property] Property {prop_name} not available on base renderer"
                )
        else:
            # V-Ray CPU - set on rt.renderers.current
            setattr(rt.renderers.current, prop_name, value)
            _logger.debug(f"[_set_vray_property] Set rt.renderers.current.{prop_name} = {value}")
    except Exception as e:
        warning_msg = f"Failed to set V-Ray property {prop_name}: {e}"
        _logger.warning(f"[_set_vray_property] {warning_msg}")
        warnings.append(warning_msg)


def get_render_elements() -> list[RenderElementInfo]:
    """
    Gets all render elements present in the max scene with their properties.

    This function provides render element detection that matches
    Deadline 10's functionality, including V-Ray VFB detection and element
    index tracking for later manipulation.

    :returns: a list of RenderElementInfo objects containing render element information
    """
    render_elements: list[RenderElementInfo] = []

    try:
        # Get render element manager
        re_manager = rt.maxOps.GetCurRenderElementMgr()
        if not re_manager:
            _logger.warning("No render element manager found")
            return render_elements

        # Iterate through all render elements
        for i in range(re_manager.NumRenderElements()):
            element = re_manager.GetRenderElement(i)
            if not element:
                continue

            # Skip Missing_Render_Element_Plug_in (Deadline 10 pattern)
            if rt.classof(element) == rt.Missing_Render_Element_Plug_in:
                _logger.debug(f"Skipping missing render element plugin at index {i}")
                continue

            # Extract render element information
            element_info = RenderElementInfo(
                index=i,
                name=(
                    str(element.elementName) if hasattr(element, "elementName") else f"Element_{i}"
                ),
                type=str(rt.classof(element)),
                enabled=bool(getattr(element, "enabled", True)),
                output_filename="",
                has_output_path=False,
                vray_vfb=False,
                element_object=element,  # Store reference for later manipulation
            )

            # Get output filename if available
            try:
                output_filename = re_manager.GetRenderElementFilename(i)
                if output_filename:
                    element_info.output_filename = str(output_filename).replace("\\", "/")
                    element_info.has_output_path = True
            except Exception as e:
                _logger.debug(f"Could not get output filename for render element {i}: {e}")

            # Check for V-Ray VFB property (V-Ray specific)
            try:
                if hasattr(element, "vrayVFB"):
                    element_info.vray_vfb = bool(element.vrayVFB)
            except Exception as e:
                _logger.debug(f"Could not get V-Ray VFB property for render element {i}: {e}")

            render_elements.append(element_info)

    except Exception as e:
        _logger.error(f"Error getting render elements: {e}")

    return render_elements


def validate_render_element_paths(render_elements: list[RenderElementInfo]) -> list[str]:
    """
    Validates render element output paths and returns warnings for problematic paths.

    This function provides path validation matching Deadline 10's
    sanity check system for render elements.

    :param render_elements: list of RenderElementInfo objects from get_render_elements()
    :returns: list of warning messages for render elements with path issues
    """
    warnings: list[str] = []

    for element in render_elements:
        element_name: str = element.name
        output_filename: str = element.output_filename
        enabled: bool = element.enabled

        # Skip disabled render elements
        if not enabled:
            continue

        # Check if output directory is accessible
        try:
            output_path: Path = Path(output_filename)
            parent_dir: Path = output_path.parent

            if not parent_dir.exists():
                warnings.append(
                    f"Render element '{element_name}' output directory does not exist: {parent_dir}"
                )
            elif not os.access(parent_dir, os.W_OK):
                warnings.append(
                    f"Render element '{element_name}' output directory is not writable: {parent_dir}"
                )

        except (OSError, ValueError) as e:
            warnings.append(
                f"Render element '{element_name}' has invalid output path: {output_filename} ({e})"
            )

    return warnings


def get_render_elements_output_directories() -> set[str]:
    """
    Gets all unique output directories from render elements in the scene.

    This function is used by both the submitter (for job bundle asset management)
    and the adaptor (for directory creation and validation).

    :returns: set of directory paths where render elements will be output
    """
    output_dirs: set[str] = set()

    try:
        render_elements: list[RenderElementInfo] = get_render_elements()
        for element in render_elements:
            output_filename: str = element.output_filename
            if output_filename and element.enabled:
                try:
                    output_path: Path = Path(output_filename)
                    parent_dir: str = str(output_path.parent).replace("\\", "/")
                    if parent_dir and parent_dir != ".":
                        output_dirs.add(parent_dir)
                except (OSError, ValueError):
                    continue

    except Exception as e:
        _logger.error(f"Error getting render element output directories: {e}")

    return output_dirs


def purify_render_element_name(element_name: str) -> str:
    """
    Purifies render element names by removing invalid characters for file paths.

    This matches Deadline 10's render element name purification logic to ensure
    consistent naming between GUI submission and render execution.

    :param element_name: original render element name
    :returns: purified element name safe for file paths
    """
    if not element_name:
        return "Element"

    # Replace invalid characters with underscores
    invalid_chars: list[str] = ["<", ">", ":", '"', "|", "?", "*", "/", "\\"]
    purified_name: str = element_name

    for char in invalid_chars:
        purified_name = purified_name.replace(char, "_")

    # Remove leading/trailing spaces and dots
    purified_name = purified_name.strip(" .")

    # Ensure name is not empty after purification
    if not purified_name:
        purified_name = "Element"

    return purified_name


def validate_render_element_configuration(
    render_elements: list[RenderElementInfo], settings: RenderElementConfigurationSettings
) -> list[str]:
    """
    Validates render element configuration against settings.

    This function provides comprehensive validation of render element settings
    to ensure consistency between GUI configuration and render execution.

    :param render_elements: list of RenderElementInfo objects
    :param settings: render element configuration settings
    :returns: list of validation warnings
    """
    warnings: list[str] = []

    if not render_elements:
        return warnings

    # Validate ignore by name settings
    ignore_by_name: list[str] = settings.ignore_render_elements_by_name
    if ignore_by_name:
        element_names: list[str] = [element.name for element in render_elements]
        for ignored_name in ignore_by_name:
            if ignored_name not in element_names:
                warnings.append(
                    f"Render element '{ignored_name}' specified in ignore list but not found in scene"
                )

    # Validate path settings consistency
    if settings.render_elements_update_paths:
        path_warnings: list[str] = validate_render_element_paths(render_elements)
        warnings.extend(path_warnings)

    return warnings


def configure_render_element_paths(
    render_elements: list[RenderElementInfo], settings: RenderElementConfigurationSettings
) -> list:
    """
    Configures render element paths based on settings.

    This function updates render element paths and filenames according to
    Deadline 10's path management system, including name/type inclusion options.

    :param render_elements: list of RenderElementInfo objects
    :param settings: render element configuration settings
    :returns: list of configuration warnings
    """
    warnings: list[str] = []

    if not render_elements or not settings.render_elements_update_paths:
        return warnings

    try:
        re_manager = rt.maxOps.GetCurRenderElementMgr()
        if not re_manager:
            warnings.append("No render element manager found")
            return warnings

        for element in render_elements:
            element_index: int = element.index
            element_name: str = element.name
            element_type: str = element.type

            if element_index < 0:
                continue

            # Build new path based on settings
            base_path: str = element.output_filename
            if not base_path:
                continue

            # Apply path modifications based on settings
            new_path: str = _build_render_element_path(
                base_path, element_name, element_type, settings
            )

            # Update render element path
            try:
                re_manager.SetRenderElementFilename(element_index, new_path)
                # Update the RenderElementInfo object so validation uses the correct path
                element.output_filename = new_path
                element.has_output_path = True
                _logger.debug(f"Updated render element '{element_name}' path to: {new_path}")
            except Exception as e:
                warnings.append(f"Failed to update path for render element '{element_name}': {e}")

    except Exception as e:
        _logger.error(f"Error configuring render element paths: {e}")
        warnings.append(f"Path configuration failed: {e}")

    return warnings


def is_vray_raw_output_format(output_format: str) -> bool:
    """
    Check if the output format requires V-Ray raw output pipeline.

    V-Ray raw output is used for .vrimg and .exr formats, which store all
    render elements in a single multichannel container file.

    :param output_format: Output format extension (e.g., ".exr", ".vrimg")
    :returns: True if format requires raw output pipeline
    """
    if not output_format:
        return False
    return output_format.lower() in [".vrimg", ".exr"]


def configure_vray_raw_output(
    output_path: str,
    output_name: str,
    output_format: str,
) -> list[str]:
    """
    Configure V-Ray raw image output (.vrimg or multichannel .exr).

    This function sets up V-Ray to output all render elements to a single
    multichannel container file using the V-Ray Frame Buffer pipeline.

    The properties must be set in this order:
    1. output_userigbe = True (enable VFB first)
    2. output_on = True (enable raw output feature)
    3. output_saveRawFile = True (enable file writing)
    4. output_rawFileName = path (set output path)

    :param output_path: Output directory path
    :param output_name: Base output filename (without extension)
    :param output_format: Output format extension (.vrimg or .exr)
    :returns: List of warning messages
    """
    warnings: list[str] = []

    try:
        # Build output filename with correct extension
        # Strip any existing extension from output_name to avoid double extensions
        # (e.g. output_name="render.exr" + extension=".exr" would produce "render.exr.exr")
        extension: str = output_format if output_format.startswith(".") else f".{output_format}"
        base_name: str = output_name
        if output_name.endswith(extension):
            base_name = output_name[: -len(extension)]
        raw_filename: str = os.path.join(output_path, f"{base_name}{extension}")

        # Step 1: Enable V-Ray Frame Buffer (required for raw output)
        _set_vray_property("output_userigbe", True, warnings)
        _logger.info(
            "[configure_vray_raw_output] Enabled V-Ray Frame Buffer (output_userigbe = True)"
        )

        # Step 2: Enable raw output feature
        _set_vray_property("output_on", True, warnings)
        _logger.info("[configure_vray_raw_output] Enabled V-Ray raw output (output_on = True)")

        # Step 3: Enable file writing
        _set_vray_property("output_saveRawFile", True, warnings)
        _logger.info(
            "[configure_vray_raw_output] Enabled V-Ray raw file saving (output_saveRawFile = True)"
        )

        # Step 4: Set output filename
        _set_vray_property("output_rawFileName", raw_filename, warnings)
        _logger.info(f"[configure_vray_raw_output] V-Ray raw output configured: {raw_filename}")

    except Exception as e:
        error_msg: str = f"Failed to configure V-Ray raw output: {e}"
        _logger.error(f"[configure_vray_raw_output] {error_msg}")
        warnings.append(error_msg)

    return warnings


def _configure_split_buffer_settings(
    output_path: Optional[str],
    output_name: Optional[str],
    output_file_format: str,
    warnings: list[str],
) -> Optional[str]:
    """
    Configure V-Ray split buffer settings for both CPU and GPU renderers.

    This helper function sets up the split buffer flags and filename that are
    common to both V-Ray VFB and 3dsMax framebuffer modes.

    D10 Pattern:
    - output_splitgbuffer = True (enable split buffer)
    - output_splitRGB = True (save RGB channels)
    - output_splitAlpha = True (save Alpha channel)
    - output_splitfilename = path (base filename for split files)

    NOTE: output_saveRawFile is for saving raw .vrimg files, NOT for split buffer.

    :param output_path: output directory path for split buffer files
    :param output_name: base output filename for split buffer files
    :param output_file_format: output file format/extension
    :param warnings: list to append warning messages to
    :returns: the base filepath if successfully configured, None otherwise
    """
    # D10: Enable split buffer flag only
    _set_vray_property("output_splitgbuffer", True, warnings)

    # Enable split RGB to save render elements to separate files
    # This is required for V-Ray to actually output the render element files
    _set_vray_property("output_splitRGB", True, warnings)
    _set_vray_property("output_splitAlpha", True, warnings)
    # NOTE: output_saveRawFile is for saving raw .vrimg files, NOT for split buffer output

    base_filepath: Optional[str] = None

    # Set the base filename for split files
    if output_path and output_name:
        base_name, _ = os.path.splitext(output_name)
        extension = (
            output_file_format if output_file_format.startswith(".") else f".{output_file_format}"
        )
        base_filepath = os.path.join(output_path, f"{base_name}{extension}")

        _logger.debug(
            "[_configure_split_buffer_settings] Setting output_splitfilename "
            "via _set_vray_property"
        )
        _set_vray_property("output_splitfilename", base_filepath, warnings)
        _logger.info(
            f"[_configure_split_buffer_settings] V-Ray split buffer filename set to: "
            f"{base_filepath}"
        )

        # Explicitly unset output_splitbitmap to ensure clean state
        # _set_vray_property("output_splitbitmap", rt.undefined, warnings)
        # rt.renderers.current.output_splitbitmap = rt.undefined
        # rt.renderers.current.V_Ray_settings.output_splitbitmap = rt.undefined
        _logger.info("[_configure_split_buffer_settings] V-Ray output_splitbitmap set to undefined")
    else:
        missing_params = []
        if not output_path:
            missing_params.append("output_file_path")
        if not output_name:
            missing_params.append("output_file_name (check template has this defined)")
        warnings.append(
            f"Split buffer enabled but missing: {', '.join(missing_params)} - split files may not save correctly"
        )

    return base_filepath


def _configure_render_element_filenames(
    render_elements: list[RenderElementInfo],
    base_filepath: Optional[str],
    ignore_list: list[str],
    warnings: list[str],
) -> None:
    """
    Configure filenames for render elements (D10 pattern).

    Sets a UNIQUE output filename for each render element by appending the
    element name to the base filename. Does NOT modify the element's enabled state.

    D10 Pattern:
    - Skip ignored elements (by name)
    - Skip disabled elements (read but don't modify enabled state)
    - Use SetRenderElementFilename() to set paths with unique names per element
    - Use SetElementsActive(True) to enable RE output
    - Does NOT use SetOutputEnabled()

    :param render_elements: list of RenderElementInfo objects
    :param base_filepath: base filepath for output (e.g., "C:/output/render.png")
    :param ignore_list: list of render element names to ignore
    :param warnings: list to append warning messages to
    """
    if not base_filepath:
        warnings.append("Render element filename setup skipped: Missing output path or name")
        return

    try:
        re_manager = rt.maxOps.GetCurRenderElementMgr()
        if not re_manager:
            warnings.append("Render element filename setup failed: No render element manager")
            return

        # Parse base filepath into components for building unique filenames
        base_dir = os.path.dirname(base_filepath)
        base_name_with_ext = os.path.basename(base_filepath)
        base_name, extension = os.path.splitext(base_name_with_ext)

        filename_set_count = 0
        for element in render_elements:
            # D10 pattern: Skip ignored elements (by name)
            if element.name in ignore_list:
                _logger.debug(f"Skipping ignored render element: {element.name}")
                continue

            # D10 does NOT skip disabled elements - it sets filenames for ALL elements
            # Users may enable elements later, and V-Ray VFB needs all paths configured

            try:
                # Create unique filename per element: basename_elementname.ext
                purified_name = purify_render_element_name(element.name)
                unique_filename = f"{base_name}_{purified_name}{extension}"
                unique_filepath = os.path.join(base_dir, unique_filename)

                re_manager.SetRenderElementFilename(element.index, unique_filepath)
                # Update in-memory element info for later validation
                element.output_filename = unique_filepath.replace("\\", "/")
                element.has_output_path = True
                filename_set_count += 1
                _logger.debug(f"Set filename for '{element.name}': {unique_filepath}")
            except Exception as e:
                warnings.append(f"Failed to set filename for '{element.name}': {e}")

        # D10: Enable render element output via SetElementsActive(True)
        # This is CRITICAL - without this, render elements won't be saved to files
        try:
            re_manager.SetElementsActive(True)
            _logger.info("Render element manager: SetElementsActive(True)")
        except Exception as e:
            _logger.warning(f"Could not call SetElementsActive: {e}")

        _logger.info(f"Set filenames for {filename_set_count} render elements")
    except Exception as e:
        warnings.append(f"Failed to configure render element filenames: {e}")


def _configure_per_element_settings(
    render_elements: list[RenderElementInfo],
    vfb_control: bool,
    ignore_list: list[str],
    warnings: list[str],
) -> None:
    """
    Configure per-element settings for render elements.

    This function handles enabling/disabling render elements based on VFB control
    and ignore list, and sets the vrayVFB property on each element.

    :param render_elements: list of RenderElementInfo objects
    :param vfb_control: whether VFB control is enabled
    :param ignore_list: list of render element names to ignore
    :param warnings: list to append warning messages to
    """
    enabled_count = 0
    disabled_count = 0

    for element in render_elements:
        element_obj = element.element_object
        if not element_obj:
            continue

        element_name: str = element.name
        should_ignore = element_name in ignore_list

        # Skip Missing_Render_Element_Plug_in
        element_type = str(rt.classof(element_obj))
        if element_type == "Missing_Render_Element_Plug_in":
            continue

        # Automatically enable/disable render elements based on VFB control and ignore list
        if vfb_control:
            try:
                if should_ignore:
                    element_obj.enabled = False
                    element.enabled = False
                    disabled_count += 1
                    _logger.info(f"Disabled render element (ignored): {element_name}")
                else:
                    element_obj.enabled = True
                    element.enabled = True
                    enabled_count += 1
                    _logger.debug(f"Enabled render element: {element_name}")
            except Exception as e:
                warnings.append(f"Failed to set enabled state for '{element_name}': {e}")

        # Configure V-Ray VFB control per element
        if hasattr(element_obj, "vrayVFB"):
            try:
                # Set vrayVFB based on vfb_control setting
                element_obj.vrayVFB = not vfb_control
                _logger.debug(f"Set V-Ray VFB for '{element_name}': {not vfb_control}")
            except Exception as e:
                warnings.append(f"Failed to configure V-Ray VFB for '{element_name}': {e}")

    if vfb_control:
        _logger.info(
            f"V-Ray VFB Control: Enabled {enabled_count} render elements, disabled {disabled_count}"
        )


def _dump_vray_settings_to_file(
    output_path: Optional[str], render_elements: list[RenderElementInfo]
) -> None:
    """
    Dump V-Ray renderer settings to a debug file for troubleshooting.

    This function writes the current V-Ray renderer settings and render element
    configuration to a text file at the output path for debugging purposes.

    :param output_path: output directory path where debug file will be written
    :param render_elements: list of RenderElementInfo objects
    """
    if not output_path:
        _logger.debug("[_dump_vray_settings_to_file] No output path provided, skipping debug dump")
        return

    debug_filepath = os.path.join(output_path, "vray_settings_debug.txt")

    try:
        lines: list[str] = []
        renderer = rt.renderers.current
        renderer_name = str(renderer)

        lines.append("=" * 60)
        lines.append("V-Ray Settings Debug Dump")
        lines.append("=" * 60)
        lines.append(f"Current Renderer: {renderer_name}")
        lines.append(f"Is V-Ray RT (GPU): {_is_vray_rt()}")
        lines.append("")

        vray_settings = [
            "output_on",
            "output_splitgbuffer",
            "output_splitRGB",
            "output_splitAlpha",
            "output_splitfilename",
            "output_splitbitmap",
            "output_saveRawFile",
        ]

        # Dump renderer.current settings
        lines.append("-" * 40)
        lines.append("renderers.current Settings:")
        lines.append("-" * 40)
        for setting in vray_settings:
            try:
                value = getattr(renderer, setting)
                lines.append(f"  {setting}: {value}")
            except Exception as e:
                lines.append(f"  {setting}: <not available> ({e})")

        # Dump vray_rt_settings (GPU) if available
        vray_rt_settings = _get_vray_rt_settings()
        if vray_rt_settings:
            lines.append("")
            lines.append("-" * 40)
            lines.append("V-Ray RT Settings (vray_rt_settings):")
            lines.append("-" * 40)
            for setting in vray_settings:
                try:
                    value = getattr(vray_rt_settings, setting)
                    lines.append(f"  {setting}: {value}")
                except Exception as e:
                    lines.append(f"  {setting}: <not available> ({e})")

        # Render Element Manager
        lines.append("")
        lines.append("-" * 40)
        lines.append("Render Element Manager:")
        lines.append("-" * 40)

        re_manager = rt.maxOps.GetCurRenderElementMgr()
        if re_manager:
            num_elements = re_manager.NumRenderElements()
            lines.append(f"  Number of render elements: {num_elements}")
            try:
                lines.append(f"  Elements active: {re_manager.GetElementsActive()}")
            except Exception:
                lines.append("  Elements active: <not available>")

            lines.append("")
            lines.append("  Render Elements:")
            for element in render_elements:
                element_obj = element.element_object
                vray_vfb = "N/A"
                if element_obj and hasattr(element_obj, "vrayVFB"):
                    try:
                        vray_vfb = element_obj.vrayVFB
                    except Exception:
                        _logger.info(
                            f"Failed to get vrayVFB property for render element: {element.name}"
                        )

                lines.append(f"    [{element.index}] {element.name}")
                lines.append(f"        type: {element.type}")
                lines.append(f"        enabled: {element.enabled}, vrayVFB: {vray_vfb}")
                lines.append(f"        output: {element.output_filename}")
        else:
            lines.append("  No render element manager found")

        lines.append("")
        lines.append("=" * 60)
        lines.append("End of Debug Dump")
        lines.append("=" * 60)

        # Write to file
        with open(debug_filepath, "w") as f:
            f.write("\n".join(lines))

        _logger.info(f"[_dump_vray_settings_to_file] Debug dump written to: {debug_filepath}")

    except Exception as e:
        _logger.warning(f"[_dump_vray_settings_to_file] Failed to write debug dump: {e}")


def configure_vray_render_elements(
    render_elements: list[RenderElementInfo],
    settings: VRayRenderElementSettings,
    output_path: Optional[str] = None,
    output_name: Optional[str] = None,
    output_file_format: str = ".png",
    ignore_list: list[str] = [],
) -> list:
    """
    Configures V-Ray specific render element settings.

    This function handles V-Ray VFB control and split buffer support
    matching Deadline 10's V-Ray integration. The default output file type is PNG for V-Ray,
    in case it is not specified in the bundle. The file format is usually configured from
    the submitter, but the default is useful for any hand-crafted bundles missing the
    file format specification.

    :param render_elements: list of RenderElementInfo objects
    :param settings: V-Ray render element settings
    :param output_path: output directory path for split buffer files
    :param output_name: base output filename for split buffer files
    :param output_file_format: output file format/extension for split buffer files (default: .png)
    :param ignore_list: list of render element names to ignore (disable)
    :returns: list of configuration warnings
    """
    warnings: list[str] = []

    if not render_elements:
        return warnings

    # Check if current renderer matches V-Ray pattern (^V_Ray.*$)
    is_vray, current_renderer = _is_renderer_vray()

    if not is_vray:
        message = f"Skipping V-Ray render element configuration - current renderer '{current_renderer}' does not match V-Ray pattern"
        _logger.info(message)
        warnings.append(message)
        return warnings

    _logger.info(
        f"V-Ray renderer detected: '{current_renderer}' - proceeding with V-Ray configuration"
    )

    vfb_control: bool = settings.vray_render_elements_vfb_control
    split_buffer: bool = settings.vray_split_buffer_support

    try:
        # Configure global V-Ray VFB control if enabled
        if vfb_control:
            _set_vray_property("output_on", False, warnings)
            _logger.info(
                "Disabled V-Ray VFB (output_on = False) - render elements will use 3ds Max framebuffer"
            )

        # Configure split buffer if enabled
        base_filepath: Optional[str] = None
        if split_buffer:
            base_filepath = _configure_split_buffer_settings(
                output_path, output_name, output_file_format, warnings
            )
        elif output_path and output_name:
            # Build base_filepath without configuring split buffer
            base_name, _ = os.path.splitext(output_name)
            extension = (
                output_file_format
                if output_file_format and output_file_format.startswith(".")
                else f".{output_file_format}" if output_file_format else ".png"
            )
            base_filepath = os.path.join(output_path, f"{base_name}{extension}")

        # Configure render element filenames
        _configure_render_element_filenames(render_elements, base_filepath, ignore_list, warnings)

        # Configure per-element settings
        _configure_per_element_settings(render_elements, vfb_control, ignore_list, warnings)

    except Exception as e:
        _logger.error(f"Error configuring V-Ray render elements: {e}")
        warnings.append(f"V-Ray configuration failed: {e}")

    # Dump V-Ray settings to debug file at output path
    _dump_vray_settings_to_file(output_path, render_elements)

    return warnings


def store_original_render_element_state(
    render_elements: list[RenderElementInfo],
) -> RenderElementState:
    """
    Stores original render element state for later restoration.

    This function captures the current state of render elements
    to enable restoration after rendering completes.

    :param render_elements: list of RenderElementInfo objects
    :returns: RenderElementState object containing original state information
    """
    original_state = RenderElementState()

    try:
        re_manager = rt.maxOps.GetCurRenderElementMgr()
        if not re_manager:
            return original_state

        for element in render_elements:
            element_index: int = element.index
            element_obj = element.element_object

            if element_index < 0:
                continue

            # Store original names and paths
            original_state.element_names.append(element.name)
            original_state.element_paths.append(element.output_filename)
            original_state.element_enabled.append(element.enabled)

            # Store V-Ray VFB states
            if element_obj and hasattr(element_obj, "vrayVFB"):
                try:
                    original_state.vray_vfb_states.append(bool(element_obj.vrayVFB))
                except Exception:
                    original_state.vray_vfb_states.append(False)
            else:
                original_state.vray_vfb_states.append(False)

    except Exception as e:
        _logger.error(f"Error storing original render element state: {e}")

    return original_state


def restore_original_render_element_state(original_state: RenderElementState) -> list:
    """
    Restores original render element state.

    This function restores render elements to their original state
    using previously stored state information.

    :param original_state: RenderElementState object containing original state information
    :returns: list of restoration warnings
    """
    warnings: list[str] = []

    if not original_state:
        return warnings

    try:
        re_manager = rt.maxOps.GetCurRenderElementMgr()
        if not re_manager:
            warnings.append("No render element manager found for restoration")
            return warnings

        render_elements: list[RenderElementInfo] = get_render_elements()

        for i, element in enumerate(render_elements):
            element_index: int = element.index
            element_obj = element.element_object

            if element_index < 0 or i >= len(original_state.element_paths):
                continue

            # Restore original paths
            try:
                original_path: str = original_state.element_paths[i]
                if original_path:
                    re_manager.SetRenderElementFilename(element_index, original_path)
            except Exception as e:
                warnings.append(f"Failed to restore path for render element {i}: {e}")

            # Restore V-Ray VFB states
            if (
                element_obj
                and hasattr(element_obj, "vrayVFB")
                and i < len(original_state.vray_vfb_states)
            ):
                try:
                    element_obj.vrayVFB = original_state.vray_vfb_states[i]
                except Exception as e:
                    warnings.append(
                        f"Failed to restore V-Ray VFB state for render element {i}: {e}"
                    )

    except Exception as e:
        _logger.error(f"Error restoring original render element state: {e}")
        warnings.append(f"State restoration failed: {e}")

    return warnings


def _configure_render_element_outputs_filename(
    render_elements: list[RenderElementInfo],
    output_path: Optional[str] = None,
    output_name: Optional[str] = None,
    output_file_format: Optional[str] = ".exr",
    ignore_list: list[str] = [],
) -> list[str]:
    """
    Configure output filenames for standard (non-V-Ray) render elements.

    This function sets unique output filenames for each enabled render element
    using standard 3ds Max naming conventions. The default output file type is EXR,
    in case it is not specified in the bundle. The file format is usually configured from
    the submitter, but the default is useful for any hand-crafted bundles missing the
    file format specification.


    :param render_elements: list of RenderElementInfo objects
    :param output_path: base output directory path
    :param output_name: base output filename
    :param output_file_format: output file format/extension
    :param ignore_list: list of render element names to skip
    :returns: list of configuration warnings
    """
    warnings: list[str] = []

    if not render_elements:
        return warnings

    if not (output_path and output_name):
        warnings.append(
            "Standard render element filename configuration skipped: Missing output path or name"
        )
        return warnings

    try:
        re_manager = rt.maxOps.GetCurRenderElementMgr()
        if not re_manager:
            warnings.append(
                "Standard render element filename configuration failed: No render element manager"
            )
            return warnings

        # Prepare base filename without extension
        base_filename, _ = os.path.splitext(output_name)

        filename_set_count = 0
        for element in render_elements:
            if not element.enabled or element.name in ignore_list:
                continue

            try:
                # Create unique filename: basename_elementname.ext
                purified_element_name = purify_render_element_name(element.name)
                assert output_file_format is not None  # Should never be None due to default value
                extension = (
                    output_file_format
                    if output_file_format.startswith(".")
                    else f".{output_file_format}"
                )
                unique_filename = f"{base_filename}_{purified_element_name}{extension}"
                full_path = os.path.join(output_path, unique_filename)

                # Set the render element filename
                re_manager.SetRenderElementFilename(element.index, full_path)
                # Update the RenderElementInfo object so validation uses the correct path
                element.output_filename = full_path
                element.has_output_path = True
                filename_set_count += 1
                _logger.debug(
                    f"Set standard render element filename for '{element.name}': {full_path}"
                )

            except Exception as e:
                warnings.append(f"Failed to set filename for render element '{element.name}': {e}")

        _logger.info(
            f"Standard render elements: Set unique filenames for {filename_set_count} render elements"
        )

    except Exception as e:
        _logger.error(f"Error configuring standard render element filenames: {e}")
        warnings.append(f"Standard render element filename configuration failed: {e}")

    return warnings


def _is_renderer_vray() -> tuple[bool, str]:
    """
    Check if the current renderer is V-Ray.

    This is a private helper function that checks if the current renderer
    matches the V-Ray pattern used throughout the Deadline integration.

    :returns: tuple of (is_vray, renderer_name)
    """
    try:
        current_renderer = str(rt.renderers.current)
        vray_pattern = r"^V_Ray.*$"
        is_vray = bool(re.match(vray_pattern, current_renderer))
        return is_vray, current_renderer
    except Exception as e:
        _logger.error(f"Failed to check current renderer: {e}")
        return False, "Unknown"


def _build_render_element_path(
    base_path: str,
    element_name: str,
    element_type: str,
    settings: RenderElementConfigurationSettings,
) -> str:
    """
    Builds render element path based on naming settings.

    This is a private helper function that constructs the final path
    based on Deadline 10's path building logic.

    :param base_path: original base path
    :param element_name: render element name
    :param element_type: render element type
    :param settings: render element configuration settings
    :returns: constructed path
    """
    try:
        path_obj: Path = Path(base_path)
        directory: Path = path_obj.parent
        filename: str = path_obj.stem
        extension: str = path_obj.suffix

        # Build directory path modifications
        if settings.render_elements_include_name_in_path:
            purified_name: str = purify_render_element_name(element_name)
            directory = directory / purified_name

        if settings.render_elements_include_type_in_path:
            purified_type: str = purify_render_element_name(element_type)
            directory = directory / purified_type

        # Build filename modifications
        if settings.render_elements_include_name_in_filename:
            purified_name = purify_render_element_name(element_name)
            filename = f"{filename}_{purified_name}"

        if settings.render_elements_include_type_in_filename:
            purified_type = purify_render_element_name(element_type)
            filename = f"{filename}_{purified_type}"

        # Construct final path
        final_path: Path = directory / f"{filename}{extension}"
        return str(final_path).replace("\\", "/")

    except Exception as e:
        _logger.error(f"Error building render element path: {e}")
        return base_path


class MissingRenderElementInfo(TypedDict):
    """Type definition for missing render element information."""

    index: int
    name: str
    type: str
    enabled: bool
    original_class: str


def detect_missing_render_elements() -> list[MissingRenderElementInfo]:
    """
    Detects missing render element plugins in the scene.

    This function identifies render elements that reference missing plugins,
    matching Deadline 10's missing element detection system.

    :returns: list of typed dictionaries containing missing element information
    """
    missing_elements: list[MissingRenderElementInfo] = []

    try:
        re_manager = rt.maxOps.GetCurRenderElementMgr()
        if not re_manager:
            return missing_elements

        for i in range(re_manager.NumRenderElements()):
            element = re_manager.GetRenderElement(i)
            if not element:
                continue

            # Check for Missing_Render_Element_Plug_in
            if rt.classof(element) == rt.Missing_Render_Element_Plug_in:
                missing_info: MissingRenderElementInfo = {
                    "index": i,
                    "name": f"Missing_Element_{i}",
                    "type": "Missing_Render_Element_Plug_in",
                    "enabled": bool(getattr(element, "enabled", True)),
                    "original_class": getattr(element, "originalClassName", "Unknown"),
                }
                missing_elements.append(missing_info)
                _logger.warning(f"Found missing render element plugin at index {i}")

    except Exception as e:
        _logger.error(f"Error detecting missing render elements: {e}")

    return missing_elements


def validate_render_element_names(render_elements: list[RenderElementInfo]) -> list[str]:
    """
    Validates render element names for duplicates and invalid characters.

    This function provides comprehensive name validation matching Deadline 10's
    render element name checking system.

    :param render_elements: list of RenderElementInfo objects
    :returns: list of validation warnings
    """
    warnings: list[str] = []

    if not render_elements:
        return warnings

    element_names: list[str] = []

    for element in render_elements:
        element_name: str = element.name
        element_index: int = element.index

        # Check for empty names
        if not element_name or element_name.strip() == "":
            warnings.append(f"Render element at index {element_index} has empty name")
            continue

        # Check for duplicate names
        if element_name in element_names:
            warnings.append(f"Duplicate render element name found: '{element_name}'")
        else:
            element_names.append(element_name)

        # Check for invalid characters
        invalid_chars: list[str] = ["<", ">", ":", '"', "|", "?", "*", "/", "\\"]
        found_invalid: list[str] = [char for char in invalid_chars if char in element_name]
        if found_invalid:
            warnings.append(
                f"Render element '{element_name}' contains invalid characters: {', '.join(found_invalid)}"
            )

        # Check for names that are too long (Windows path limit consideration)
        if len(element_name) > 100:
            warnings.append(
                f"Render element name '{element_name}' is too long ({len(element_name)} characters)"
            )

    return warnings
