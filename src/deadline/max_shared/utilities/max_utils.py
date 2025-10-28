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


def get_render_elements() -> list[RenderElementInfo]:
    """
    Gets all render elements present in the max scene with their properties.

    This function provides render element detection that matches
    Deadline 10's functionality, including V-Ray VFB detection and element
    index tracking for later manipulation.

    :returns: a list of RenderElementInfo objects containing render element information
    :return_type: list[RenderElementInfo]
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
    :type render_elements: list[RenderElementInfo]
    :returns: list of warning messages for render elements with path issues
    :return_type: list[str]
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
    :return_type: set[str]
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
    :type element_name: str
    :returns: purified element name safe for file paths
    :return_type: str
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


def get_render_element_by_name(element_name: str) -> Optional[RenderElementInfo]:
    """
    Gets a specific render element by name.

    :param element_name: name of the render element to find
    :type element_name: str
    :returns: RenderElementInfo object or None if not found
    :return_type: RenderElementInfo or None
    """
    render_elements: list[RenderElementInfo] = get_render_elements()

    for element in render_elements:
        if element.name == element_name:
            return element

    return None


def validate_render_element_configuration(
    render_elements: list[RenderElementInfo], settings: RenderElementConfigurationSettings
) -> list[str]:
    """
    Validates render element configuration against settings.

    This function provides comprehensive validation of render element settings
    to ensure consistency between GUI configuration and render execution.

    :param render_elements: list of RenderElementInfo objects
    :type render_elements: list[RenderElementInfo]
    :param settings: render element configuration settings
    :type settings: RenderElementConfigurationSettings
    :returns: list of validation warnings
    :return_type: list[str]
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
    :type render_elements: list[RenderElementInfo]
    :param settings: render element configuration settings
    :type settings: RenderElementConfigurationSettings
    :returns: list of configuration warnings
    :return_type: list[str]
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
                _logger.debug(f"Updated render element '{element_name}' path to: {new_path}")
            except Exception as e:
                warnings.append(f"Failed to update path for render element '{element_name}': {e}")

    except Exception as e:
        _logger.error(f"Error configuring render element paths: {e}")
        warnings.append(f"Path configuration failed: {e}")

    return warnings


