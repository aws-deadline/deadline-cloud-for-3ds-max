# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for deadline.max_submitter.data_classes
"""

import dataclasses
import json
from unittest.mock import patch, mock_open

import pytest

from deadline.max_submitter.data_classes import (
    StepData,
    StateSetData,
    BatchRenderSettings,
    RenderSubmitterUISettings,
)
from deadline.max_shared.utilities.max_utils import BatchRenderView


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


class TestStepData:
    """Tests for StepData.name property."""

    @pytest.fixture
    def sample_state_set(self):
        """Create a sample StateSetData for testing."""
        return StateSetData(
            state_set="MyStateSet",
            renderer="V_Ray_6",
            frame_range="1-100",
            output_directories={"/output"},
            output_file_dir="/output",
            output_file_name="render_####",
            output_file_format=".png",
            image_resolution=(1920, 1080),
            ui_group_label="My State Set",
        )

    def test_name_without_batch_view(self, sample_state_set):
        """Verify name returns state_set name when no batch render view."""
        step_data = StepData(
            state_set=sample_state_set,
            batch_view=None,
            frame_range="1-100",
            width=1920,
            height=1080,
        )

        assert step_data.name == "MyStateSet"

    def test_name_with_batch_view(self, sample_state_set):
        """Verify name includes batch render view name when present."""
        batch_view = BatchRenderView(name="BatchRender001")
        step_data = StepData(
            state_set=sample_state_set,
            batch_view=batch_view,
            frame_range="1-100",
            width=1920,
            height=1080,
        )

        assert step_data.name == "StateSet_MyStateSet_Batch_BatchRender001"


class TestRenderSubmitterUISettings:
    """Tests for RenderSubmitterUISettings sticky settings with nested dataclasses."""

    @pytest.fixture(autouse=True)
    def mock_rt(self):
        """Mock pymxs runtime for all tests."""
        with patch("deadline.max_submitter.data_classes.rt") as mock:
            mock.maxFilePath = "C:/scenes/"
            mock.maxFileName = "test_scene.max"
            yield mock

    def test_load_sticky_settings_with_nested_dataclass(self, mock_rt):
        """Verify load_sticky_settings correctly deserializes nested BatchRenderSettings."""
        sticky_data = {
            "name": "TestJob",
            "batch_render_enabled": True,
            "batch_render": {
                "enabled_views": ["Item1", "Item2", "Item3"],
            },
            "priority": 75,
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(sticky_data))):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_file", return_value=True):
                    settings = RenderSubmitterUISettings()
                    settings.load_sticky_settings()

        assert settings.name == "TestJob"
        assert settings.batch_render_enabled is True
        assert isinstance(settings.batch_render, BatchRenderSettings)
        assert settings.batch_render.enabled_views == ["Item1", "Item2", "Item3"]
        assert settings.priority == 75

    def test_load_sticky_settings_without_nested_dataclass(self, mock_rt):
        """Verify load_sticky_settings works with simple values."""
        sticky_data = {
            "name": "SimpleJob",
            "priority": 50,
            "frame_list": "1-50",
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(sticky_data))):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_file", return_value=True):
                    settings = RenderSubmitterUISettings()
                    settings.load_sticky_settings()

        assert settings.name == "SimpleJob"
        assert settings.priority == 50
        assert settings.frame_list == "1-50"
        # batch_render should remain default
        assert isinstance(settings.batch_render, BatchRenderSettings)
        assert settings.batch_render.enabled_views == []

    def test_load_sticky_settings_file_not_found(self, mock_rt):
        """Verify load_sticky_settings uses defaults when file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            settings = RenderSubmitterUISettings()
            settings.load_sticky_settings()

        # Should use defaults
        assert settings.name == ""
        assert settings.priority == 50
        assert settings.batch_render.enabled_views == []

    def test_load_sticky_settings_invalid_json(self, mock_rt):
        """Verify load_sticky_settings handles invalid JSON gracefully."""
        with patch("builtins.open", mock_open(read_data="not valid json {")):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_file", return_value=True):
                    settings = RenderSubmitterUISettings()
                    # Should not raise, just use defaults
                    settings.load_sticky_settings()

        assert settings.name == ""

    def test_save_sticky_settings_with_nested_dataclass(self, mock_rt):
        """Verify save_sticky_settings correctly serializes nested BatchRenderSettings."""
        settings = RenderSubmitterUISettings()
        settings.name = "TestJob"
        settings.batch_render_enabled = True
        settings.batch_render = BatchRenderSettings(enabled_views=["Item1", "view2"])
        settings.priority = 80

        written_chunks = []

        m = mock_open()
        m.return_value.write.side_effect = lambda data: written_chunks.append(data)

        with patch("builtins.open", m):
            settings.save_sticky_settings()

        written_data = json.loads("".join(written_chunks))

        assert written_data["name"] == "TestJob"
        assert written_data["batch_render_enabled"] is True
        assert written_data["batch_render"] == {"enabled_views": ["Item1", "view2"]}
        assert written_data["priority"] == 80

    def test_save_sticky_settings_only_saves_sticky_fields(self, mock_rt):
        """Verify save_sticky_settings only saves fields with sticky=True metadata."""
        settings = RenderSubmitterUISettings()
        settings.name = "TestJob"  # sticky=True
        settings.project_path = "/some/path"  # sticky=False
        settings.renderer = "V_Ray_6"  # sticky=False

        written_chunks = []

        m = mock_open()
        m.return_value.write.side_effect = lambda data: written_chunks.append(data)

        with patch("builtins.open", m):
            settings.save_sticky_settings()

        written_data = json.loads("".join(written_chunks))

        assert "name" in written_data
        assert "project_path" not in written_data
        assert "renderer" not in written_data
