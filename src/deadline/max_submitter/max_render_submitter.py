# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Create UI
"""

import logging
import math
import os
from os.path import abspath, join, normpath
from pathlib import Path
from typing import Any, Optional

import yaml

import qtmax
import pymxs  # noqa
from pymxs import runtime as rt

from PySide2.QtCore import Qt

from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.ui.dialogs._types import JobBundlePurpose

from ui.submit_dialog import SubmitMaxJobToDeadlineDialog
from ui.scene_settings_tab import SceneSettingsWidget
from data_classes import RenderSubmitterUISettings, StateSetData
from sanity_checks import check_sanity
from create_job_bundle import get_job_template, get_parameters_values
from utilities import max_utils, submission_utils
from data_const import (
    ALL_STEREO_CAMERAS_STR,
    ALL_STATE_SETS_STR,
    UI_GROUP_LABEL,
    TEMP_BACKUP_FILENAME,
)
from _version import version_tuple as adaptor_version_tuple

_logger = logging.getLogger(__name__)


def show_job_bundle_submitter():
    """
    Main function that shows the UI.
    """
    _logger.info("Opening Deadline Cloud 3dsMax Submitter interface")
    # Get main max window
    main_window = qtmax.GetQMaxMainWindow()

    # Load default template
    with open(Path(__file__).parent / "default_max_job_template.yaml") as fh:
        default_job_template = yaml.safe_load(fh)

    render_settings = RenderSubmitterUISettings()

    # Set settings dependent on scene
    render_settings.name = max_utils.get_scene_name()
    render_settings.frame_list = max_utils.get_frames()
    render_settings.project_path = max_utils.get_scene_path()
    render_settings.output_path = max_utils.get_scene_dir()
    render_settings.output_name = max_utils.get_scene_name() + "_###"
    render_settings.backup_file = rt.execute("GetDir #temp") + "\\" + TEMP_BACKUP_FILENAME
    render_settings.renderer = str(rt.renderers.current).split(":")[0].split("__")[0]

    render_settings.load_sticky_settings()

    output_directories: set[str] = set()

    # Add output dir from state set settings if one is set
    state_sets = max_utils.get_state_set_names()
    for state_set in state_sets:
        rt.execute(
            f"stateSetsDotNetObject = dotNetObject "
            f'"Autodesk.Max.StateSets.Plugin" \n'
            f"stateSets = stateSetsDotNetObject.Instance \n"
            f"masterState = stateSets.EntityManager.RootEntity."
            f"MasterStateSet \n"
            f"needState = masterState.Children.Item[{state_set[1]}] \n"
            f"masterState.CurrentState = #(needState)"
        )
        if rt.rendOutputFilename:
            output = os.path.split(rt.rendOutputFilename)
            output_directories.update([output[0]])
    output_directories.update([render_settings.output_path])
    render_settings.output_directories = output_directories

    def on_create_job_bundle_callback(
        widget: SubmitMaxJobToDeadlineDialog,
        job_bundle_dir: str,
        settings: RenderSubmitterUISettings,
        queue_parameters: list[dict[str, Any]],
        asset_references: AssetReferences,
        host_requirements: Optional[dict[str, Any]] = None,
        purpose: JobBundlePurpose = JobBundlePurpose.SUBMISSION,
    ) -> None:
        """
        Function that collects all data from the UI and creates a job bundle from that data.

        :param widget: the 3dsMax Submitter dialog
        :param job_bundle_dir: the directory where the job bundle needs to be saved
        :param settings: a RenderSubmitterUISettings object containing the latest UI settings
        :param queue_parameters: the settings from the shared job settings tab
        :param asset_references: an AssetReferences object containing the filepaths from the job attachments tab
        :param host_requirements: a list of OpenJD parameter definition dicts with values filled from the widget
        :param purpose: a value indicating which button was pressed.
            JobBundlePurpose.EXPORT when 'Export Bundle' was pressed
            JobBundlePurpose.SUBMISSION when 'Submit' was pressed
        """
        # Run all sanity checks
        check_sanity(settings)

        _logger.debug("Start on_create_job_bundle_callback")
        settings.backup_file = rt.execute("GetDir #temp") + "\\" + TEMP_BACKUP_FILENAME
        _logger.debug(f"backup file: {settings.backup_file}")

        # Reset in case Max remembered these settings
        submission_utils.backup_saved = False
        submission_utils.clear_mat = False
        submission_utils.unlock_mat = False
        submission_utils.custom_mat = False

        state_sets_to_submit: list[StateSetData] = []
        state_sets = max_utils.get_state_set_names()
        # if all state sets were chosen for submission, make a StateSetData object for each state set
        if settings.state_set == ALL_STATE_SETS_STR:
            for state_set in state_sets:
                # Set the current state set
                rt.execute(
                    f"stateSetsDotNetObject = dotNetObject "
                    f'"Autodesk.Max.StateSets.Plugin" \n'
                    f"stateSets = stateSetsDotNetObject.Instance \n"
                    f"masterState = stateSets.EntityManager.RootEntity."
                    f"MasterStateSet \n"
                    f"needState = masterState.Children.Item[{state_set[1]}] \n"
                    f"masterState.CurrentState = #(needState)"
                )
                # Check if an output directory is set in render setup dialog
                if rt.rendOutputFilename:
                    output_dir = os.path.split(rt.rendOutputFilename)[0]
                    output_file = os.path.split(rt.rendOutputFilename)[1]
                    output_file_name = Path(output_file).stem
                    output_file_format = os.path.splitext(output_file)[1]
                # If it isn't, use the UI fields data
                else:
                    output_dir = settings.output_path
                    output_file_name = state_set[0] + "_" + settings.output_name
                    output_file_format = settings.output_ext
                image_resolution = (rt.renderWidth, rt.renderHeight)

                state_sets_to_submit.append(
                    StateSetData(
                        state_set=state_set[0],
                        renderer=str(rt.renderers.current).split(":")[0].split("__")[0],
                        frame_range=max_utils.get_frames(),
                        output_directories=output_directories,
                        output_file_dir=output_dir,
                        output_file_name=output_file_name,
                        output_file_format=output_file_format,
                        image_resolution=image_resolution,
                        ui_group_label=state_set[0] + " Settings",
                    )
                )
        # Otherwise only create it for the selected state set
        else:
            need_state = settings.state_set_index
            # Set the current state set
            rt.execute(
                f"stateSetsDotNetObject = dotNetObject "
                f'"Autodesk.Max.StateSets.Plugin" \n'
                f"stateSets = stateSetsDotNetObject.Instance \n"
                f"masterState = stateSets.EntityManager.RootEntity."
                f"MasterStateSet \n"
                f"needState = masterState.Children.Item[{need_state}]\n"
                f"masterState.CurrentState = #(needState)"
            )
            # Check if an output directory is set in render setup dialog
            if rt.rendOutputFilename:
                output_dir = os.path.split(rt.rendOutputFilename)[0]
                output_file = os.path.split(rt.rendOutputFilename)[1]
                output_file_name = Path(output_file).stem
                output_file_format = os.path.splitext(output_file)[1]
            # If it isn't, use the UI fields data
            else:
                output_dir = settings.output_path
                output_file_name = settings.output_name
                output_file_format = settings.output_ext
            image_resolution = (rt.renderWidth, rt.renderHeight)

            state_sets_to_submit.append(
                StateSetData(
                    state_set=settings.state_set,
                    renderer=str(rt.renderers.current).split(":")[0].split("__")[0],
                    frame_range=max_utils.get_frames(),
                    output_directories=output_directories,
                    output_file_dir=output_dir,
                    output_file_name=output_file_name,
                    output_file_format=output_file_format,
                    image_resolution=image_resolution,
                    ui_group_label=UI_GROUP_LABEL,
                )
            )

        # Use override from UI if the checkbox is checked
        if settings.override_frame_range:
            for state_set in state_sets_to_submit:
                state_set.frame_range = settings.frame_list

        # Only do these actions when we want to submit a scene
        if purpose == JobBundlePurpose.SUBMISSION:
            # Make a backup of the current state of the scene
            if os.path.exists(settings.backup_file):
                os.remove(settings.backup_file)
            submission_utils.save_max_backup_file(settings.backup_file, True)
            _logger.debug("Saving backup")
            submission_utils.backup_saved = True
            submission_utils.backup_file = settings.backup_file

            # Make files absolute before submission
            submission_utils.make_paths_absolute()

            # Go over all the 'scene tweaks' check boxes
            if settings.merge_xref_obj or settings.merge_xref_scn:
                asset_references = submission_utils.merge_xrefs(settings, asset_references)

            if settings.clear_mat:
                submission_utils.cleared_materials = submission_utils.clear_material_editor()
                submission_utils.clear_mat = True

            if settings.unlock_mat:
                submission_utils.unlock_material_editor_renderer()
                submission_utils.unlock_mat = True

            if settings.custom_mat_chck:
                submission_utils.overridden_materials = submission_utils.apply_custom_material(
                    settings.custom_mat
                )
                submission_utils.custom_mat = True

            # Save the scene so that absolute paths and any scene tweaks applied become sticky.
            # When the ui closes after submission the scene gets reverted back to the original state
            submission_utils.save_scene()

        job_bundle_path = Path(job_bundle_dir)

        # Decide what 'all cameras' is based on the camera selection in the ui
        cameras_in_scene = settings.all_cameras
        if settings.camera_selection == ALL_STEREO_CAMERAS_STR:
            cameras_in_scene = settings.all_stereo_cameras

        job_template = get_job_template(
            default_job_template, settings, state_sets_to_submit, cameras_in_scene
        )

        parameter_values = get_parameters_values(settings, state_sets_to_submit, queue_parameters)

        # If "HostRequirements" is provided, inject it into each of the "Step"
        if host_requirements:
            # for each step in the template, append the same host requirements.
            for step in job_template["steps"]:
                step["hostRequirements"] = host_requirements

        # write template, parameter_values and asset_references file
        with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(job_template, f, indent=1)

        with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump({"parameterValues": parameter_values}, f, indent=1)
        with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

        attachments: AssetReferences = widget.job_attachments.attachments
        settings.input_filenames = sorted(attachments.input_filenames)
        settings.input_directories = sorted(attachments.input_directories)
        settings.input_filenames = sorted(attachments.input_filenames)

        # Save sticky settings
        settings.save_sticky_settings()

    # Fill in the auto-detected input files
    auto_detected_attachments = AssetReferences()
    relative_dir_base = rt.maxFilePath
    input_files: set[str] = {
        abspath(normpath(join(relative_dir_base, path)))
        for path in max_utils.get_referenced_files()
    }
    auto_detected_attachments.input_filenames = input_files

    attachments = AssetReferences(
        input_filenames=set(render_settings.input_filenames),
        input_directories=set(render_settings.input_directories),
        output_directories=set(render_settings.output_directories),
    )

    max_version = 2000 + (math.ceil(rt.maxVersion()[0] / 1000.0) - 2)
    adaptor_version = ".".join(str(v) for v in adaptor_version_tuple[:2])
    conda_packages = f"3dsmax={max_version}.* 3dsmax-openjd={adaptor_version}.*"

    # Instantiate and show the Submitter UI
    window = SubmitMaxJobToDeadlineDialog(
        job_setup_widget_type=SceneSettingsWidget,
        initial_job_settings=render_settings,
        initial_shared_parameter_values={
            "CondaPackages": conda_packages,
        },
        auto_detected_attachments=auto_detected_attachments,
        attachments=attachments,
        on_create_job_bundle_callback=on_create_job_bundle_callback,
        parent=main_window,
        f=Qt.Tool,
        show_host_requirements_tab=True,
    )
    window.show()
