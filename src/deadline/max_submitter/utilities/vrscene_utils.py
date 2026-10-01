# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
V-Ray Scene Export Utilities
"""

import logging
import os
from typing import List, Tuple

from pymxs import runtime as rt

_logger = logging.getLogger(__name__)


def is_vray_renderer() -> bool:
    """Check if the current renderer is V-Ray."""
    try:
        renderer_class = str(rt.classof(rt.renderers.current))
        return "VRay" in renderer_class or "V_Ray" in renderer_class
    except Exception:
        return False


def get_vrscene_filename(scene_name: str, output_path: str) -> str:
    """Generate vrscene filepath from scene name and output directory."""
    if not scene_name:
        scene_name = "untitled"

    vrscene_name = f"{scene_name}.vrscene"
    return os.path.join(output_path, vrscene_name)


def get_frame_vrscene_filename(base_path: str, frame: int) -> str:
    """Generate frame-specific vrscene filename (e.g. scene.0001.vrscene)."""
    dir_path = os.path.dirname(base_path)
    base_name = os.path.splitext(os.path.basename(base_path))[0]
    ext = os.path.splitext(base_path)[1]

    padded_frame = f"{frame:04d}"
    return os.path.join(dir_path, f"{base_name}.{padded_frame}{ext}")


def export_vrscene_local(
    vrscene_path: str,
    start_frame: int,
    end_frame: int,
    export_animation_mode: int,
) -> Tuple[bool, str]:
    """Export vrscene file(s) locally. Returns (success, message)."""
    if not is_vray_renderer():
        return False, "Current renderer is not V-Ray. Cannot export vrscene."

    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(vrscene_path), exist_ok=True)

        _logger.info(f"Exporting V-Ray scene to: {vrscene_path}")
        _logger.info(f"Export mode: {export_animation_mode}, Frames: {start_frame}-{end_frame}")

        # Escape backslashes for MAXScript
        vrscene_path_escaped = vrscene_path.replace("\\", "\\\\")
        output_dir_escaped = os.path.dirname(vrscene_path).replace("\\", "\\\\")
        base_name = os.path.splitext(os.path.basename(vrscene_path))[0]

        # Load MAXScript export template and inject runtime values
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "export_vrscene_local.ms"
        )
        with open(script_path, "r") as f:
            template = f.read()
        export_script = template.format(
            export_animation_mode=export_animation_mode,
            start_frame=start_frame,
            end_frame=end_frame,
            vrscene_path_escaped=vrscene_path_escaped,
            output_dir_escaped=output_dir_escaped,
            base_name=base_name,
        )

        result = rt.execute(export_script)

        if result and "SUCCESS" in str(result):
            _logger.info("Successfully exported vrscene")
            return True, vrscene_path
        else:
            error_msg = f"Failed to export vrscene: {result}"
            _logger.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Exception during vrscene export: {str(e)}"
        _logger.error(error_msg)
        return False, error_msg


def validate_vrscene_export_settings(settings) -> List[str]:
    """Validate settings, return list of error messages (empty if valid).

    Validation is centralised here rather than in the UI so it also runs
    inside the job-bundle callback, catching invalid values regardless of
    how the settings were constructed.
    """
    errors = []

    # Check if V-Ray is the current renderer
    if not is_vray_renderer():
        errors.append("V-Ray scene export requires V-Ray as the active renderer")
        return errors

    # Validate output path
    if settings.export_mode == 1:  # Local export
        output_dir = settings.output_path
        if not output_dir:
            errors.append("Output path cannot be empty")
        else:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot write to output directory: {output_dir} - {str(e)}")

    # Validate frame range
    if not settings.frame_list or not settings.frame_list.strip():
        errors.append("Frame range cannot be empty")

    # Validate region settings
    if settings.vrscene_render_region_columns < 1 or settings.vrscene_render_region_columns > 10:
        errors.append("Region columns must be between 1 and 10")

    if settings.vrscene_render_region_rows < 1 or settings.vrscene_render_region_rows > 10:
        errors.append("Region rows must be between 1 and 10")

    # Validate render engine
    from data_const import VRAY_ENGINE_ALLOWED

    if settings.vrscene_render_engine not in VRAY_ENGINE_ALLOWED:
        errors.append(
            f"Invalid render engine: {settings.vrscene_render_engine}. "
            f"Must be one of {VRAY_ENGINE_ALLOWED} (0=CPU, 5=CUDA, 7=RTX)"
        )

    # Validate RT engine parameters (only relevant for GPU engines)
    if settings.vrscene_render_engine != 0:
        if settings.vrscene_rt_timeout < 0:
            errors.append("RT Frame Timeout must be >= 0 (0 = no limit)")
        if not (0.0 <= settings.vrscene_rt_noise <= 1.0):
            errors.append("RT Noise Threshold must be between 0.0 and 1.0")
        if settings.vrscene_rt_sample_level < 0:
            errors.append("RT Max Samples must be >= 0 (0 = no limit)")

    return errors


def get_output_format_from_scene() -> str:
    """Auto-detect output format from 3ds Max render settings. Defaults to 'png'."""
    try:
        # Query 3ds Max render output filename
        output_filename = rt.rendOutputFilename

        if output_filename and str(output_filename).strip():
            # Extract extension
            _, ext = os.path.splitext(str(output_filename))

            if ext:
                # Normalize and validate
                normalized = normalize_output_format(ext)
                if validate_output_format(normalized):
                    _logger.info(f"Detected output format from scene: {normalized}")
                    return normalized

        _logger.info("No output format detected, defaulting to png")
        return "png"

    except Exception as e:
        _logger.warning(f"Error detecting output format: {e}, defaulting to png")
        return "png"


def validate_output_format(format_str: str) -> bool:
    """Check if format is supported (png, exr, tiff, tif, jpg, jpeg)."""
    # Normalize first
    normalized = normalize_output_format(format_str)

    # List of supported formats
    supported_formats = {"png", "exr", "tiff", "tif", "jpg", "jpeg"}

    return normalized in supported_formats


def normalize_output_format(format_str: str) -> str:
    """Normalize format to lowercase without leading dot (e.g. '.PNG' -> 'png')."""
    if not format_str:
        return ""

    # Convert to string and strip whitespace
    normalized = str(format_str).strip().lower()

    # Remove leading dot if present
    if normalized.startswith("."):
        normalized = normalized[1:]

    return normalized
