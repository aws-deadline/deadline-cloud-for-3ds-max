# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
V-Ray Standalone Job Submission Utilities
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Shipped in the submitter bundle (see scripts/deps_bundle.py). Imported at module
# scope deliberately: if it is missing, the frame list cannot be checked against
# the rules the service applies, and failing loudly here is better than validating
# by some approximation of them.
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

    ``frames`` is the OpenJD ``Frames`` value, handed to
    ``range: '{{Param.Frames}}'`` verbatim. It is the artist's own text with
    only the ends trimmed, checked by :func:`validate_frame_string` before
    submission, and may be non-contiguous, e.g. ``"1-3,8,11-12"``.
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

    ``frames`` is the OpenJD ``Frames`` value, handed to
    ``range: '{{Param.Frames}}'`` verbatim. It is the artist's own text with
    only the ends trimmed, checked by :func:`validate_frame_string` before
    submission, and may be non-contiguous, e.g. ``"1-3,8,11-12"``.
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


def validate_frame_string(frame_string: str) -> List[str]:
    """Check a frame string with the parser that will judge it, and report plainly.

    The frame list is passed to the service verbatim as the ``Frames`` job
    parameter and consumed as ``range: '{{Param.Frames}}'``, so OpenJD's range
    expression is what decides whether it is usable. Asking that parser directly
    is the only way to be certain the answer matches: a second implementation
    here could only ever approximate it, and every gap would show up as a
    submit-time rejection of a value the artist was told was fine.

    Only the wording is ours. OpenJD reports an overlap or a duplicate as
    "Failed to create IntRangeExpr", which is no use to an artist, so its text is
    quoted after a sentence that names the rules instead.

    :param frame_string: frame specification
    :return: a list of human-readable problems; empty when the value is usable
    """
    if not frame_string or not frame_string.strip():
        return ["Frame range cannot be empty"]

    value = frame_string.strip()
    try:
        IntRangeExpr.from_str(value)
    except Exception as exc:
        return [
            f"'{value}' is not a frame range the service accepts. Use plain digits: "
            "a frame (5), a range (1-10), or a range with a step (1-10:2). Ranges may "
            "not overlap and each frame may be listed only once, and a descending "
            "range needs a negative step (10-1:-1). "
            f"The parser reported: {exc}"
        ]
    return []


def get_frame_range_from_string(frame_string: str) -> Tuple[int, int]:
    """Parse a frame string and return the lowest and highest frame in it.

    Handles non-contiguous input, e.g. "1-10,20-30" -> (1, 30) and "1-3,6,8" ->
    (1, 8). Used for the vrscene export, which needs a first and last frame
    rather than the exact set; the exact set never matters on this path, because
    the frame string goes to the service verbatim as the ``Frames`` job parameter
    and OpenJD fans it out into tasks.

    ``start`` and ``end`` are taken from the expression's own properties, which
    read the first and last of its sorted, direction-normalised groups. Indexing
    the expression instead would be wrong as well as slower: groups sort by their
    low end but a descending group still iterates high to low, so for
    "1-5,30-20:-1" the last element is 20 while the highest frame is 30 -- the
    export would then miss every frame the render job still has a task for.

    The properties are also O(1). This runs on the raw frame-list field, so a
    typo such as an extra zero must not expand: "1-1000000000" is eleven
    characters and a billion frames.

    :param frame_string: frame specification
    :return: (lowest, highest) of the requested frames
    :raises ValueError: if the string is empty or OpenJD cannot parse it
    """
    if not frame_string or not frame_string.strip():
        raise ValueError("Frame range cannot be empty")

    expression = IntRangeExpr.from_str(frame_string.strip())
    return expression.start, expression.end


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
