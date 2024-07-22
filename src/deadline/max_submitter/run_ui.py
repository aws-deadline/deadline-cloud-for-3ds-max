# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Show UI
"""

from logging import root

from deadline.client.config import config_file
from max_render_submitter import show_job_bundle_submitter
from pymxs import runtime as rt
from PySide2.QtWidgets import QMessageBox
from utilities.log_utils import configure_logging


def show_ui():
    """
    Checks if the 3dsMax scene is saved or not. If it isn't saved yet show pop-up indicating the scene needs
    to be saved. If the scene is saved, open the submitter.
    Scene needs to be saved before opening, cause otherwise the load_sticky_settings function errors trying to find
    the json file with sticky settings
    """
    # Give popup if scene isn't saved yet
    if not rt.maxFileName:
        msg = QMessageBox()
        msg.setWindowTitle("AWS Deadline Cloud")
        msg.setText(
            "The 3dsMax Scene is not saved to disk. \n"
            "Please save it before opening the submitter dialog"
        )
        msg.setStandardButtons(QMessageBox.Ok)

        return_value = msg.exec()
        if return_value == QMessageBox.Ok:
            return

    show_job_bundle_submitter()


if __name__ == "__main__":
    configure_logging()
    # Read starting log level from config file
    root.setLevel(config_file.get_setting("settings.log_level"))
    show_ui()
