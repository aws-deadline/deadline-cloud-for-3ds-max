# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Data Classes for the UI settings and state set data
"""

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pymxs  # noqa
from deadline.max_submitter.data_const import ALL_CAMERAS_STR, RENDER_SUBMITTER_SETTINGS_FILE_EXT
from pymxs import runtime as rt


# Constants for render element parameter processing
RENDER_ELEMENT_PARAMS: List[str] = [
    "RenderElementsModified",
    "RenderElements",
    "RenderElementsUpdatePaths",
    "RenderElementsIncludeNameInPath",
    "RenderElementsIncludeTypeInPath",
    "RenderElementsIncludeNameInFilename",
    "RenderElementsIncludeTypeInFilename",
    "VRayRenderElementsVFBControl",
    "VRaySplitBufferSupport",
    "IgnoreRenderElementsByName",
]

RENDER_ELEMENT_PARAM_MAPPING: Dict[str, str] = {
    "RenderElementsModified": "enabled_modify_render_elements",
    "RenderElements": "render_elements",
    "RenderElementsUpdatePaths": "render_elements_update_paths",
    "RenderElementsIncludeNameInPath": "render_elements_include_name_in_path",
    "RenderElementsIncludeTypeInPath": "render_elements_include_type_in_path",
    "RenderElementsIncludeNameInFilename": "render_elements_include_name_in_filename",
    "RenderElementsIncludeTypeInFilename": "render_elements_include_type_in_filename",
    "VRayRenderElementsVFBControl": "vray_render_elements_vfb_control",
    "VRaySplitBufferSupport": "vray_split_buffer_support",
    "IgnoreRenderElementsByName": "ignore_render_elements_by_name",
}


@dataclass
class StateSetData:
    """
    Data class containing all variables that can be state set specific
    """

    state_set: str
    renderer: str
    frame_range: str
    output_directories: set[str]
    output_file_dir: str
    output_file_name: str
    output_file_format: str
    image_resolution: tuple[int, int]
    ui_group_label: Optional[str]


@dataclass
class RenderSubmitterUISettings:
    """
    Settings that the submitter UI will use
    """

    submitter_name: str = field(default="3dsMax")

    # Shared job settings tab
    name: str = field(default="", metadata={"sticky": True})
    description: str = field(default="", metadata={"sticky": True})

    priority: int = field(default=50, metadata={"sticky": True})
    initial_status: str = field(default="READY", metadata={"sticky": True})
    max_failed_tasks_count: int = field(default=20, metadata={"sticky": True})
    max_retries_per_task: int = field(default=5, metadata={"sticky": True})
    max_worker_count: int = field(
        default=-1, metadata={"sticky": True}
    )  # -1 indicates unlimited max worker count

    # Job specific settings tab
    override_frame_range: bool = field(default=False, metadata={"sticky": True})
    frame_list: str = field(default="", metadata={"sticky": True})
    project_path: str = field(default="")
    output_path: str = field(default="")

    output_name: str = field(default="", metadata={"sticky": True})
    output_ext_list: list[str] = field(default_factory=list)
    output_ext: str = field(default=".jpg", metadata={"sticky": True})

    renderer: str = field(default="")
    state_set: str = field(default="")
    state_set_index: str = field(default="")

    # Scene tweaks
    merge_xref_obj: bool = field(default=False, metadata={"sticky": True})
    merge_xref_scn: bool = field(default=False, metadata={"sticky": True})
    clear_mat: bool = field(default=False, metadata={"sticky": True})
    unlock_mat: bool = field(default=False, metadata={"sticky": True})
    custom_mat_chck: bool = field(default=False, metadata={"sticky": True})
    custom_mat: str = field(default="", metadata={"sticky": True})
    backup_file: str = field(default="")

    # Attachments
    input_filenames: list[str] = field(default_factory=list, metadata={"sticky": True})
    input_directories: list[str] = field(default_factory=list, metadata={"sticky": True})
    output_directories: list[str] = field(default_factory=list, metadata={"sticky": True})

    # Cameras
    camera_selection: str = field(default=ALL_CAMERAS_STR)
    stereo_camera: str = field(default="None")
    all_cameras: list[str] = field(default_factory=list)
    all_stereo_cameras: list[str] = field(default_factory=list)

    # Render Elements (Basic Support - already implemented)
    # Master control for render elements modification
    enabled_modify_render_elements: bool = field(default=False, metadata={"sticky": True})
    # Enable/disable render elements output
    render_elements: bool = field(default=True, metadata={"sticky": True})

    # List of specific render element names to ignore
    ignore_render_elements_by_name: list[str] = field(
        default_factory=list, metadata={"sticky": True}
    )
    # Output paths for each render element
    render_element_output_filenames: list[str] = field(default_factory=list)

    # Enhanced Render Elements (building on existing basic support - Deadline 10 feature parity)
    # Automatically update render element output paths during submission
    render_elements_update_paths: bool = field(default=True, metadata={"sticky": True})

    # Include render element name in the output directory path
    render_elements_include_name_in_path: bool = field(default=True, metadata={"sticky": True})
    # Include render element type (class name) in the output directory path
    render_elements_include_type_in_path: bool = field(default=False, metadata={"sticky": True})
    # Include render element name in the output filename
    render_elements_include_name_in_filename: bool = field(default=True, metadata={"sticky": True})
    # Include render element type (class name) in the output filename
    render_elements_include_type_in_filename: bool = field(default=False, metadata={"sticky": True})

    # Store original render element names for restoration after submission
    original_render_element_names: list[str] = field(default_factory=list)

    # V-Ray Render Element Integration (V-Ray specific features from Deadline 10)
    # Control V-Ray VFB settings for render elements during rendering
    vray_render_elements_vfb_control: bool = field(default=True, metadata={"sticky": True})
    # Enable V-Ray split buffer functionality for render elements
    vray_split_buffer_support: bool = field(default=True, metadata={"sticky": True})

    # Developer options
    include_adaptor_wheels: bool = field(default=False, metadata={"sticky": True})

    def load_sticky_settings(self) -> None:
        """
        Reads sticky settings from the sticky settings json file saved alongside the max scene
        """
        scene = rt.maxFilePath + rt.maxFileName
        sticky_settings_filename = Path(scene).with_suffix(RENDER_SUBMITTER_SETTINGS_FILE_EXT)
        if sticky_settings_filename.exists() and sticky_settings_filename.is_file():
            try:
                with open(sticky_settings_filename, encoding="utf8") as fh:
                    sticky_settings = json.load(fh)

                if isinstance(sticky_settings, dict):
                    sticky_fields = {
                        field.name: field
                        for field in dataclasses.fields(self)
                        if field.metadata.get("sticky")
                    }
                    for name, value in sticky_settings.items():
                        # Only set fields that are defined in the dataclass
                        if name in sticky_fields:
                            setattr(self, name, value)
            except (OSError, json.JSONDecodeError):
                # If something bad happened to the sticky settings file, just use the defaults instead of
                # producing an error.
                import traceback

                traceback.print_exc()
                print(
                    f"WARNING: Failed to load sticky settings file {sticky_settings_filename}, reverting to the "
                    "default settings."
                )

    def save_sticky_settings(self) -> None:
        """
        Writes sticky settings to json file at same directory as max scene
        """
        scene = rt.maxFilePath + rt.maxFileName
        sticky_settings_filename = Path(scene).with_suffix(RENDER_SUBMITTER_SETTINGS_FILE_EXT)
        with open(sticky_settings_filename, "w", encoding="utf8") as fh:
            obj = {
                field.name: getattr(self, field.name)
                for field in dataclasses.fields(self)
                if field.metadata.get("sticky")
            }
            json.dump(obj, fh, indent=1)

    def validate_render_element_names(self) -> list[str]:
        """
        Validate render element names to ensure they exist in the scene.

        :returns: list of invalid render element names
        :return_type: list[str]
        """
        invalid_names: list[str] = []
        if not self.ignore_render_elements_by_name:
            return invalid_names

        try:
            # Get render element manager
            re_manager = rt.maxOps.GetCurRenderElementMgr()
            if not re_manager:
                return self.ignore_render_elements_by_name  # All names are invalid if no manager

            # Get all render element names in the scene
            scene_element_names = []
            for i in range(re_manager.NumRenderElements()):
                element = re_manager.GetRenderElement(i)
                if element:
                    scene_element_names.append(str(element.elementName))

            # Check which names in ignore list don't exist in scene
            for name in self.ignore_render_elements_by_name:
                if name not in scene_element_names:
                    invalid_names.append(name)

        except Exception:
            # If we can't access render elements, consider all names invalid
            invalid_names = self.ignore_render_elements_by_name.copy()

        return invalid_names

    def validate_render_element_paths(self) -> list[str]:
        """
        Validate render element output paths to ensure they are accessible.

        :returns: list of invalid or inaccessible paths
        :return_type: list[str]
        """
        # No validation needed for render element output filenames currently
        return []

    def validate_render_element_configuration(self) -> list[str]:
        """
        Validate render element configuration consistency for enhanced features.

        :returns: list of configuration warnings or issues
        :return_type: list[str]
        """
        warnings = []

        # Basic validation - check if ignore list has invalid names
        invalid_names = self.validate_render_element_names()
        if invalid_names:
            warnings.append(
                f"Ignored render element names not found in scene: {', '.join(invalid_names)}"
            )

        # Check V-Ray specific settings consistency
        if self.vray_split_buffer_support and not self.vray_render_elements_vfb_control:
            warnings.append(
                "V-Ray split buffer support is enabled but V-Ray VFB control is disabled - this may not work as expected"
            )

        return warnings

    def store_original_render_element_state(self) -> None:
        """
        Store original render element names and settings for restoration after submission.
        This should be called before making any permanent changes to render elements.
        """
        try:
            # Get render element manager
            re_manager = rt.maxOps.GetCurRenderElementMgr()
            if not re_manager:
                return

            # Store original element names
            original_names = []
            for i in range(re_manager.NumRenderElements()):
                element = re_manager.GetRenderElement(i)
                if element and hasattr(element, "elementName"):
                    original_names.append(str(element.elementName))
                else:
                    original_names.append(f"Element_{i}")

            self.original_render_element_names = original_names

        except Exception:
            # If we can't access render elements, clear the original names list
            self.original_render_element_names = []

    def restore_original_render_element_state(self) -> bool:
        """
        Restore original render element names and settings after submission.

        :returns: True if restoration was successful, False otherwise
        :return_type: bool
        """
        if not self.original_render_element_names:
            return False

        try:
            # Get render element manager
            re_manager = rt.maxOps.GetCurRenderElementMgr()
            if not re_manager:
                return False

            # Restore original element names
            count = min(len(self.original_render_element_names), re_manager.NumRenderElements())
            for i in range(count):
                element = re_manager.GetRenderElement(i)
                if element and hasattr(element, "elementName"):
                    element.elementName = self.original_render_element_names[i]

            # Clear the stored names after restoration
            self.original_render_element_names = []
            return True

        except Exception:
            return False
