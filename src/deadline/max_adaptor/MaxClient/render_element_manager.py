"""
3ds Max Deadline Cloud Adaptor - Render Element Manager

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pymxs  # noqa
from pymxs import runtime as rt

# Import shared utilities for consistent behavior with submitter
from deadline.max_shared.utilities.max_utils import (
    RenderElementConfigurationSettings,
    RenderElementInfo,
    RenderElementState,
    VRayRenderElementSettings,
    _configure_render_element_outputs_filename,
    _is_renderer_vray,
    configure_render_element_paths,
    configure_vray_render_elements,
    get_render_elements,
    restore_original_render_element_state,
    store_original_render_element_state,
    validate_render_element_configuration,
)

logger = logging.getLogger(__name__)


@dataclass
class RenderElementResult:
    """
    Structured result for render element operations.

    Attributes:
        success: Whether the operation succeeded
        message: Success message (when success=True)
        warnings: List of warning messages (optional)
        error: Error message (when success=False)
        element_count: Number of render elements processed (optional)
    """

    success: bool
    message: Optional[str] = None
    warnings: Optional[List[str]] = None
    error: Optional[str] = None
    element_count: Optional[int] = None

    def __post_init__(self):
        """Validate that either message or error is provided based on success status."""
        if self.success and not self.message:
            self.message = "Operation completed successfully"
        elif not self.success and not self.error:
            self.error = "Unknown error occurred"


class RenderElementManager:
    """
    Render element management using pymxs (based on Deadline 10's system).

    This class handles all render element configuration during rendering, including:
    - Basic render element enable/disable
    - Ignore settings (all elements or by name)
    - Path and filename updates with naming patterns
    - V-Ray VFB integration and split buffer support
    - Original state storage and restoration
    """

    def __init__(
        self,
        output_file_path: Optional[str] = None,
        output_file_name: Optional[str] = None,
        output_file_format: Optional[str] = None,
    ) -> None:
        """
        Initialize the render element manager.

        If any of the output_file_* parameters are None, they will default to the current
        settings of the render element in the scene. Note that paths may not be path mapped
        in this case. By default, the submitter always populates these values based on the scene.

        Args:
            output_file_path: Output directory path for split buffer
            output_file_name: Output filename for split buffer
            output_file_format: Output file format/extension
        """
        self.logger = logging.getLogger(__name__)
        self.re_manager: Optional[Any] = None
        self.original_state: Optional[RenderElementState] = None
        self.cached_settings: Dict[str, Any] = {}
        self.is_configured = False
        self.output_file_path: Optional[str] = output_file_path
        self.output_file_name: Optional[str] = output_file_name
        self.output_file_format: Optional[str] = output_file_format
        self.is_vray: bool = False
        self.current_renderer: str = ""

    def _print_render_element_debug_info(self, render_elements: List[RenderElementInfo]) -> None:
        """
        Print debug information about render element manager and render elements.

        Args:
            render_elements: List of render elements to debug
        """
        # DEBUG: Print render element manager's available functions
        self.logger.debug("=== DEBUG: Printing render element manager functions ===")
        re_manager_props = [prop for prop in dir(self.re_manager) if not prop.startswith("_")]
        self.logger.debug(f"DEBUG: re_manager type: {type(self.re_manager)}")
        self.logger.debug(f"DEBUG: re_manager props: {re_manager_props}")

        # DEBUG: Loop through all render elements and print available functions for element_object
        self.logger.debug(
            "=== DEBUG: Printing element_object functions for all render elements ==="
        )
        for i, element in enumerate(render_elements):
            element_obj = element.element_object
            if element_obj:
                element_obj_props = [
                    props for props in dir(element_obj) if not props.startswith("_")
                ]
                self.logger.debug(
                    f"DEBUG: Element [{i}] '{element.name}' - element_object props: {element_obj_props}"
                )
            else:
                self.logger.debug(f"DEBUG: Element [{i}] '{element.name}' - element_object is None")

    def configure_render_elements(self, data: Dict[str, Any]) -> RenderElementResult:
        """
        Comprehensive render element configuration matching Deadline 10.

        Args:
            data: Dictionary containing render element configuration parameters

        Returns:
            RenderElementResult with success status and any messages/errors
        """
        try:
            # Add explicit logging that should definitely appear
            print("=== RENDER ELEMENT MANAGER: Starting configuration ===", flush=True)
            try:
                pymxs.runtime.logsystem.logEntry(
                    "=== RENDER ELEMENT MANAGER: Starting configuration ===", broadcast=True
                )
            except Exception:
                pass

            self.logger.info("Starting render elements configuration")
            self.logger.info(f"Received configuration data: {data}")

            # Cache the settings for later use
            self.cached_settings = data.copy()
            self.is_configured = True

            # Get render element manager
            self.re_manager = rt.maxOps.GetCurRenderElementMgr()
            if not self.re_manager:
                raise Exception("Failed to get render element manager")

            # At this point, re_manager is guaranteed to be not None
            assert self.re_manager is not None

            # Get current render elements from scene
            render_elements = get_render_elements()
            if not render_elements:
                self.logger.info("No render elements found in scene")
                return RenderElementResult(success=True, message="No render elements to configure")

            # Print debug information about render elements
            self._print_render_element_debug_info(render_elements)

            self.logger.info(f"Found {len(render_elements)} render elements in scene:")
            for i, element in enumerate(render_elements):
                self.logger.info(
                    f"  [{i}] {element.name} - Type: {element.type} - Enabled: {element.enabled} - Output: {element.output_filename or 'None'}"
                )

            # Store original state for restoration
            self.original_state = store_original_render_element_state(render_elements)
            self.logger.debug(f"Stored original state for {len(render_elements)} render elements")

            # Parse ignore list once for all operations
            ignore_list = self._get_ignore_list(data)
            if ignore_list:
                self.logger.info(f"Ignoring render elements by name: {ignore_list}")

            # Configure render elements active state
            elements_enabled = self._configure_render_elements_active(data)

            # Log all render element parameters received
            self.logger.info("Render element configuration parameters:")
            for key, value in data.items():
                if key.lower().startswith(("render_element", "vray", "ignore")):
                    self.logger.info(f"  {key}: {value}")

            if not elements_enabled:
                self.logger.info("Render elements disabled, skipping further configuration")
                return RenderElementResult(success=True, message="Render elements disabled")

            # Handle ignore settings
            self._handle_ignore_settings(data, render_elements, ignore_list)

            # Detect renderer type and store as attributes
            self.is_vray, self.current_renderer = _is_renderer_vray()
            self.logger.info(
                f"Detected renderer: '{self.current_renderer}' (V-Ray: {self.is_vray})"
            )

            # Configure render element outputs based on renderer type
            if self.is_vray:
                # Handle V-Ray specific settings
                self._configure_vray_settings(data, render_elements, ignore_list)
            else:
                # Configure standard render element outputs for non-VRay renderers
                self.logger.info(
                    f"Configuring standard render element outputs for '{self.current_renderer}'"
                )

                # Configure standard render element outputs
                warnings = _configure_render_element_outputs_filename(
                    render_elements,
                    self.output_file_path,
                    self.output_file_name,
                    self.output_file_format,
                    ignore_list,
                )
                if warnings:
                    for warning in warnings:
                        self.logger.warning(f"Standard render element configuration: {warning}")

            # Validate final configuration
            settings = self._convert_data_to_settings(data)
            validation_warnings = validate_render_element_configuration(render_elements, settings)
            if validation_warnings:
                for warning in validation_warnings:
                    self.logger.warning(f"Configuration validation: {warning}")

            self.logger.info("Render elements configuration completed successfully")

            # Add explicit success logging
            print(
                "=== RENDER ELEMENT MANAGER: Configuration completed successfully ===", flush=True
            )
            try:
                pymxs.runtime.logsystem.logEntry(
                    "=== RENDER ELEMENT MANAGER: Configuration completed successfully ===",
                    broadcast=True,
                )
            except Exception as e:
                self.logger.error(f"Failed to log success message to 3ds Max: {e}")

            return RenderElementResult(
                success=True,
                message="Render elements configured successfully",
                warnings=validation_warnings if validation_warnings else None,
                element_count=len(render_elements),
            )

        except Exception as e:
            # Add explicit error logging
            print(f"=== RENDER ELEMENT MANAGER: Configuration failed: {e} ===", flush=True)
            try:
                pymxs.runtime.logsystem.logEntry(
                    f"=== RENDER ELEMENT MANAGER: Configuration failed: {e} ===", broadcast=True
                )
            except Exception:
                pass

            self.logger.error(f"Failed to configure render elements: {e}")
            return RenderElementResult(success=False, error=str(e))

    def _configure_render_elements_active(self, data: Dict[str, Any]) -> bool:
        """
        Configure render elements active state.

        Args:
            data: Configuration parameters

        Returns:
            bool: True if render elements should be enabled, False otherwise
        """
        elements_enabled = (
            self._get_param_value(data, ["render_elements"], "true").lower() == "true"
        )
        self.logger.info(f"Setting render elements active: {elements_enabled}")

        # Set render elements active
        assert self.re_manager is not None, "Render element manager must be initialized"
        try:
            self.re_manager.SetElementsActive(elements_enabled)
        except Exception as e:
            self.logger.error(f"Failed to set render elements active state: {e}")
            # Continue execution as this might not be critical

        return elements_enabled

    def _handle_ignore_settings(
        self, data: Dict[str, Any], render_elements: List[RenderElementInfo], ignore_list: List[str]
    ) -> None:
        """
        Handle render element ignore settings.

        Args:
            data: Configuration parameters
            render_elements: List of render elements from scene
        """
        # Handle ignore by name list
        if ignore_list:
            disabled_count = 0
            for element in render_elements:
                element_name = element.name
                if element_name in ignore_list:
                    try:
                        # Disable the render element using the underlying pymxs object
                        element_obj = element.element_object
                        if element_obj and hasattr(element_obj, "enabled"):
                            element_obj.enabled = False
                            # Also update our wrapper to keep it in sync
                            element.enabled = False
                            self.logger.debug(
                                f"Successfully disabled pymxs object for '{element_name}' - element_obj.enabled = False"
                            )
                        else:
                            # Fallback: just update our wrapper
                            element.enabled = False
                            self.logger.debug(
                                f"Fallback: only disabled wrapper for '{element_name}' - element_obj not available or no enabled property"
                            )

                        self.logger.info(
                            f"DISABLED render element: '{element_name}' (index {element.index})"
                        )
                        disabled_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to disable render element '{element_name}': {e}")

            self.logger.info(f"Disabled {disabled_count} render elements based on ignore list")

    def _update_paths_and_filenames(
        self, data: Dict[str, Any], render_elements: List[RenderElementInfo]
    ) -> None:
        """
        Update render element paths and filenames based on configuration.

        Args:
            data: Configuration parameters
            render_elements: List of render elements from scene
        """
        # Check if path updates are requested
        update_paths = (
            self._get_param_value(data, ["render_elements_update_paths"], "true").lower() == "true"
        )
        if not update_paths:
            return

        try:
            self.logger.info("Updating render element paths and filenames")

            # Configure paths using shared utilities
            settings = self._convert_data_to_settings(data)
            path_warnings = configure_render_element_paths(render_elements, settings)
            if path_warnings:
                for warning in path_warnings:
                    self.logger.warning(f"Path configuration: {warning}")

        except Exception as e:
            self.logger.error(f"Failed to update render element paths: {e}")
            raise

    def _configure_vray_settings(
        self, data: Dict[str, Any], render_elements: List[RenderElementInfo], ignore_list: List[str]
    ) -> None:
        """
        Configure V-Ray specific render element settings.

        Args:
            data: Configuration parameters
            render_elements: List of render elements from scene
        """
        try:
            # Check if V-Ray VFB control is enabled
            vfb_control = (
                self._get_param_value(
                    data,
                    ["vray_render_elements_vfb_control"],
                    "true",
                ).lower()
                == "true"
            )
            split_buffer = (
                self._get_param_value(data, ["vray_split_buffer_support"], "true").lower() == "true"
            )

            if vfb_control or split_buffer:
                self.logger.info(
                    f"Configuring V-Ray settings for '{self.current_renderer}' - VFB Control: {vfb_control}, Split Buffer: {split_buffer}"
                )
                if split_buffer:
                    if self.output_file_path and self.output_file_name:
                        self.logger.info(
                            f"Split buffer output: {os.path.join(self.output_file_path, self.output_file_name)}"
                        )
                    else:
                        self.logger.warning(
                            f"Split buffer enabled but missing output info - path: '{self.output_file_path}', name: '{self.output_file_name}'"
                        )

                vray_settings = VRayRenderElementSettings(
                    vray_render_elements_vfb_control=vfb_control,
                    vray_split_buffer_support=split_buffer,
                )

                vray_warnings = configure_vray_render_elements(
                    render_elements,
                    vray_settings,
                    output_path=self.output_file_path,
                    output_name=self.output_file_name,
                    output_file_format=self.output_file_format,
                    ignore_list=ignore_list,
                )
                if vray_warnings:
                    for warning in vray_warnings:
                        self.logger.warning(f"V-Ray configuration: {warning}")

        except Exception as e:
            self.logger.error(f"Failed to configure V-Ray settings: {e}")
            raise

    def validate_render_elements(self, data: Dict[str, Any]) -> RenderElementResult:
        """
        Validate render element configuration without making changes.

        Args:
            data: Dictionary containing render element configuration parameters

        Returns:
            RenderElementResult with validation results
        """
        try:
            self.logger.info("Validating render elements configuration")

            # Get current render elements from scene
            render_elements = get_render_elements()

            # Validate configuration using shared utilities
            settings = self._convert_data_to_settings(data)
            validation_warnings = validate_render_element_configuration(render_elements, settings)

            return RenderElementResult(
                success=True,
                message="Validation completed",
                element_count=len(render_elements),
                warnings=validation_warnings if validation_warnings else None,
            )

        except Exception as e:
            self.logger.error(f"Failed to validate render elements: {e}")
            return RenderElementResult(success=False, error=str(e))

    def restore_render_elements(self, data: Optional[Dict[str, Any]] = None) -> RenderElementResult:
        """
        Restore render elements to their original state.

        Args:
            data: Optional configuration data (unused but kept for interface consistency)

        Returns:
            RenderElementResult with restoration results
        """
        try:
            if not self.original_state:
                self.logger.info("No original state to restore")
                return RenderElementResult(success=True, message="No original state to restore")

            self.logger.info("Restoring render elements to original state")

            # Restore using shared utilities
            restore_warnings = restore_original_render_element_state(self.original_state)
            if restore_warnings:
                for warning in restore_warnings:
                    self.logger.warning(f"Restoration: {warning}")

            # Clear stored state and cached settings
            self.original_state = None
            self.cached_settings = {}
            self.is_configured = False

            self.logger.info("Render elements restored successfully")
            return RenderElementResult(
                success=True,
                message="Render elements restored successfully",
                warnings=restore_warnings if restore_warnings else None,
            )

        except Exception as e:
            self.logger.error(f"Failed to restore render elements: {e}")
            return RenderElementResult(success=False, error=str(e))

    def _get_ignore_list(self, data: Dict[str, Any]) -> List[str]:
        """
        Parse ignore render elements list from configuration data.

        Args:
            data: Configuration data dictionary

        Returns:
            List of render element names to ignore
        """
        ignore_names_str = self._get_param_value(data, ["ignore_render_elements_by_name"], "")
        if ignore_names_str:
            return [name.strip() for name in ignore_names_str.split(",") if name.strip()]
        return []

    def _get_param_value(
        self, data: Dict[str, Any], param_names: List[str], default: str = ""
    ) -> str:
        """
        Get parameter value from data dictionary.

        Args:
            data: Data dictionary
            param_names: List of parameter names to try (typically just one)
            default: Default value if none found

        Returns:
            Parameter value or default
        """
        for param_name in param_names:
            if param_name in data:
                value = data[param_name]
                self.logger.debug(f"Found parameter '{param_name}' with value: {value}")
                return str(value)

        self.logger.debug(f"No parameter found from {param_names}, using default: {default}")
        return default

    def _convert_data_to_settings(self, data: Dict[str, Any]) -> RenderElementConfigurationSettings:
        """
        Convert OpenJD data format to settings format expected by shared utilities.

        Args:
            data: OpenJD data dictionary

        Returns:
            RenderElementConfigurationSettings object compatible with shared utilities
        """
        # Use the parsed ignore list
        ignore_names = self._get_ignore_list(data)

        # Convert boolean settings
        render_elements_update_paths = (
            self._get_param_value(data, ["render_elements_update_paths"], "true").lower() == "true"
        )

        # Path and filename inclusion settings
        render_elements_include_name_in_path = (
            self._get_param_value(
                data,
                ["render_elements_include_name_in_path"],
                "true",
            ).lower()
            == "true"
        )

        render_elements_include_type_in_path = (
            self._get_param_value(
                data,
                ["render_elements_include_type_in_path"],
                "false",
            ).lower()
            == "true"
        )

        render_elements_include_name_in_filename = (
            self._get_param_value(
                data,
                ["render_elements_include_name_in_filename"],
                "true",
            ).lower()
            == "true"
        )

        render_elements_include_type_in_filename = (
            self._get_param_value(
                data,
                ["render_elements_include_type_in_filename"],
                "false",
            ).lower()
            == "true"
        )

        return RenderElementConfigurationSettings(
            ignore_render_elements_by_name=ignore_names,
            render_elements_update_paths=render_elements_update_paths,
            render_elements_include_name_in_path=render_elements_include_name_in_path,
            render_elements_include_type_in_path=render_elements_include_type_in_path,
            render_elements_include_name_in_filename=render_elements_include_name_in_filename,
            render_elements_include_type_in_filename=render_elements_include_type_in_filename,
        )

    def get_cached_settings(self) -> Dict[str, Any]:
        """
        Get the cached render element settings.

        Returns:
            Dictionary containing cached render element settings
        """
        return self.cached_settings.copy()

    def has_render_elements_configured(self) -> bool:
        """
        Check if render elements have been configured.

        Returns:
            True if render elements have been configured, False otherwise
        """
        return self.is_configured and bool(self.cached_settings)
