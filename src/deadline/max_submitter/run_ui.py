# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Show UI
"""


# --- sys.path bootstrap (defense in depth) --------------------------------
# The installer registers DeadlineCloudMenu.ms as a 3ds Max startup script,
# which prepends the submitter's bundled dependencies to sys.path. If that
# startup step did not run (for example a customer with startup scripts
# disabled), make sure imports below can still resolve by prepending the
# submitter root ourselves. Idempotent: dedup is done on normalized paths
# (os.path.normpath + os.path.normcase) so entries added by
# DeadlineCloudMenu.ms with mixed forward/back slashes still match.
def _dc_bootstrap_sys_path() -> None:
    import os
    import sys

    submitter_root = os.environ.get("MAX_SUBMITTER") or os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    candidates = (
        os.path.join(submitter_root, "deadline", "max_submitter"),
        submitter_root,
    )

    def canonical(p: str) -> str:
        return os.path.normcase(os.path.normpath(p))

    existing = {canonical(p) for p in sys.path if p}
    for path in candidates:
        if path and os.path.isdir(path) and canonical(path) not in existing:
            sys.path.insert(0, path)
            existing.add(canonical(path))


_dc_bootstrap_sys_path()
del _dc_bootstrap_sys_path
# --------------------------------------------------------------------------

from logging import root  # noqa: E402

from deadline.client.config import config_file  # noqa: E402
from max_render_submitter import show_job_bundle_submitter  # noqa: E402
from pymxs import runtime as rt  # noqa: E402
from qtpy.QtWidgets import QMessageBox  # type: ignore  # noqa: E402
from update_utils import check_and_show_update_dialog  # noqa: E402
from utilities.log_utils import configure_logging  # noqa: E402


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

    if check_and_show_update_dialog():
        return

    show_job_bundle_submitter()


if __name__ == "__main__":
    configure_logging()
    # Read starting log level from config file
    root.setLevel(config_file.get_setting("settings.log_level"))
    show_ui()
