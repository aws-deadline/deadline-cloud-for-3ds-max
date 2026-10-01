# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""3ds Max Command-Line (3dsmaxcmd) Render Settings Data Class."""

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path

from data_const import MAXCMD_SUBMITTER_SETTINGS_FILE_EXT
from pymxs import runtime as rt


@dataclass
class MaxCmdSubmitterUISettings:
    """Settings for the 3dsmaxcmd command-line render workflow."""

    submitter_name: str = field(default="MaxCmdRender")

    # Job name and description. These are populated from the base dialog's
    # "Shared job settings" tab at submit time (not edited on the maxcmd tab),
    # so they are not sticky here.
    name: str = field(default="")
    description: str = field(default="")

    # Scene / render settings
    scene_file: str = field(default="")
    frame_list: str = field(default="", metadata={"sticky": True})
    # Output location is NOT sticky: it is derived from the scene's Render Setup
    # output (rendOutputFilename) each time the dialog opens, so the scene stays
    # the source of truth. A stale sticky value would otherwise mask a changed
    # scene output path.
    output_path: str = field(default="")
    output_filename: str = field(default="")
    camera: str = field(default="", metadata={"sticky": True})

    # 3dsmaxcmd executable. Defaults to '3dsmaxcmd' (resolved on the worker PATH);
    # override with a full path if it is not on PATH.
    maxcmd_executable: str = field(default="3dsmaxcmd", metadata={"sticky": True})

    # Per-task render timeout in seconds. 0 means no timeout (a task runs until
    # it completes). Mirrors the standard tab's "Override Task Run Timeout".
    task_run_timeout_seconds: int = field(default=0, metadata={"sticky": True})

    # Note: job attachments (input/output files and directories) are owned by the
    # base dialog's Job Attachments tab and its own sticky settings, so they are
    # not duplicated here.

    def load_sticky_settings(self) -> None:
        """Load sticky settings from the JSON file alongside the max scene."""
        scene = rt.maxFilePath + rt.maxFileName
        sticky_settings_filename = Path(scene).with_suffix(MAXCMD_SUBMITTER_SETTINGS_FILE_EXT)
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
                        if name in sticky_fields:
                            setattr(self, name, value)
            except (OSError, json.JSONDecodeError):
                import traceback

                traceback.print_exc()
                print(
                    f"WARNING: Failed to load sticky settings file {sticky_settings_filename}, "
                    "reverting to the default settings."
                )

    def save_sticky_settings(self) -> None:
        """Save sticky settings to the JSON file alongside the max scene."""
        scene = rt.maxFilePath + rt.maxFileName
        sticky_settings_filename = Path(scene).with_suffix(MAXCMD_SUBMITTER_SETTINGS_FILE_EXT)
        with open(sticky_settings_filename, "w", encoding="utf8") as fh:
            obj = {
                field.name: getattr(self, field.name)
                for field in dataclasses.fields(self)
                if field.metadata.get("sticky")
            }
            json.dump(obj, fh, indent=1)
