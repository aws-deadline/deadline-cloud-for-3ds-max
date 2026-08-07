# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
V-Ray Standalone Job Submission Utilities
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

# These generic helpers now live in a renderer-agnostic module. They are
# re-exported here under their original private names so existing V-Ray call
# sites keep working unchanged.
from utilities.job_template_utils import inject_embedded_script as _inject_embedded_script
from utilities.job_template_utils import load_job_template as _load_job_template


def calculate_region_coordinates(
    column: int,
    row: int,
    total_columns: int,
    total_rows: int,
    image_width: int,
    image_height: int,
) -> Tuple[int, int, int, int]:
    """
    Calculate pixel-based region coordinates for a tile (Deadline 10 style).
    Top-left origin, exclusive end coordinates. Last tile gets remainder pixels.

    Returns (xStart, yStart, xEnd, yEnd) in pixels.
    """
    if total_columns < 1 or total_rows < 1:
        raise ValueError(f"Grid must be at least 1x1, got {total_columns}x{total_rows}")
    if image_width < 1 or image_height < 1:
        raise ValueError(f"Image must be at least 1x1, got {image_width}x{image_height}")
    if column < 0 or column >= total_columns:
        raise ValueError(f"Column {column} out of bounds for {total_columns} columns")
    if row < 0 or row >= total_rows:
        raise ValueError(f"Row {row} out of bounds for {total_rows} rows")

    delta_x, remainder_x = divmod(image_width, total_columns)
    delta_y, remainder_y = divmod(image_height, total_rows)

    if delta_x < 1 or delta_y < 1:
        raise ValueError(
            f"Image {image_width}x{image_height} too small for {total_columns}x{total_rows} grid"
        )

    # Region boundaries
    x_start = delta_x * column
    x_end = delta_x * (column + 1)
    y_start = delta_y * row
    y_end = delta_y * (row + 1)

    # Last tile gets remainder
    if column == total_columns - 1:
        x_end += remainder_x
    if row == total_rows - 1:
        y_end += remainder_y

    return (x_start, y_start, x_end, y_end)


def get_tile_index(column: int, row: int, total_columns: int) -> int:
    """Row-major tile index: row * cols + col."""
    return row * total_columns + column


def _get_tile_render_script() -> str:
    """Reads the tile_render.py script from the scripts directory."""
    script_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
    script_path = os.path.join(script_dir, "tile_render.py")
    with open(script_path, "r") as f:
        return f.read()


def _get_tile_merge_script() -> str:
    """Reads the tile_merge.py script from the scripts directory."""
    script_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
    script_path = os.path.join(script_dir, "tile_merge.py")
    with open(script_path, "r") as f:
        return f.read()


def create_tile_rendering_job_template(
    settings,
    vrscene_path: str,
    output_filename: str,
    start_frame: int,
    end_frame: int,
) -> Dict[str, Any]:
    """
    Create job template with tile rendering steps. Loaded from YAML.

    Steps: RenderRegions (N×M tasks/frame) → MergeRegions (1 task/frame).
    """
    template = _load_job_template("vray_tile_render_job_template.yaml")
    template["name"] = f"{settings.name} - VRay Tile Render"

    # Inject embedded scripts
    _inject_embedded_script(template, "INJECT_TILE_RENDER_SCRIPT", _get_tile_render_script())
    _inject_embedded_script(template, "INJECT_TILE_MERGE_SCRIPT", _get_tile_merge_script())

    # Set dynamic parameter defaults from settings
    if start_frame == end_frame:
        frames = str(start_frame)
    else:
        frames = f"{start_frame}-{end_frame}"

    defaults = {
        "OutputFileName": output_filename,
        "Frames": frames,
        "ImageWidth": str(settings.image_width),
        "ImageHeight": str(settings.image_height),
        "RegionColumns": str(settings.vrscene_render_region_columns),
        "RegionRows": str(settings.vrscene_render_region_rows),
        "CreateMovie": "true" if settings.vrscene_create_movie else "false",
        "MovieFilename": settings.vrscene_movie_filename,
        "FrameRate": str(settings.vrscene_movie_framerate),
    }
    for param in template.get("parameterDefinitions", []):
        if param["name"] in defaults:
            param["default"] = defaults[param["name"]]

    return template


def _get_create_movie_script() -> str:
    """Reads the create_movie.py script from the scripts directory."""
    script_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
    script_path = os.path.join(script_dir, "create_movie.py")
    with open(script_path, "r") as f:
        return f.read()


def create_vrscene_render_job_parameters(
    settings,
    vrscene_path: str,
    output_path: str,
    output_filename: str,
    start_frame: int,
    end_frame: int,
    vray_executable: str,
) -> List[Dict[str, Any]]:
    """Create parameter values for vrscene render job."""
    # Determine frame range string
    if start_frame == end_frame:
        frames = str(start_frame)
    else:
        frames = f"{start_frame}-{end_frame}"

    parameters = [
        {"name": "VRayExecutable", "value": vray_executable},
        {"name": "VRSceneOutputPath", "value": vrscene_path},
        {"name": "OutputDir", "value": output_path},
        {"name": "OutputFileName", "value": output_filename},
        {"name": "Frames", "value": frames},
        {"name": "RegionColumns", "value": str(settings.vrscene_render_region_columns)},
        {"name": "RegionRows", "value": str(settings.vrscene_render_region_rows)},
        {"name": "RenderEngine", "value": str(settings.vrscene_render_engine)},
        {"name": "RTTimeout", "value": str(settings.vrscene_rt_timeout)},
        {"name": "RTNoise", "value": str(settings.vrscene_rt_noise)},
        {"name": "RTSampleLevel", "value": str(settings.vrscene_rt_sample_level)},
    ]

    return parameters


def create_export_job_parameters(
    settings,
    vrscene_path: str,
    start_frame: int,
    end_frame: int,
) -> List[Dict[str, Any]]:
    """Create parameter values for vrscene export job (farm mode)."""
    parameters = [
        {"name": "SceneFile", "value": settings.scene_file},
        {"name": "VRSceneOutputPath", "value": vrscene_path},
        {"name": "StartFrame", "value": str(start_frame)},
        {"name": "EndFrame", "value": str(end_frame)},
        {"name": "ExportAnimationMode", "value": str(settings.export_animation_mode)},
    ]

    return parameters


def get_frame_range_from_string(frame_string: str) -> Tuple[int, int]:
    """Parse frame range string (e.g. "1-100") and return (start, end)."""
    # Handle simple cases
    if "-" in frame_string:
        parts = frame_string.split("-")
        start = int(parts[0].split(",")[-1].strip())
        end = int(parts[-1].split(",")[0].strip())
        return start, end
    elif "," in frame_string:
        frames = [int(f.strip()) for f in frame_string.split(",")]
        return min(frames), max(frames)
    else:
        frame = int(frame_string.strip())
        return frame, frame


def create_export_job_template() -> Dict[str, Any]:
    """Create job template for vrscene export job (farm mode). Loaded from YAML."""
    template = _load_job_template("vray_export_job_template.yaml")
    _inject_embedded_script(template, "INJECT_EXPORT_SCRIPT", _get_export_script_content())
    return template


def _get_export_script_content() -> str:
    """Read the MAXScript export script from the scripts directory."""
    script_path = Path(__file__).parent.parent / "scripts" / "export_vrscene_farm.ms"
    if not script_path.exists():
        raise FileNotFoundError(f"Export script not found at {script_path}")
    with open(script_path, "r") as f:
        return f.read()
