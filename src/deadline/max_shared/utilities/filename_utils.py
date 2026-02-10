# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Shared output filename utilities for Deadline Cloud 3ds Max integration.

Provides token-based output filename formatting.

Supported tokens:
    <camera>   — Scene camera name (e.g., "Camera001", "RenderCam")
    <stateset> — State Set name (e.g., "DayLight", "NightTime")
    <scene>    — Scene file name without extension (e.g., "myScene")

Everything else in the pattern is literal text (base name, frame padding, delimiters).
"""

# Hardcoded delimiter for cleanup
_DELIMITER = "_"

# Default frame padding when auto-added for multi-frame ranges
_DEFAULT_FRAME_PADDING = "####"


def is_single_frame(frame_range: str) -> bool:
    """
    Check if a frame range string represents a single frame.

    :param frame_range: frame range string (e.g., "5", "1-10", "1,3,5")
    :returns: True if the range is a single frame
    """
    return bool(frame_range) and "-" not in frame_range and "," not in frame_range


def ensure_frame_padding(pattern: str, frame_range: str) -> str:
    """
    Ensure the output filename pattern has appropriate frame padding.

    If the frame range is a single frame, any existing # padding is stripped.
    If the frame range is multiple frames and no # padding exists, #### is appended.

    :param pattern: the output filename pattern
    :param frame_range: the frame range string (e.g., "0", "1-10", "1,3,5-12")
    :returns: the pattern with appropriate frame padding
    """
    has_padding = "#" in pattern

    if is_single_frame(frame_range):
        # Single frame — strip any # padding
        if has_padding:
            pattern = pattern.rstrip("#").rstrip(_DELIMITER)
        return pattern
    else:
        # Multi-frame — ensure padding exists
        if not has_padding:
            return f"{pattern}{_DELIMITER}{_DEFAULT_FRAME_PADDING}"
        return pattern


def format_output_filename(
    pattern: str,
    camera_name: str = "",
    state_set_name: str = "",
    scene_name: str = "",
) -> str:
    """
    Resolve an output filename from a token pattern.

    Replaces <camera>, <stateset>, and <scene> tokens with actual values,
    then cleans up double underscores and leading/trailing underscores
    that result from empty token values.

    Examples:
        >>> format_output_filename(
        ...     "<camera>_<stateset>_<scene>_###",
        ...     camera_name="RenderCam", state_set_name="DayLight", scene_name="myScene")
        'RenderCam_DayLight_myScene_###'

        >>> format_output_filename(
        ...     "<camera>_<stateset>_<scene>_###",
        ...     camera_name="", state_set_name="", scene_name="myScene")
        'myScene_###'

        >>> format_output_filename(
        ...     "<camera>_<stateset>_myRender_###",
        ...     camera_name="RenderCam", state_set_name="DayLight")
        'RenderCam_DayLight_myRender_###'

        >>> format_output_filename("myRender_###")
        'myRender_###'

    :param pattern: the full filename pattern with optional tokens
    :param camera_name: the scene camera name, or "" if not applicable
    :param state_set_name: the state set name, or "" if not applicable
    :param scene_name: the scene file name (no extension), or "" if not applicable
    :returns: the resolved filename string
    """
    if not pattern:
        return ""

    result = pattern
    result = result.replace("<camera>", camera_name)
    result = result.replace("<stateset>", state_set_name)
    result = result.replace("<scene>", scene_name)

    # Collapse runs of the delimiter into a single delimiter
    double = _DELIMITER + _DELIMITER
    while double in result:
        result = result.replace(double, _DELIMITER)

    # Strip leading/trailing delimiters
    result = result.strip(_DELIMITER)

    return result
