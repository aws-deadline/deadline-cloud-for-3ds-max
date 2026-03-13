# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for vrscene_utils pure-logic functions."""

import pytest

from deadline.max_submitter.utilities.vrscene_utils import (
    normalize_output_format,
    validate_output_format,
    get_vrscene_filename,
    get_frame_vrscene_filename,
)


class TestNormalizeOutputFormat:
    """Tests for format string normalization."""

    def test_lowercase(self):
        assert normalize_output_format("PNG") == "png"

    def test_strip_leading_dot(self):
        assert normalize_output_format(".png") == "png"

    def test_dot_and_uppercase(self):
        assert normalize_output_format(".EXR") == "exr"

    def test_whitespace(self):
        assert normalize_output_format("  jpg  ") == "jpg"

    def test_empty_string(self):
        assert normalize_output_format("") == ""

    def test_already_normalized(self):
        assert normalize_output_format("tiff") == "tiff"

    def test_mixed_case_with_dot(self):
        assert normalize_output_format(".Jpeg") == "jpeg"


class TestValidateOutputFormat:
    """Tests for format validation."""

    @pytest.mark.parametrize("fmt", ["png", "exr", "tiff", "tif", "jpg", "jpeg"])
    def test_supported_formats(self, fmt):
        assert validate_output_format(fmt) is True

    @pytest.mark.parametrize("fmt", [".PNG", ".EXR", "TIFF", ".jpg"])
    def test_supported_formats_unnormalized(self, fmt):
        assert validate_output_format(fmt) is True

    @pytest.mark.parametrize("fmt", ["bmp", "gif", "webp", "vrimg", ""])
    def test_unsupported_formats(self, fmt):
        assert validate_output_format(fmt) is False


class TestGetVrsceneFilename:
    """Tests for vrscene filepath generation."""

    def test_basic(self):
        result = get_vrscene_filename("MyScene", "C:/output")
        assert result.endswith("MyScene.vrscene")
        assert "output" in result

    def test_empty_scene_name_defaults_to_untitled(self):
        result = get_vrscene_filename("", "C:/output")
        assert "untitled.vrscene" in result


class TestGetFrameVrsceneFilename:
    """Tests for frame-specific vrscene filename generation."""

    def test_frame_padding(self):
        result = get_frame_vrscene_filename("C:/output/scene.vrscene", 1)
        assert result.endswith("scene.0001.vrscene")

    def test_frame_padding_large_number(self):
        result = get_frame_vrscene_filename("C:/output/scene.vrscene", 1234)
        assert result.endswith("scene.1234.vrscene")

    def test_preserves_directory(self):
        result = get_frame_vrscene_filename("C:/my/path/scene.vrscene", 5)
        assert "my" in result and "path" in result
