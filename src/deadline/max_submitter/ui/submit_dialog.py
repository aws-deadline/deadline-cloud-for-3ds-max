"""
3ds Max Deadline Cloud Submitter - Custom submit dialog functions.

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import logging

from deadline.client.ui.dialogs.submit_job_to_deadline_dialog import SubmitJobToDeadlineDialog
from utilities import submission_utils

_logger = logging.getLogger(__name__)


class SubmitMaxJobToDeadlineDialog(SubmitJobToDeadlineDialog):
    """
    Inherited from original SubmitJobToDeadlineDialog.
    - 3ds Max needs custom close function
    - Override the submit function to revert scene to original state when cancel button gets pressed
    """

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
