# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Shared output filename utilities for Deadline Cloud 3ds Max integration.

Provides token-based output filename formatting.
Everything else in the pattern is literal text (base name, frame padding, delimiters).
"""

# Single source of truth for supported tokens and their descriptions.
# Add new tokens here — the UI tooltip and replacement logic both read from this.
SUPPORTED_TOKENS: dict[str, str] = {
    "<camera>": "Scene camera name (e.g., Camera001, RenderCam)",
    "<stateset>": "State set name",
    "<scene>": "Scene file name (without extension)",
}


def get_tokens_tooltip() -> str:
    """Build a tooltip string describing all supported tokens."""
    lines = ["Available tokens:"]
    for token, desc in SUPPORTED_TOKENS.items():
        lines.append(f"  {token}  — {desc}")
    lines.append("")
    lines.append("Everything else is literal text.")
    lines.append("Remove a token to exclude it from the filename.")
    lines.append("Examples:")
    lines.append("  <camera>_<stateset>_<scene>_###")
    lines.append("  <camera>_<stateset>_myRender_###")
    lines.append("  <scene>_###")
    lines.append("  myScene_###")
    return "\n".join(lines)


def format_output_filename(
    pattern: str,
    camera_name: str = "",
    state_set_name: str = "",
    scene_name: str = "",
) -> str:
    """
    Resolve an output filename from a token pattern.

    Replaces <camera>, <stateset>, and <scene> tokens with their actual values.
    No additional cleanup is performed — what you see is what you get.

    Examples:
        >>> format_output_filename(
        ...     "<camera>_<stateset>_<scene>_###",
        ...     camera_name="RenderCam", state_set_name="DayLight", scene_name="myScene")
        'RenderCam_DayLight_myScene_###'

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

    return result
