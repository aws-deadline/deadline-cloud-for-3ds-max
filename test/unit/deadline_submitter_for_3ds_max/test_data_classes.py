# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for deadline.max_submitter.data_classes

Covers the changes made to RenderSubmitterUISettings:
- output_filename_pattern field exists with correct default and sticky metadata
- last_rend_output_filename field is removed
"""

import dataclasses

from deadline.max_submitter.data_classes import RenderSubmitterUISettings


class TestOutputFilenamePattern:
    """Tests for the output_filename_pattern field."""

    def test_field_exists(self) -> None:
        settings = RenderSubmitterUISettings()
        assert hasattr(settings, "output_filename_pattern")

    def test_default_value(self) -> None:
        settings = RenderSubmitterUISettings()
        assert settings.output_filename_pattern == "<camera>_<stateset>_<scene>_###"

    def test_is_sticky(self) -> None:
        fields = {f.name: f for f in dataclasses.fields(RenderSubmitterUISettings)}
        assert fields["output_filename_pattern"].metadata.get("sticky") is True


class TestLastRendOutputFilenameRemoved:
    """Verify that the removed field is no longer present."""

    def test_no_last_rend_output_filename_field(self) -> None:
        field_names = {f.name for f in dataclasses.fields(RenderSubmitterUISettings)}
        assert "last_rend_output_filename" not in field_names

    def test_no_last_rend_output_filename_attr(self) -> None:
        settings = RenderSubmitterUISettings()
        assert not hasattr(settings, "last_rend_output_filename")
