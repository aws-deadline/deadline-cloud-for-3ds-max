# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
V-Ray Standalone Job Submission Utilities
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from openjd.model import IntRangeExpr

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
    frames: str,
) -> Dict[str, Any]:
    """
    Create job template with tile rendering steps. Loaded from YAML.

    Steps: RenderRegions (N×M tasks/frame) → MergeRegions (1 task/frame).

    ``frames`` is the OpenJD ``Frames`` value (see
    :func:`build_frames_parameter`) and may be non-contiguous, e.g.
    ``"1-3,8,11-12"``.
    """
    template = _load_job_template("vray_tile_render_job_template.yaml")
    template["name"] = f"{settings.name} - VRay Tile Render"

    # Inject embedded scripts
    _inject_embedded_script(template, "INJECT_TILE_RENDER_SCRIPT", _get_tile_render_script())
    _inject_embedded_script(template, "INJECT_TILE_MERGE_SCRIPT", _get_tile_merge_script())

    # Set dynamic parameter defaults from settings
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
    frames: str,
    vray_executable: str,
) -> List[Dict[str, Any]]:
    """Create parameter values for vrscene render job.

    ``frames`` is the OpenJD ``Frames`` value (see
    :func:`build_frames_parameter`) and may be non-contiguous, e.g.
    ``"1-3,8,11-12"``.
    """
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


def expand_frame_list(frame_string: str) -> List[int]:
    """Expand a frame string into a sorted, de-duplicated list of frames.

    Supports single frames, contiguous ranges and non-contiguous mixes, e.g.
    "5" -> [5], "1-3" -> [1, 2, 3], "1-3,8,11-12" -> [1, 2, 3, 8, 11, 12].

    :param frame_string: frame specification (numbers, commas, dashes)
    :return: sorted list of unique integer frames
    :raises ValueError: if the string is empty or cannot be parsed
    """
    if not frame_string or not frame_string.strip():
        raise ValueError("Frame string cannot be empty")

    frames: set[int] = set()
    for group in frame_string.strip().split(","):
        group = group.strip()
        if not group:
            continue
        if "-" in group:
            start_str, end_str = group.split("-", 1)
            start, end = int(start_str.strip()), int(end_str.strip())
            if end < start:
                start, end = end, start
            frames.update(range(start, end + 1))
        else:
            frames.add(int(group))

    if not frames:
        raise ValueError(f"No frames parsed from '{frame_string}'")

    return sorted(frames)


def build_frames_parameter(frame_string: str) -> str:
    """Build the OpenJD ``Frames`` parameter value from a frame string,
    preserving non-contiguous gaps.

    The heavy lifting is delegated to OpenJD's own range engine
    (:class:`openjd.model.IntRangeExpr`) so the emitted value is guaranteed to
    be a valid OpenJD range expression that the framework can fan out into one
    task per frame. OpenJD also validates, de-duplicates, sorts and (where
    possible) compacts the frames, and natively understands step syntax such
    as ``"1-10:2"``.

    Two-tier strategy:

    1. Fast path -- hand the raw string to :meth:`IntRangeExpr.from_str`. This
       covers well-formed input directly, including step ranges.
    2. Artist-friendly fallback -- OpenJD rejects input that is otherwise
       reasonable for an artist to type (unordered, overlapping, duplicate or
       reversed ranges, e.g. ``"1-5,3-7"`` or ``"5-1"``). For those we expand
       to an explicit frame list with :func:`expand_frame_list` and let
       :meth:`IntRangeExpr.from_list` sort, de-duplicate and normalize it.

    Examples: ``"1-100"`` -> ``"1-100"``, ``"1-10,15,18-20,21"`` ->
    ``"1-10,15,18-21"``, ``"5-1"`` -> ``"1-5"``.

    :param frame_string: frame specification (numbers, commas, dashes, steps)
    :return: a valid OpenJD ``Frames`` value covering exactly the unique frames
    :raises ValueError: if the string is empty or cannot be parsed at all
    """
    if not frame_string or not frame_string.strip():
        raise ValueError("Frame string cannot be empty")

    try:
        # OpenJD parses, validates and compacts well-formed range strings.
        return str(IntRangeExpr.from_str(frame_string.strip()))
    except Exception:
        # Fall back for artist input OpenJD won't accept as-is; expand to an
        # explicit list and let OpenJD normalize it. expand_frame_list raises
        # ValueError if the input can't be parsed at all.
        return str(IntRangeExpr.from_list(expand_frame_list(frame_string)))


def get_frame_range_from_string(frame_string: str) -> Tuple[int, int]:
    """Parse a frame string and return its bounding (start, end).

    Handles non-contiguous input by returning the min/max, e.g.
    "1-10,20-30" -> (1, 30). Use :func:`expand_frame_list` when the exact
    set of frames (without gap filling) is required.
    """
    frames = expand_frame_list(frame_string)
    return frames[0], frames[-1]


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
