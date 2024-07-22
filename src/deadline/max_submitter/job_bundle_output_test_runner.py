# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Defines the Render submitter command which is registered in 3ds Max.
"""
import difflib
import filecmp
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

import pymxs  # noqa
import qtmax
from deadline.client.exceptions import DeadlineOperationError
from deadline.client.ui import gui_error_handler
from deadline.client.ui.dialogs import submit_job_to_deadline_dialog
from max_render_submitter import show_job_bundle_submitter
from pymxs import runtime as rt
from PySide2.QtWidgets import (  # pylint: disable=import-error; type: ignore
    QApplication,
    QFileDialog,
    QMessageBox,
)


# The following functions expose a DCC interface to the job bundle output test logic.
def _get_dcc_main_window() -> Any:
    return qtmax.GetQMaxMainWindow()


def _open_dcc_scene_file(filename: str):
    """Opens the scene file in 3ds Max."""
    rt.SetQuietMode(True)
    rt.loadMaxFile(filename, quiet=True)


def _close_dcc_scene_file():
    """Closes the scene file in 3ds Max."""
    rt.SetQuietMode(True)
    rt.resetMaxFile(rt.Name("noPrompt"))


def _copy_dcc_scene_file(source_filename: str, dest_filename: str):
    # Copy all support files under the source filename's dirname
    shutil.copytree(
        os.path.dirname(source_filename), os.path.dirname(dest_filename), dirs_exist_ok=True
    )


def _show_deadline_cloud_submitter():
    """Shows the Deadline Cloud Submitter for Max."""
    return show_job_bundle_submitter()


# The following functions implement the test logic.


def _timestamp_string() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def run_max_render_submitter_job_bundle_output_test():
    """
    Runs a set of job bundle output tests from a directory.
    """
    # Get the DCC's main window so we can parent the submitter to it
    mainwin = _get_dcc_main_window()
    count_succeeded = 0
    count_failed = 0
    with gui_error_handler("Error running job bundle output test", mainwin):
        default_tests_dir = Path(__file__).parent.parent.parent.parent / "job_bundle_output_tests"

        tests_dir = QFileDialog.getExistingDirectory(
            mainwin, "Select a Directory Containing Max Job Bundle Tests", str(default_tests_dir)
        )

        if not tests_dir:
            return

        tests_dir = os.path.normpath(tests_dir)

        test_job_bundle_results_file = os.path.join(tests_dir, "test-job-bundle-results.txt")
        with open(test_job_bundle_results_file, "w", encoding="utf8") as report_fh:
            for test_name in os.listdir(tests_dir):
                job_bundle_test = os.path.join(tests_dir, test_name)
                if not os.path.isdir(job_bundle_test):
                    continue
                report_fh.write(f"\nTimestamp: {_timestamp_string()}\n")
                report_fh.write(f"Running job bundle output test: {job_bundle_test}\n")

                dcc_scene_file = os.path.join(job_bundle_test, "scene", f"{test_name}.max")

                if not (os.path.exists(dcc_scene_file) and os.path.isfile(dcc_scene_file)):
                    raise DeadlineOperationError(
                        f"Directory {job_bundle_test} does not contain the expected .max scene: {dcc_scene_file}."
                    )

                succeeded = _run_job_bundle_output_test(
                    job_bundle_test, dcc_scene_file, report_fh, mainwin
                )
                if succeeded:
                    count_succeeded += 1
                else:
                    count_failed += 1

            report_fh.write("\n")
            if count_failed:
                report_fh.write(f"Failed {count_failed} tests, succeeded {count_succeeded}.\n")
                QMessageBox.warning(
                    mainwin,
                    "Some Job Bundle Tests Failed",
                    f"Failed {count_failed} tests, succeeded {count_succeeded}.\nSee the file {test_job_bundle_results_file} for a full report.",
                )
            else:
                report_fh.write(f"All tests passed, ran {count_succeeded} total.\n")
                QMessageBox.information(
                    mainwin,
                    "All Job Bundle Tests Passed",
                    f"Ran {count_succeeded} tests in total.",
                )
            report_fh.write(f"Timestamp: {_timestamp_string()}\n")


def _run_job_bundle_output_test(test_dir: str, dcc_scene_file: str, report_fh, mainwin: Any):
    with tempfile.TemporaryDirectory(prefix="job_bundle_output_test") as tempdir:
        temp_job_bundle_dir = os.path.join(tempdir, "job_bundle")
        os.makedirs(temp_job_bundle_dir, exist_ok=True)

        temp_dcc_scene_file = os.path.join(tempdir, os.path.basename(dcc_scene_file))

        # Copy the DCC scene file to the temp directory, transforming any
        # internal paths as necessary.
        _copy_dcc_scene_file(dcc_scene_file, temp_dcc_scene_file)

        # Open the DCC scene file
        _open_dcc_scene_file(temp_dcc_scene_file)
        QApplication.processEvents()

        # Open the AWS Deadline Cloud submitter
        submitter = _show_deadline_cloud_submitter()
        QApplication.processEvents()

        # Save the Job Bundle
        # Use patching to set the job bundle directory and skip the success messagebox
        with (
            mock.patch.object(
                submit_job_to_deadline_dialog,
                "create_job_history_bundle_dir",
                return_value=temp_job_bundle_dir,
            ),
            mock.patch.object(submit_job_to_deadline_dialog, "QMessageBox"),
            mock.patch.object(
                os,
                "startfile",
                create=True,  # only exists on win. Just create to avoid AttributeError
            ),
        ):
            submitter.on_export_bundle()
        QApplication.processEvents()

        # Close the DCC scene file
        _close_dcc_scene_file()
        submitter.close()

        # Process every file in the job bundle to replace the temp dir with a standardized path
        for filename in os.listdir(temp_job_bundle_dir):
            full_filename = os.path.join(temp_job_bundle_dir, filename)
            with open(full_filename, encoding="utf8") as f:
                contents = f.read()
            contents = contents.replace(tempdir + "\\", "/normalized/job/bundle/dir/")
            contents = contents.replace(
                tempdir.replace("\\", "/") + "/", "/normalized/job/bundle/dir/"
            )
            contents = contents.replace(tempdir, "/normalized/job/bundle/dir")
            contents = contents.replace(tempdir.replace("\\", "/"), "/normalized/job/bundle/dir")
            with open(full_filename, "w", encoding="utf8") as f:
                f.write(contents)

        # If there's an expected job bundle to compare with, do the comparison,
        # otherwise copy the one we created to be that expected job bundle.
        expected_job_bundle_dir = os.path.join(test_dir, "expected_job_bundle")
        if os.path.exists(expected_job_bundle_dir):
            test_job_bundle_dir = os.path.join(test_dir, "test_job_bundle")
            if os.path.exists(test_job_bundle_dir):
                shutil.rmtree(test_job_bundle_dir)
            shutil.copytree(temp_job_bundle_dir, test_job_bundle_dir)

            dcmp = filecmp.dircmp(expected_job_bundle_dir, test_job_bundle_dir)
            report_fh.write("\n")
            report_fh.write(f"{os.path.basename(test_dir)}\n")
            if dcmp.left_only or dcmp.right_only or dcmp.diff_files:
                report_fh.write("Test failed, found differences\n")
                if dcmp.left_only:
                    report_fh.write(f"Missing files: {dcmp.left_only}\n")
                if dcmp.right_only:
                    report_fh.write(f"Extra files: {dcmp.right_only}\n")
                for file in dcmp.diff_files:
                    with (
                        open(os.path.join(expected_job_bundle_dir, file), encoding="utf8") as fleft,
                        open(os.path.join(test_job_bundle_dir, file), encoding="utf8") as fright,
                    ):
                        diff = "".join(
                            difflib.unified_diff(
                                list(fleft), list(fright), "expected/" + file, "test/" + file
                            )
                        )
                        report_fh.write(diff)

                # Failed the test
                return False
            else:
                report_fh.write("Test succeeded\n")
                # Succeeded the test
                return True
        else:
            shutil.copytree(temp_job_bundle_dir, expected_job_bundle_dir)

            report_fh.write("Test cannot compare. Saved new reference to expected_job_bundle.\n")
            # We generated the original expected job bundle, so did not succeed a test.
            return False


if __name__ == "__main__":
    run_max_render_submitter_job_bundle_output_test()
