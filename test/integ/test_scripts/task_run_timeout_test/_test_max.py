# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Submitter test script for the task_run_timeout feature.

Runs inside 3ds Max via 3dsmaxbatch. Sets task_run_timeout_seconds = 30 on the
settings object and exports a job bundle. The test then verifies that the generated
template.yaml has `timeout: 30` on the onRun action of every step.
"""

from pymxs import runtime as rt

from deadline.client.ui.dialogs._types import JobBundlePurpose

from deadline.max_submitter.max_render_submitter import (
    show_job_bundle_submitter,
    on_create_job_bundle_callback,
)
from deadline.max_submitter.data_const import ALL_CAMERAS_STR, ALL_STATE_SETS_STR

# Timeout value used by both this script and the pytest assertion
TASK_RUN_TIMEOUT_SECONDS = 30


def main(job_history_dir: str, output_dir: str):
    """
    Open the submitter, configure a task run timeout, and export a job bundle.
    """
    widget = show_job_bundle_submitter()
    # show_job_bundle_submitter returns None when a pre-GUI hook aborts the open (declined
    # confirmation, hook failure, or a bad hook value). This test configures no environment hooks,
    # so that path is not expected here; assert to fail clearly instead of raising an opaque
    # AttributeError on widget.job_settings_type() below if it ever does.
    assert widget is not None, "submitter did not open (pre-GUI hook aborted?)"

    settings = widget.job_settings_type()
    widget.shared_job_settings.update_settings(settings)
    widget.job_settings.update_settings(settings)

    settings.state_set = ALL_STATE_SETS_STR
    settings.camera_selection = ALL_CAMERAS_STR
    settings.include_adaptor_wheels = False
    settings.override_frame_range = True
    settings.frame_list = "1"
    settings.output_filename_pattern = "<stateset>_test_###_<camera>"

    # --- The feature under test ---
    settings.task_run_timeout_seconds = TASK_RUN_TIMEOUT_SECONDS

    widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
        {"name": "deadline:targetTaskRunStatus", "value": "READY"}
    )
    widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
        {"name": "deadline:maxFailedTasksCount", "value": 20}
    )
    widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
        {"name": "deadline:maxRetriesPerTask", "value": 5}
    )
    widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
        {"name": "deadline:priority", "value": 50}
    )

    on_create_job_bundle_callback(
        widget,
        job_history_dir,
        settings,
        widget.shared_job_settings.get_parameters(),
        widget.job_attachments.get_asset_references(),
        {output_dir},
        widget.host_requirements.get_requirements(),
        purpose=JobBundlePurpose.EXPORT,
    )


if __name__ == "__main__":
    opts = rt.maxops.mxsCmdLineArgs
    job_history_dir = repr(opts[rt.name("job_history_dir")])
    output_dir = repr(opts[rt.name("output_dir")])
    main(job_history_dir[1:-1], output_dir[1:-1])
