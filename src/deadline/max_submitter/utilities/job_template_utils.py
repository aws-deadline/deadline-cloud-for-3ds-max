# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Generic job-bundle template helpers.

These utilities are renderer-agnostic: they load a YAML job template from the
job_templates directory and substitute embedded-script placeholders. They live
here (rather than in a renderer-specific module) so any submitter workflow can
use them without depending on another workflow's internals.
"""

from pathlib import Path

import yaml

_TEMPLATE_DIR = Path(__file__).parent.parent / "job_templates"


def load_job_template(template_name: str) -> dict:
    """Load a YAML job template from the job_templates directory."""
    with open(_TEMPLATE_DIR / template_name) as fh:
        return yaml.safe_load(fh)


def inject_embedded_script(template: dict, placeholder: str, script_content: str) -> None:
    """Replace a placeholder string in embedded file data fields with actual script content."""
    for step in template.get("steps", []):
        # Check step-level script
        script_section = step.get("script", {})
        for ef in script_section.get("embeddedFiles", []):
            if ef.get("data") == placeholder:
                ef["data"] = script_content
        # Check stepEnvironments
        for env in step.get("stepEnvironments", []):
            env_script = env.get("script", {})
            for ef in env_script.get("embeddedFiles", []):
                if ef.get("data") == placeholder:
                    ef["data"] = script_content
