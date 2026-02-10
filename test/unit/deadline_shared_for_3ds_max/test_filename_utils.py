# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for deadline.max_shared.utilities.filename_utils

Covers the new output filename token formatting and frame padding logic
added in the "fix: incorrect output filenames" commit.
"""

import pytest

from deadline.max_shared.utilities.filename_utils import (
    ensure_frame_padding,
    format_output_filename,
    is_single_frame,
)


# ============================================================================
# is_single_frame
# ============================================================================


@pytest.mark.parametrize(
    "frame_range,expected",
    [
        ("0", True),
        ("5", True),
        ("100", True),
        ("1-10", False),
        ("1,3,5", False),
        ("1,3,5-12", False),
        ("", False),
    ],
)
def test_is_single_frame(frame_range: str, expected: bool) -> None:
    assert is_single_frame(frame_range) is expected


# ============================================================================
# ensure_frame_padding
# ============================================================================


@pytest.mark.parametrize(
    "pattern,frame_range,expected",
    [
        # Single frame — strip padding
        ("myRender_####", "0", "myRender"),
        ("myRender_###", "5", "myRender"),
        # Single frame — no padding to strip
        ("myRender", "0", "myRender"),
        # Multi-frame — padding already present
        ("myRender_####", "1-10", "myRender_####"),
        ("myRender_###", "1,3,5", "myRender_###"),
        # Multi-frame — padding auto-added
        ("myRender", "1-10", "myRender_####"),
        ("myRender", "0,5,10", "myRender_####"),
    ],
)
def test_ensure_frame_padding(pattern: str, frame_range: str, expected: str) -> None:
    assert ensure_frame_padding(pattern, frame_range) == expected


# ============================================================================
# format_output_filename
# ============================================================================


class TestFormatOutputFilename:
    def test_all_tokens_filled(self) -> None:
        result = format_output_filename(
            "<camera>_<stateset>_<scene>_###",
            camera_name="RenderCam",
            state_set_name="DayLight",
            scene_name="myScene",
        )
        assert result == "RenderCam_DayLight_myScene_###"

    def test_empty_tokens_cleaned_up(self) -> None:
        """Empty tokens should not leave double underscores or leading/trailing underscores."""
        result = format_output_filename(
            "<camera>_<stateset>_<scene>_###",
            camera_name="",
            state_set_name="",
            scene_name="myScene",
        )
        assert result == "myScene_###"

    def test_no_tokens(self) -> None:
        result = format_output_filename("myRender_###")
        assert result == "myRender_###"

    def test_partial_tokens(self) -> None:
        result = format_output_filename(
            "<camera>_<stateset>_myRender_###",
            camera_name="RenderCam",
            state_set_name="DayLight",
        )
        assert result == "RenderCam_DayLight_myRender_###"

    def test_only_camera(self) -> None:
        result = format_output_filename(
            "<camera>_<stateset>_<scene>_###",
            camera_name="Cam1",
        )
        assert result == "Cam1_###"

    def test_empty_pattern(self) -> None:
        assert format_output_filename("") == ""

    def test_all_tokens_empty(self) -> None:
        """All tokens empty should still return the literal parts."""
        result = format_output_filename(
            "<camera>_<stateset>_<scene>_###",
            camera_name="",
            state_set_name="",
            scene_name="",
        )
        assert result == "###"
