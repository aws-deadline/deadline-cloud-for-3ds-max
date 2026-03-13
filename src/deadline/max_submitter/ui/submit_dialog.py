"""
3ds Max Deadline Cloud Submitter - Custom submit dialog functions.

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import logging

from deadline.client.ui.dialogs.submit_job_to_deadline_dialog import SubmitJobToDeadlineDialog
from pymxs import runtime as rt
from ui.vray_standalone_tab import VRayStandaloneSettingsWidget
from utilities import max_utils, submission_utils
from utilities.vrscene_utils import is_vray_renderer
from vrscene_settings import VRSceneRenderSubmitterUISettings

_logger = logging.getLogger(__name__)


class SubmitMaxJobToDeadlineDialog(SubmitJobToDeadlineDialog):
    """
    Inherited from original SubmitJobToDeadlineDialog.
    - 3ds Max needs custom close function
    - Override the submit function to revert scene to original state when cancel button gets pressed
    - Adds V-Ray Export tab when V-Ray is the active renderer
    """

    def __init__(self, **kwargs):
        """
        Initialize the submit dialog.

        Args:
            **kwargs: Arguments passed to parent class
        """
        # Store the original callback
        self._original_callback = kwargs.get("on_create_job_bundle_callback")

        # Replace with our wrapper callback
        kwargs["on_create_job_bundle_callback"] = self._on_create_job_bundle_wrapper

        # Call parent constructor
        super().__init__(**kwargs)

        # Add V-Ray Export tab if V-Ray is active
        self._add_vray_export_tab_if_available()

    def _on_create_job_bundle_wrapper(
        self,
        widget,
        job_bundle_dir,
        settings,
        queue_parameters,
        asset_references,
        output_directories=None,
        host_requirements=None,
        purpose=None,
    ):
        """
        Wrapper callback that routes to V-Ray export or regular 3ds Max render.

        Checks if V-Ray Export is enabled and routes accordingly.
        """
        # Check if V-Ray Export tab exists and is enabled
        if hasattr(self, "vray_export_widget") and self.vray_export_widget.is_vray_export_enabled():
            _logger.info("V-Ray Export is enabled - creating V-Ray export job")

            # Get V-Ray settings from the tab (creates new settings object)
            vrscene_settings = self.vray_export_widget.update_settings()

            # Update scene file and vrscene filename from current scene
            vrscene_settings.scene_file = rt.maxFilePath + rt.maxFileName
            vrscene_settings.vrscene_filename = max_utils.get_scene_name()

            # Imported here to avoid circular import:
            # submit_dialog -> vray_standalone_submitter -> submit_dialog
            from vray_standalone_submitter import on_create_vrscene_job_bundle_callback

            on_create_vrscene_job_bundle_callback(
                widget=widget,
                job_bundle_dir=job_bundle_dir,
                settings=vrscene_settings,
                queue_parameters=queue_parameters,
                asset_references=asset_references,
                host_requirements=host_requirements,
                purpose=purpose,
            )
        else:
            _logger.info("V-Ray Export is disabled - creating regular 3ds Max render job")

            # Call original 3ds Max render job creation
            if self._original_callback:
                self._original_callback(
                    widget=widget,
                    job_bundle_dir=job_bundle_dir,
                    settings=settings,
                    queue_parameters=queue_parameters,
                    asset_references=asset_references,
                    output_directories=output_directories,
                    host_requirements=host_requirements,
                    purpose=purpose,
                )

    def _add_vray_export_tab_if_available(self):
        """
        Add V-Ray Export tab if V-Ray is the active renderer.
        """
        try:
            if is_vray_renderer():
                _logger.info("V-Ray detected - adding V-Ray Export tab")

                # Create V-Ray settings
                vrscene_settings = VRSceneRenderSubmitterUISettings()
                vrscene_settings.name = max_utils.get_scene_name()
                vrscene_settings.frame_list = max_utils.get_frames()
                vrscene_settings.scene_file = rt.maxFilePath + rt.maxFileName
                vrscene_settings.output_path = max_utils.get_scene_dir()
                vrscene_settings.vrscene_filename = max_utils.get_scene_name()
                vrscene_settings.load_sticky_settings()

                # Create V-Ray widget
                self.vray_export_widget = VRayStandaloneSettingsWidget(
                    initial_settings=vrscene_settings, parent=self
                )

                # Add as a new tab
                if hasattr(self, "tabs"):
                    self.tabs.addTab(self.vray_export_widget, "V-Ray Export")
                    _logger.info("V-Ray Export tab added successfully")

        except Exception as e:
            _logger.warning(f"Could not add V-Ray Export tab: {e}")

    def close(self):
        """
        Restore all changes made by the scene tweaks to their original state.
        """
        scene_tweaks = False

        if submission_utils.clear_mat:
            submission_utils.restore_material_editor(submission_utils.cleared_materials)
            submission_utils.clear_mat = False
            scene_tweaks = True

        if submission_utils.unlock_mat:
            submission_utils.lock_material_editor_renderer()
            submission_utils.unlock_mat = False
            scene_tweaks = True

        if submission_utils.custom_mat:
            submission_utils.restore_scene_materials(submission_utils.overridden_materials)
            submission_utils.custom_mat = False
            scene_tweaks = True

        if submission_utils.backup_saved:
            submission_utils.restore_max_copy(submission_utils.backup_file)
            submission_utils.backup_saved = False
            scene_tweaks = True

        if scene_tweaks:
            submission_utils.save_scene()

    def on_submit(self):
        """
        Perform a submission when the submit button is pressed. Calls super and then calls the close function
        to always revert the scene to the original state after pressing submit.
        """
        super().on_submit()
        self.close()
