# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for deadline.max_shared.utilities.filename_utils

Covers the output filename token formatting.
"""

from deadline.max_shared.utilities.filename_utils import (
    SUPPORTED_TOKENS,
    format_output_filename,
    get_tokens_tooltip,
)


class TestSupportedTokens:
    def test_contains_expected_tokens(self) -> None:
        assert "<camera>" in SUPPORTED_TOKENS
        assert "<stateset>" in SUPPORTED_TOKENS
        assert "<scene>" in SUPPORTED_TOKENS

    def test_all_values_are_strings(self) -> None:
        for token, desc in SUPPORTED_TOKENS.items():
            assert isinstance(token, str)
            assert isinstance(desc, str)


class TestGetTokensTooltip:
    def test_contains_all_tokens(self) -> None:
        tooltip = get_tokens_tooltip()
        for token in SUPPORTED_TOKENS:
            assert token in tooltip

    def test_contains_all_descriptions(self) -> None:
        tooltip = get_tokens_tooltip()
        for desc in SUPPORTED_TOKENS.values():
            assert desc in tooltip

    def test_starts_with_header(self) -> None:
        tooltip = get_tokens_tooltip()
        assert tooltip.startswith("Available tokens:")


class TestFormatOutputFilename:
    def test_all_tokens_filled(self) -> None:
        result = format_output_filename(
            "<camera>_<stateset>_<scene>_###",
            camera_name="RenderCam",
            state_set_name="DayLight",
            scene_name="myScene",
        )
        assert result == "RenderCam_DayLight_myScene_###"

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
        """Only camera filled — other tokens become empty strings, delimiters remain."""
        result = format_output_filename(
            "<camera>_<stateset>_<scene>_###",
            camera_name="Cam1",
        )
        assert result == "Cam1___###"

    def test_empty_pattern(self) -> None:
        assert format_output_filename("") == ""

    def test_all_tokens_empty(self) -> None:
        """All tokens empty — only literal delimiters and padding remain."""
        result = format_output_filename(
            "<camera>_<stateset>_<scene>_###",
            camera_name="",
            state_set_name="",
            scene_name="",
        )
        assert result == "___###"
