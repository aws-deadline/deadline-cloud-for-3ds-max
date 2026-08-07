# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - 3dsmaxcmd Command-Line Render Workflow

Builds a job bundle that renders the scene with 3dsmaxcmd.exe (the render
server) instead of the standard 3dsmaxbatch adaptor. Path mapping is applied to
the scene's asset references before each render via a pre-render script, so
absolute paths baked into the scene resolve to their session locations on the
worker.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.ui.dialogs._types import JobBundlePurpose
from maxcmd_settings import MaxCmdSubmitterUISettings
from ui.submit_dialog import SubmitMaxJobToDeadlineDialog
from utilities.job_template_utils import inject_embedded_script, load_job_template

_logger = logging.getLogger(__name__)

_MAXCMD_TEMPLATE = "maxcmd_render_job_template.yaml"
_SCRIPT_PLACEHOLDER = "INJECT_MAXCMD_RENDER_SCRIPT"


def _get_maxcmd_render_script() -> str:
    """Read the maxcmd_render.py task-driver script from the scripts directory."""
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "maxcmd_render.py")
    with open(script_path, "r", encoding="utf8") as fh:
        return fh.read()


def on_create_maxcmd_job_bundle_callback(
    widget: SubmitMaxJobToDeadlineDialog,
    job_bundle_dir: str,
    settings: MaxCmdSubmitterUISettings,
    queue_parameters: list[dict[str, Any]],
    asset_references: AssetReferences,
    host_requirements: Optional[dict[str, Any]] = None,
    purpose: JobBundlePurpose = JobBundlePurpose.SUBMISSION,
) -> None:
    """Callback for creating the 3dsmaxcmd command-line render job bundle.

    Asset coverage
    --------------
    This callback does not scan the scene for dependencies itself. Scene-
    referenced assets (textures, XRefs, proxies, IES files, etc.) reach the
    bundle through ``asset_references`` as passed in by the base dialog, which
    combines Deadline Cloud's auto-detected attachments with anything the artist
    adds on the Job Attachments tab. On top of that incoming set, this callback
    only guarantees two things:

    * the scene file itself is added as an input (``input_filenames``), and
    * the output directory is registered as an output (``output_directories``).

    So if a dependency is missed by auto-detection, it must be added manually on
    the Job Attachments tab.

    Path-mapping coverage (limitation)
    ----------------------------------
    Uploading an asset is not enough on its own: the scene still holds the
    artist's absolute path for it, so at render time the pre-render script has
    to rewrite that path to the uploaded session location. That script only
    remaps **bitmap textures and XRef scenes** (plus the render output paths).
    Other baked absolute paths -- e.g. VRayProxy/Alembic caches, IES photometric
    files, OSL maps, sim caches -- are NOT rewritten, so even when their files
    are uploaded the scene keeps pointing at the original path and the worker
    won't find them. Scenes relying on those asset types are not fully supported
    by this command-line workflow yet; broader coverage is a follow-up.

    In particular, V-Ray VFB raw output (``output_rawFileName``) and split-channel
    output (``output_splitfilename``) are renderer-owned paths V-Ray writes
    itself, bypassing Max's output plumbing, so they are NOT redirected to the
    job output directory. A V-Ray scene using them, submitted through this tab,
    will write that output to the artist's baked path (failing on the worker or
    landing outside the captured output). For V-Ray, use the standard Output
    Filename field or the adaptor workflow. Redirecting V-Ray raw output is a
    follow-up.

    Output directory is required
    ----------------------------
    A job output directory must be set. Relying on the scene's baked Render
    Setup output path does not work on a worker (that path is the artist's local
    disk, has no path-mapping rule, and the render aborts writing there), and
    without a registered output directory the results are never captured by job
    attachments. So an empty output path is rejected below.
    """
    _logger.debug("Start on_create_maxcmd_job_bundle_callback")

    if not settings.scene_file:
        raise ValueError("A saved 3ds Max scene file is required to submit a 3dsmaxcmd render.")
    if not settings.frame_list:
        raise ValueError("A frame range is required to submit a 3dsmaxcmd render.")
    if not settings.output_path:
        raise ValueError(
            "An output directory is required to submit a 3dsmaxcmd render so the rendered "
            "images are written to a writable, captured location on the worker."
        )

    job_bundle_path = Path(job_bundle_dir)

    # Load the template and inject the task-driver script into the embedded file.
    job_template = load_job_template(_MAXCMD_TEMPLATE)
    job_template["name"] = settings.name or "3ds Max Command-Line Render"
    if settings.description:
        job_template["description"] = settings.description
    inject_embedded_script(job_template, _SCRIPT_PLACEHOLDER, _get_maxcmd_render_script())

    parameter_values: list[dict[str, Any]] = [
        {"name": "MaxCmdExecutable", "value": settings.maxcmd_executable or "3dsmaxcmd"},
        {"name": "SceneFile", "value": settings.scene_file},
        {"name": "Frames", "value": settings.frame_list},
        {"name": "OutputDirectory", "value": settings.output_path},
        {"name": "OutputFileName", "value": settings.output_filename},
        {"name": "Camera", "value": settings.camera},
    ]
    parameter_values.extend(queue_parameters)

    # Apply host requirements from the Host Requirements tab to each step, the
    # same way the default 3ds Max submitter does. Without this, requirements
    # the artist sets (CPU/memory/GPU) would be silently dropped.
    if host_requirements:
        for step in job_template["steps"]:
            step["hostRequirements"] = host_requirements

    # Inject the per-task run timeout when the artist has configured one. The
    # timeout field on onRun is enforced by the OpenJD session runtime, so a
    # runaway frame is cancelled instead of burning worker time indefinitely.
    if settings.task_run_timeout_seconds > 0:
        for step in job_template["steps"]:
            step["script"]["actions"]["onRun"]["timeout"] = settings.task_run_timeout_seconds

    # Ensure the scene file is uploaded via job attachments.
    asset_references.input_filenames.add(settings.scene_file)
    # Register the output directory as an output (guaranteed non-empty above) so
    # rendered images are captured by job attachments.
    asset_references.output_directories.add(settings.output_path)

    with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as fh:
        deadline_yaml_dump(job_template, fh, indent=1)

    with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as fh:
        deadline_yaml_dump({"parameterValues": parameter_values}, fh, indent=1)

    with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as fh:
        deadline_yaml_dump(asset_references.to_dict(), fh, indent=1)

    _logger.info(f"3dsmaxcmd render job bundle created at: {job_bundle_path}")

    settings.save_sticky_settings()