def configure_vray_render_elements(
    render_elements: list[RenderElementInfo],
    settings: VRayRenderElementSettings,
    output_path: Optional[str] = None,
    output_name: Optional[str] = None,
    output_file_format: Optional[str] = ".png",
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
    :type render_elements: list[RenderElementInfo]
    :param settings: V-Ray render element settings
    :type settings: VRayRenderElementSettings
    :param output_path: output directory path for split buffer files
    :type output_path: str
    :param output_name: base output filename for split buffer files
    :type output_name: str
    :param output_file_format: output file format/extension for split buffer files (default: .png)
    :type output_file_format: str
    :param ignore_list: list of render element names to ignore (disable)
    :type ignore_list: list[str]
    :returns: list of configuration warnings
    :return_type: list[str]
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
            try:
                rt.renderers.current.output_on = False
                _logger.info(
                    "Disabled V-Ray VFB (output_on = False) - render elements will use 3ds Max framebuffer"
                )
            except Exception as e:
                warnings.append(f"Failed to configure global V-Ray VFB control: {e}")

        # Configure split buffer if enabled
        if split_buffer:
            try:
                rt.renderers.current.output_splitgbuffer = True

                # Set the base filename for split files (critical for split buffer to work)
                if output_path and output_name:
                    # Prepare base filename with format extension
                    base_name, _ = os.path.splitext(output_name)
                    assert (
                        output_file_format is not None
                    )  # Should never be None due to default value
                    extension = (
                        output_file_format
                        if output_file_format.startswith(".")
                        else f".{output_file_format}"
                    )
                    filename_with_format = f"{base_name}{extension}"
                    base_filepath = os.path.join(output_path, filename_with_format)
                    rt.renderers.current.output_splitfilename = base_filepath
                    _logger.info(f"V-Ray split buffer filename set to: {base_filepath}")
                else:
                    missing_params = []
                    if not output_path:
                        missing_params.append("output_file_path")
                    if not output_name:
                        missing_params.append("output_file_name (check template has this defined)")
                    warnings.append(
                        f"Split buffer enabled but missing: {', '.join(missing_params)} - split files may not save correctly"
                    )

                rt.renderers.current.output_splitRGB = True
                rt.renderers.current.output_splitAlpha = True

                _logger.info("V-Ray split buffer configured")
            except Exception as e:
                warnings.append(f"Failed to configure V-Ray split buffer: {e}")

        # Configure split buffer filenames - set same base filename for all render elements
        if split_buffer:
            try:
                re_manager = rt.maxOps.GetCurRenderElementMgr()
                if re_manager and output_path and output_name:
                    # Prepare base filename with format extension
                    base_name, _ = os.path.splitext(output_name)
                    assert (
                        output_file_format is not None
                    )  # Should never be None due to default value
                    extension = (
                        output_file_format
                        if output_file_format.startswith(".")
                        else f".{output_file_format}"
                    )
                    filename_with_format = f"{base_name}{extension}"
                    base_filename = os.path.join(output_path, filename_with_format)

                    # Set the SAME base filename for ALL enabled render elements
                    # V-Ray VFB will automatically append layer names during rendering
                    filename_set_count = 0
                    for element in render_elements:
                        if element.enabled and element.name not in ignore_list:
                            try:
                                re_manager.SetRenderElementFilename(element.index, base_filename)
                                filename_set_count += 1
                                _logger.debug(
                                    f"Set V-Ray split buffer base filename for '{element.name}': {base_filename}"
                                )
                            except Exception as e:
                                warnings.append(
                                    f"Failed to set split buffer filename for '{element.name}': {e}"
                                )

                    _logger.info(
                        f"V-Ray split buffer: Set base filename for {filename_set_count} render elements"
                    )
                else:
                    if not re_manager:
                        warnings.append(
                            "V-Ray split buffer filename setup failed: No render element manager"
                        )
                    if not (output_path and output_name):
                        warnings.append(
                            "V-Ray split buffer filename setup skipped: Missing output path or name"
                        )
            except Exception as e:
                warnings.append(f"Failed to configure V-Ray split buffer filenames: {e}")

        # Configure per-element settings
        enabled_count = 0
        disabled_count = 0

        for element in render_elements:
            element_obj = element.element_object
            if not element_obj:
                continue

            element_name: str = element.name
            should_ignore = element_name in ignore_list

            # Skip V-Ray VFB specific elements (matching Deadline 10 pattern)
            element_type = str(rt.classof(element_obj))
            if element_type in ["VRayOptionRE", "VRayAlpha"]:
                _logger.debug(f"Skipping V-Ray VFB element: {element_name} ({element_type})")
                continue

            # Automatically enable/disable render elements based on VFB control and ignore list
            if vfb_control:
                try:
                    if should_ignore:
                        element_obj.enabled = False
                        # Also update our wrapper to keep it in sync
                        element.enabled = False
                        disabled_count += 1
                        _logger.info(f"Disabled render element (ignored): {element_name}")
                    else:
                        element_obj.enabled = True
                        # Also update our wrapper to keep it in sync
                        element.enabled = True
                        enabled_count += 1
                        _logger.debug(f"Enabled render element: {element_name}")
                except Exception as e:
                    warnings.append(f"Failed to set enabled state for '{element_name}': {e}")

            # Configure V-Ray VFB control per element
            if hasattr(element_obj, "vrayVFB"):
                try:
                    # Disable VFB for render elements when VFB control is enabled
                    element_obj.vrayVFB = not vfb_control
                    _logger.debug(f"Set V-Ray VFB for '{element_name}': {not vfb_control}")
                except Exception as e:
                    warnings.append(f"Failed to configure V-Ray VFB for '{element_name}': {e}")

        # Log summary of enabled/disabled elements
        if vfb_control:
            _logger.info(
                f"V-Ray VFB Control: Enabled {enabled_count} render elements, disabled {disabled_count}"
            )

    except Exception as e:
        _logger.error(f"Error configuring V-Ray render elements: {e}")
        warnings.append(f"V-Ray configuration failed: {e}")

    return warnings


def store_original_render_element_state(
    render_elements: list[RenderElementInfo],
) -> RenderElementState:
    """
    Stores original render element state for later restoration.

    This function captures the current state of render elements
    to enable restoration after rendering completes.

    :param render_elements: list of RenderElementInfo objects
    :type render_elements: list[RenderElementInfo]
    :returns: RenderElementState object containing original state information
    :return_type: RenderElementState
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
    :type original_state: RenderElementState
    :returns: list of restoration warnings
    :return_type: list[str]
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
    :return_type: tuple[bool, str]
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
    :type base_path: str
    :param element_name: render element name
    :type element_name: str
    :param element_type: render element type
    :type element_type: str
    :param settings: render element configuration settings
    :type settings: RenderElementConfigurationSettings
    :returns: constructed path
    :return_type: str
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
    :return_type: list[MissingRenderElementInfo]
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
    :type render_elements: list[RenderElementInfo]
    :returns: list of validation warnings
    :return_type: list[str]
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


def resolve_duplicate_render_element_names(render_elements: list[RenderElementInfo]) -> dict:
    """
    Resolves duplicate render element names by suggesting unique alternatives.

    This function provides name resolution suggestions matching Deadline 10's
    duplicate name handling system.

    :param render_elements: list of RenderElementInfo objects
    :type render_elements: list[RenderElementInfo]
    :returns: dictionary mapping original names to suggested unique names
    :return_type: dict[str, str]
    """
    name_resolutions: dict[str, str] = {}
    name_counts: dict[str, int] = {}

    # Count occurrences of each name
    for element in render_elements:
        element_name: str = element.name
        if element_name:
            name_counts[element_name] = name_counts.get(element_name, 0) + 1

    # Generate unique names for duplicates
    name_counters: dict[str, int] = {}
    for element in render_elements:
        element_name = element.name
        if not element_name:
            continue

        # If name appears multiple times, generate unique variant
        if name_counts[element_name] > 1:
            counter: int = name_counters.get(element_name, 0) + 1
            name_counters[element_name] = counter

            if counter == 1:
                # First occurrence keeps original name
                continue
            else:
                # Subsequent occurrences get numbered suffix
                unique_name: str = f"{element_name}_{counter}"
                name_resolutions[element_name] = unique_name

    return name_resolutions


def preview_render_element_paths(
    render_elements: list[RenderElementInfo], settings: RenderElementConfigurationSettings
) -> dict:
    """
    Previews render element output paths based on current settings.

    This function generates path previews without modifying the scene,
    matching Deadline 10's path preview functionality.

    :param render_elements: list of RenderElementInfo objects
    :type render_elements: list[RenderElementInfo]
    :param settings: render element configuration settings
    :type settings: RenderElementConfigurationSettings
    :returns: dictionary mapping element names to preview paths
    :return_type: dict[str, str]
    """
    path_previews: dict[str, str] = {}

    if not render_elements or not settings.render_elements_update_paths:
        return path_previews

    try:
        for element in render_elements:
            element_name: str = element.name
            element_type: str = element.type
            base_path: str = element.output_filename

            if not element_name or not base_path:
                continue

            # Generate preview path using the same logic as actual path building
            preview_path: str = _build_render_element_path(
                base_path, element_name, element_type, settings
            )

            path_previews[element_name] = preview_path

    except Exception as e:
        _logger.error(f"Error generating render element path previews: {e}")

    return path_previews


class RenderElementCompatibilityAnalysis(TypedDict):
    """Type definition for render element compatibility analysis results."""

    total_elements: int
    vray_elements: int
    corona_elements: int
    arnold_elements: int
    mental_ray_elements: int
    standard_elements: int
    unknown_elements: int
    compatibility_warnings: list[str]


def analyze_render_element_compatibility(
    render_elements: list[RenderElementInfo],
) -> RenderElementCompatibilityAnalysis:
    """
    Analyzes render element compatibility with different renderers.

    This function provides compatibility analysis matching Deadline 10's
    renderer-specific render element validation.

    :param render_elements: list of RenderElementInfo objects
    :type render_elements: list[RenderElementInfo]
    :returns: typed dictionary containing compatibility analysis
    :return_type: RenderElementCompatibilityAnalysis
    """
    analysis: RenderElementCompatibilityAnalysis = {
        "total_elements": len(render_elements),
        "vray_elements": 0,
        "corona_elements": 0,
        "arnold_elements": 0,
        "mental_ray_elements": 0,
        "standard_elements": 0,
        "unknown_elements": 0,
        "compatibility_warnings": [],
    }

    try:
        # Get current renderer
        current_renderer: str = str(rt.renderers.current)

        for element in render_elements:
            element_type: str = element.type.lower()
            element_name: str = element.name

            # Categorize by renderer type
            if "vray" in element_type:
                analysis["vray_elements"] += 1
                if "vray" not in current_renderer.lower():
                    analysis["compatibility_warnings"].append(
                        f"V-Ray render element '{element_name}' may not work with current renderer: {current_renderer}"
                    )
            elif "corona" in element_type:
                analysis["corona_elements"] += 1
                if "corona" not in current_renderer.lower():
                    analysis["compatibility_warnings"].append(
                        f"Corona render element '{element_name}' may not work with current renderer: {current_renderer}"
                    )
            elif "arnold" in element_type or "ai" in element_type:
                analysis["arnold_elements"] += 1
                if "arnold" not in current_renderer.lower():
                    analysis["compatibility_warnings"].append(
                        f"Arnold render element '{element_name}' may not work with current renderer: {current_renderer}"
                    )
            elif "mental" in element_type or "mr" in element_type:
                analysis["mental_ray_elements"] += 1
            elif any(std in element_type for std in ["beauty", "alpha", "z", "material"]):
                analysis["standard_elements"] += 1
            else:
                analysis["unknown_elements"] += 1

        _logger.debug(f"Render element compatibility analysis completed: {analysis}")

    except Exception as e:
        _logger.error(f"Error analyzing render element compatibility: {e}")
        analysis["compatibility_warnings"].append(f"Compatibility analysis failed: {e}")

    return analysis


class RenderElementStatistics(TypedDict):
    """Type definition for render element statistics results."""

    total_elements: int
    enabled_elements: int
    disabled_elements: int
    elements_with_paths: int
    elements_without_paths: int
    vray_vfb_enabled: int
    missing_elements: int
    unique_output_directories: int
    duplicate_names: int
    name_validation_issues: int


def get_render_element_statistics() -> RenderElementStatistics:
    """
    Gets comprehensive statistics about render elements in the scene.

    This function provides detailed statistics matching Deadline 10's
    render element reporting system.

    :returns: typed dictionary containing render element statistics
    :return_type: RenderElementStatistics
    """
    stats: RenderElementStatistics = {
        "total_elements": 0,
        "enabled_elements": 0,
        "disabled_elements": 0,
        "elements_with_paths": 0,
        "elements_without_paths": 0,
        "vray_vfb_enabled": 0,
        "missing_elements": 0,
        "unique_output_directories": 0,
        "duplicate_names": 0,
        "name_validation_issues": 0,
    }

    try:
        render_elements: list[RenderElementInfo] = get_render_elements()
        missing_elements: list[MissingRenderElementInfo] = detect_missing_render_elements()
        name_warnings: list[str] = validate_render_element_names(render_elements)
        output_dirs: set[str] = get_render_elements_output_directories()

        stats["total_elements"] = len(render_elements)
        stats["missing_elements"] = len(missing_elements)
        stats["unique_output_directories"] = len(output_dirs)
        stats["name_validation_issues"] = len(name_warnings)

        # Count duplicate names
        element_names: list[str] = [elem.name for elem in render_elements]
        stats["duplicate_names"] = len(element_names) - len(set(element_names))

        for element in render_elements:
            if element.enabled:
                stats["enabled_elements"] += 1
            else:
                stats["disabled_elements"] += 1

            if element.has_output_path:
                stats["elements_with_paths"] += 1
            else:
                stats["elements_without_paths"] += 1

            if element.vray_vfb:
                stats["vray_vfb_enabled"] += 1

        _logger.info(f"Render element statistics: {stats}")

    except Exception as e:
        _logger.error(f"Error getting render element statistics: {e}")

    return stats
