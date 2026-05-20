# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""V-Ray Standalone Settings Data Class."""

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import pymxs  # noqa
from data_const import VRSCENE_SUBMITTER_SETTINGS_FILE_EXT
from pymxs import runtime as rt


@dataclass
class VRSceneRenderSubmitterUISettings:
    """Settings for V-Ray Standalone workflow."""

    submitter_name: str = field(default="VRayStandalone")

    # Shared job settings
    name: str = field(default="", metadata={"sticky": True})
    description: str = field(default="", metadata={"sticky": True})
    priority: int = field(default=50, metadata={"sticky": True})
    initial_status: str = field(default="READY", metadata={"sticky": True})
    max_failed_tasks_count: int = field(default=20, metadata={"sticky": True})
    max_retries_per_task: int = field(default=5, metadata={"sticky": True})

    # Export settings
    export_mode: int = field(default=1, metadata={"sticky": True})  # 1=Local, 2=Farm
    export_animation_mode: int = field(
        default=1, metadata={"sticky": True}
    )  # 1=Single, 2=PerFrame, 3=Incremental

    # Scene settings
    scene_file: str = field(default="")
    output_path: str = field(default="")
    vrscene_filename: str = field(default="")  # Derived from scene name
    frame_list: str = field(default="", metadata={"sticky": True})

    # V-Ray Standalone Render Options
    vrscene_render_region_columns: int = field(default=2, metadata={"sticky": True})
    vrscene_render_region_rows: int = field(default=2, metadata={"sticky": True})
    vrscene_render_engine: int = field(default=0, metadata={"sticky": True})  # 0=CPU, 5=CUDA, 7=RTX
    # RT engine stopping conditions — defaults work for most scenes, can be adjusted in the UI
    vrscene_rt_timeout: float = field(default=0.0, metadata={"sticky": True})  # minutes, 0=no limit
    vrscene_rt_noise: float = field(default=0.001, metadata={"sticky": True})  # noise threshold
    vrscene_rt_sample_level: int = field(default=0, metadata={"sticky": True})  # 0=no limit
    vrscene_create_movie: bool = field(default=False, metadata={"sticky": True})
    vrscene_movie_filename: str = field(default="output.mp4", metadata={"sticky": True})
    vrscene_movie_framerate: int = field(default=24, metadata={"sticky": True})

    # Output settings
    output_format: str = field(default="auto", metadata={"sticky": True})
    output_filename_override: str = field(default="", metadata={"sticky": True})

    # Image resolution (read from 3ds Max render settings at submission time)
    image_width: int = field(default=1920)
    image_height: int = field(default=1080)

    # Attachments
    input_filenames: List[str] = field(default_factory=list, metadata={"sticky": True})
    input_directories: List[str] = field(default_factory=list, metadata={"sticky": True})
    output_directories: List[str] = field(default_factory=list, metadata={"sticky": True})

    # Developer options
    include_adaptor_wheels: bool = field(default=False, metadata={"sticky": True})

    def load_sticky_settings(self) -> None:
        """Load sticky settings from JSON file alongside the max scene."""
        scene = rt.maxFilePath + rt.maxFileName
        sticky_settings_filename = Path(scene).with_suffix(VRSCENE_SUBMITTER_SETTINGS_FILE_EXT)
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
                import traceback

                traceback.print_exc()
                print(
                    f"WARNING: Failed to load sticky settings file {sticky_settings_filename}, reverting to the "
                    "default settings."
                )

    def save_sticky_settings(self) -> None:
        """Save sticky settings to JSON file alongside the max scene."""
        scene = rt.maxFilePath + rt.maxFileName
        sticky_settings_filename = Path(scene).with_suffix(VRSCENE_SUBMITTER_SETTINGS_FILE_EXT)
        with open(sticky_settings_filename, "w", encoding="utf8") as fh:
            obj = {
                field.name: getattr(self, field.name)
                for field in dataclasses.fields(self)
                if field.metadata.get("sticky")
            }
            json.dump(obj, fh, indent=1)
