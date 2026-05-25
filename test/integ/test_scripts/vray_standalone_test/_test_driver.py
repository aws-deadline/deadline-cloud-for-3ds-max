# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Generic V-Ray Standalone integ test driver.

The host test writes a `test_config.json` into `job_history_dir` describing
the engine + RT settings to apply, then invokes this driver inside
3dsmaxbatch. The driver applies the config and either submits the bundle or,
when `expect_failure` is true, captures the resulting ValueError to
`validation_outcome.txt` for the host to assert on.
"""

import json
import os

from pymxs import runtime as rt

from deadline.client.ui.dialogs._types import JobBundlePurpose

from deadline.max_submitter.vray_standalone_submitter import (
    show_vray_standalone_submitter,
    on_create_vrscene_job_bundle_callback,
)


CONFIG_FILE = "test_config.json"
VALIDATION_OUTCOME_FILE = "validation_outcome.txt"


def main(job_history_dir: str, output_dir: str):
    with open(os.path.join(job_history_dir, CONFIG_FILE), encoding="utf8") as f:
        config = json.load(f)

    widget = show_vray_standalone_submitter()

    settings = widget.job_settings_type()
    widget.shared_job_settings.update_settings(settings)
    widget.job_settings.update_settings(settings)

    settings.export_mode = 2
    settings.export_animation_mode = 1
    settings.frame_list = "1-2"
    settings.output_path = output_dir
    settings.vrscene_render_region_columns = config["region_columns"]
    settings.vrscene_render_region_rows = config["region_rows"]
    settings.vrscene_render_engine = config["render_engine"]
    settings.vrscene_rt_timeout = config["rt_timeout"]
    settings.vrscene_rt_noise = config["rt_noise"]
    settings.vrscene_rt_sample_level = config["rt_sample_level"]
    settings.include_adaptor_wheels = False

    widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
        {"name": "deadline:targetTaskRunStatus", "value": "READY"}
    )
    widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
        {"name": "deadline:priority", "value": 50}
    )

    if config.get("expect_failure"):
        outcome_path = os.path.join(job_history_dir, VALIDATION_OUTCOME_FILE)
        try:
            on_create_vrscene_job_bundle_callback(
                widget,
                job_history_dir,
                settings,
                widget.shared_job_settings.get_parameters(),
                widget.job_attachments.get_asset_references(),
                purpose=JobBundlePurpose.EXPORT,
            )
            with open(outcome_path, "w", encoding="utf8") as f:
                f.write("UNEXPECTED_SUCCESS")
        except ValueError as e:
            with open(outcome_path, "w", encoding="utf8") as f:
                f.write(f"VALIDATION_FAILED\n{e}")
    else:
        on_create_vrscene_job_bundle_callback(
            widget,
            job_history_dir,
            settings,
            widget.shared_job_settings.get_parameters(),
            widget.job_attachments.get_asset_references(),
            purpose=JobBundlePurpose.EXPORT,
        )


if __name__ == "__main__":
    opts = rt.maxops.mxsCmdLineArgs
    job_history_dir = repr(opts[rt.name("job_history_dir")])
    output_dir = repr(opts[rt.name("output_dir")])
    main(job_history_dir[1:-1], output_dir[1:-1])
