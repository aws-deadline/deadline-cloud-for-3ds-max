# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Data Classes for the UI settings and state set data
"""

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Optional

import pymxs  # noqa
from pymxs import runtime as rt

from data_const import ALL_CAMERAS_STR, RENDER_SUBMITTER_SETTINGS_FILE_EXT


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

    # Developer options
    include_adaptor_wheels: bool = field(default=False, metadata={"sticky": True})

    def load_sticky_settings(self):
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
                pass

    def save_sticky_settings(self):
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
