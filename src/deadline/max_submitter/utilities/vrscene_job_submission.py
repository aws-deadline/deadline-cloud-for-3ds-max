# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
V-Ray Standalone Job Submission Utilities
"""

import os
import re
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


# One comma-separated frame group: a frame, a range, or a range with a step.
# The sign is part of each number rather than a separator, so "-5--1" parses as
# -5 to -1: 3ds Max allows negative animation ranges and get_frames() passes
# rt.animationrange.start straight through.
_FRAME_GROUP_RE = re.compile(
    r"^(?P<start>-?\d+)" r"(?:\s*-\s*(?P<end>-?\d+)" r"(?:\s*:\s*(?P<step>-?\d+))?" r")?$"
)


def parse_frame_groups(frame_string: str) -> List[Tuple[int, int]]:
    """Parse a frame string into the (low, high) span of each comma-separated group.

    Accepts the forms OpenJD's range expression accepts, which is what consumes
    the ``Frames`` job parameter via ``range: '{{Param.Frames}}'``:

    * a single frame, including zero and negatives -- ``5``, ``0``, ``-5``
    * a range -- ``1-10``, ``-5--1``
    * a range with a step -- ``1-10:2``, ``10-1:-2``

    Only the endpoints are inspected, never the frames between them, so the cost
    is proportional to the number of groups rather than the size of the span. That
    matters because this runs on the raw frame-list field: expanding it would let a
    typo such as ``1-100000000`` allocate a hundred million integers inside the
    3ds Max process, several GB and a long freeze with no feedback. A string-length
    limit does not help, because ``1-100000000`` is only eleven characters.

    :param frame_string: frame specification
    :return: one (low, high) pair per group, in the order written
    :raises ValueError: if the string is empty or any group is malformed
    """
    if not frame_string or not frame_string.strip():
        raise ValueError("Frame range cannot be empty")

    spans: List[Tuple[int, int]] = []
    for group in frame_string.strip().split(","):
        group = group.strip()
        if not group:
            raise ValueError(f"Empty frame group in '{frame_string}'")

        match = _FRAME_GROUP_RE.match(group)
        if not match:
            raise ValueError(
                f"'{group}' is not a frame or frame range. Use a frame (5), "
                "a range (1-10), or a range with a step (1-10:2)."
            )

        start = int(match.group("start"))
        end_text, step_text = match.group("end"), match.group("step")
        if end_text is None:
            spans.append((start, start))
            continue

        end = int(end_text)
        if step_text is None:
            # Matches OpenJD: without an explicit step the range must ascend.
            if end < start:
                raise ValueError(
                    f"'{group}' counts down, so it needs a negative step: "
                    f"write '{start}-{end}:-1' if that is what you meant."
                )
        else:
            step = int(step_text)
            if step == 0:
                raise ValueError(f"'{group}' has a step of zero, which renders no frames.")
            if step > 0 and end < start:
                raise ValueError(f"'{group}' counts down but its step is positive.")
            if step < 0 and end > start:
                raise ValueError(f"'{group}' counts up but its step is negative.")

        spans.append((min(start, end), max(start, end)))

    return spans


def validate_frame_string(frame_string: str) -> List[str]:
    """Check a frame string the way OpenJD will, and describe any problem plainly.

    The frame list is passed to the service verbatim as the ``Frames`` job
    parameter, so OpenJD is what ultimately judges it. Rather than pre-processing
    the value into something OpenJD is guaranteed to like -- which would mean
    guessing at what the artist meant -- this reports the problem so it can be
    corrected before anything is submitted.

    The rules mirror OpenJD's, established by exercising its parser directly:
    groups may appear in any order and gaps are fine, but two groups may not
    overlap, and the comparison is on each group's *span*. ``1-10:2,2-10:2`` is
    rejected even though the frames themselves are disjoint, so spans are the
    right unit here, and no range ever has to be expanded to check.

    :param frame_string: frame specification
    :return: a list of human-readable problems; empty when the value is usable
    """
    try:
        spans = parse_frame_groups(frame_string)
    except ValueError as exc:
        return [str(exc)]

    errors: List[str] = []
    ordered = sorted(spans)
    for (previous_low, previous_high), (low, high) in zip(ordered, ordered[1:]):
        if low <= previous_high:
            errors.append(_describe_overlap(previous_low, previous_high, low, high))
    return errors


def _describe_overlap(previous_low: int, previous_high: int, low: int, high: int) -> str:
    """Word an overlap the way it reads best for the shapes involved.

    Spans arrive sorted, so the second one starts at or after the first. Phrasing
    each combination separately avoids sentences like "Frames 5 overlap frames 5",
    which is what a single template produces for a repeated single frame.
    """
    single_previous = previous_low == previous_high
    single_current = low == high

    if single_current and single_previous:
        # Already says everything the guidance below would add.
        return f"Frame {low} is listed more than once."
    if single_current:
        detail = f"Frame {low} is already covered by {previous_low}-{previous_high}."
    elif single_previous:
        detail = f"Frames {low}-{high} already include frame {previous_low}."
    else:
        detail = f"Frames {low}-{high} overlap frames {previous_low}-{previous_high}."

    return detail + " Each frame may only be listed once."


def get_frame_range_from_string(frame_string: str) -> Tuple[int, int]:
    """Parse a frame string and return its bounding (start, end).

    Handles non-contiguous input by returning the true min/max, e.g.
    "1-10,20-30" -> (1, 30) and "1-3,6,8" -> (1, 8).

    Used for the vrscene export, which needs a first and last frame rather than
    the exact set. The exact set is never needed on this path: the frame string
    goes to the service verbatim as the ``Frames`` job parameter and OpenJD fans
    it out into tasks.

    :param frame_string: frame specification
    :return: (start, end) bounding the requested frames
    :raises ValueError: if the string is empty or cannot be parsed
    """
    spans = parse_frame_groups(frame_string)
    return min(low for low, _ in spans), max(high for _, high in spans)


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
