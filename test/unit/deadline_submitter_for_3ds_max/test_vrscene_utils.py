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


class TestValidateVrsceneExportSettingsRTParams:
    """Tests for RT engine parameter validation in validate_vrscene_export_settings."""

    def _make_settings(self, render_engine=5, rt_timeout=0.0, rt_noise=0.001, rt_sample_level=0):
        from unittest.mock import MagicMock

        settings = MagicMock()
        settings.export_mode = 2  # Farm export — skip output path check
        settings.frame_list = "1-10"
        settings.vrscene_render_region_columns = 1
        settings.vrscene_render_region_rows = 1
        settings.vrscene_render_engine = render_engine
        settings.vrscene_rt_timeout = rt_timeout
        settings.vrscene_rt_noise = rt_noise
        settings.vrscene_rt_sample_level = rt_sample_level
        return settings

    def _validate(self, settings):
        from deadline.max_submitter.utilities.vrscene_utils import (
            validate_vrscene_export_settings,
        )
        from unittest.mock import patch

        with patch(
            "deadline.max_submitter.utilities.vrscene_utils.is_vray_renderer",
            return_value=True,
        ):
            return validate_vrscene_export_settings(settings)

    def test_valid_gpu_settings(self):
        settings = self._make_settings(render_engine=5, rt_timeout=0.0, rt_noise=0.001)
        errors = self._validate(settings)
        assert errors == []

    def test_negative_timeout_fails(self):
        settings = self._make_settings(render_engine=5, rt_timeout=-1.0)
        errors = self._validate(settings)
        assert any("Timeout" in e for e in errors)

    def test_noise_above_1_fails(self):
        settings = self._make_settings(render_engine=5, rt_noise=1.5)
        errors = self._validate(settings)
        assert any("Noise" in e for e in errors)

    def test_negative_noise_fails(self):
        settings = self._make_settings(render_engine=5, rt_noise=-0.1)
        errors = self._validate(settings)
        assert any("Noise" in e for e in errors)

    def test_negative_sample_level_fails(self):
        settings = self._make_settings(render_engine=5, rt_sample_level=-1)
        errors = self._validate(settings)
        assert any("Samples" in e for e in errors)

    def test_cpu_engine_skips_rt_validation(self):
        # RT params are not validated for CPU engine
        settings = self._make_settings(render_engine=0, rt_timeout=-1.0, rt_noise=2.0)
        errors = self._validate(settings)
        assert errors == []
