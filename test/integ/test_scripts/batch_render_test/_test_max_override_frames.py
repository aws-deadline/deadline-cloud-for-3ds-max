# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pymxs import runtime as rt

from deadline.client.ui.dialogs._types import JobBundlePurpose

from deadline.max_submitter.max_render_submitter import (
    show_job_bundle_submitter,
    on_create_job_bundle_callback,
)
from deadline.max_submitter.data_classes import SubmissionMode


def main(job_history_dir: str, output_dir: str):
    """
    This is a script that runs inside of 3dsMax, it sets up the scene file and exports
    a job bundle. This test covers batch render submission mode with override frame range.
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

    settings.submission_mode = SubmissionMode.BATCH_RENDER.value
    settings.include_adaptor_wheels = False
    settings.override_frame_range = True
    settings.frame_list = "1-2"

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
