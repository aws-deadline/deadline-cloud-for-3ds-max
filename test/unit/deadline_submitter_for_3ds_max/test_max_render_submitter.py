# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for deadline.max_submitter.max_render_submitter
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from deadline.max_shared.utilities.max_utils import BatchRenderView
from deadline.max_submitter.max_render_submitter import _collect_batch_render_attachments

# max_render_submitter.py has bare imports (create_job_bundle, data_classes, etc.)
# that only resolve inside 3ds Max's Python environment, so we can't import the module
# in a normal test environment. Read the source file directly instead.

_SOURCE_FILE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "deadline"
    / "max_submitter"
    / "max_render_submitter.py"
)


@pytest.fixture(scope="module")
def source_code() -> str:
    return _SOURCE_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def show_job_bundle_submitter_source(source_code) -> str:
    start = source_code.index("def show_job_bundle_submitter")
    # This is the last function in the file, so grab to end
    return source_code[start:]


@pytest.fixture(scope="module")
def on_create_job_bundle_callback_source(source_code) -> str:
    start = source_code.index("def on_create_job_bundle_callback")
    end = source_code.index("\ndef show_job_bundle_submitter")
    return source_code[start:end]


class TestShowJobBundleSubmitterUsesHelper:
    """Verify show_job_bundle_submitter uses get_render_output_info() instead of os.path.split."""

    def test_calls_get_render_output_info(self, show_job_bundle_submitter_source):
        assert "get_render_output_info()" in show_job_bundle_submitter_source

    def test_no_manual_os_path_split_on_rendOutputFilename(self, show_job_bundle_submitter_source):
        """Should not manually split rt.rendOutputFilename — use the helper instead."""
        assert "os.path.split(rt.rendOutputFilename)" not in show_job_bundle_submitter_source

    def test_sets_output_filename_pattern(self, show_job_bundle_submitter_source):
        """show_job_bundle_submitter should set output_filename_pattern on render_settings."""
        assert "output_filename_pattern" in show_job_bundle_submitter_source


class TestOnCreateJobBundleUsesOutputFilenamePattern:
    """Verify on_create_job_bundle_callback reads output_filename_pattern from settings."""

    def test_uses_output_filename_pattern(self, on_create_job_bundle_callback_source):
        """State set data should be built from settings.output_filename_pattern."""
        assert "settings.output_filename_pattern" in on_create_job_bundle_callback_source

    def test_no_manual_os_path_split(self, on_create_job_bundle_callback_source):
        """Should not manually split rt.rendOutputFilename in the callback."""
        assert "os.path.split(rt.rendOutputFilename)" not in on_create_job_bundle_callback_source

    def test_no_last_rend_output_filename(self, on_create_job_bundle_callback_source):
        """on_create_job_bundle_callback should not reference last_rend_output_filename."""
        assert "last_rend_output_filename" not in on_create_job_bundle_callback_source


class TestCollectBatchRenderAttachments:
    """Tests for _collect_batch_render_attachments function."""

    @pytest.fixture(autouse=True)
    def mock_max_utils(self):
        """Mock max_utils for all tests."""
        with patch("deadline.max_submitter.max_render_submitter.max_utils") as mock:
            mock.get_scene_path.return_value = "C:/scenes/test.max"
            yield mock

    @pytest.fixture(autouse=True)
    def mock_os_path(self):
        """Mock os.path functions for all tests."""
        with patch("deadline.max_submitter.max_render_submitter.os.path.exists") as mock_exists:
            with patch("deadline.max_submitter.max_render_submitter.os.path.isfile") as mock_isfile:
                with patch(
                    "deadline.max_submitter.max_render_submitter.os.path.isabs"
                ) as mock_isabs:
                    mock_exists.return_value = True
                    mock_isfile.return_value = True
                    mock_isabs.return_value = True
                    yield {
                        "exists": mock_exists,
                        "isfile": mock_isfile,
                        "isabs": mock_isabs,
                    }

    def test_returns_empty_list_for_no_items(self):
        """Verify empty list returned when no batch render views provided."""
        result = _collect_batch_render_attachments([])

        assert result == []

    def test_returns_empty_list_for_items_without_presets(self):
        """Verify empty list returned when items have no preset files."""
        from deadline.max_submitter.max_render_submitter import _collect_batch_render_attachments

        batch_views = [
            BatchRenderView(name="view1", preset_file=""),
            BatchRenderView(name="view2", preset_file=None),
        ]

        result = _collect_batch_render_attachments(batch_views)

        assert result == []

    def test_collects_preset_files(self, mock_os_path):
        """Verify preset files are collected from batch views."""
        batch_views = [
            BatchRenderView(name="view1", preset_file="C:/presets/render1.rps"),
            BatchRenderView(name="view2", preset_file="C:/presets/render2.rps"),
        ]

        result = _collect_batch_render_attachments(batch_views)

        assert len(result) == 2
        assert "C:/presets/render1.rps" in result
        assert "C:/presets/render2.rps" in result

    def test_deduplicates_preset_files(self, mock_os_path):
        """Verify duplicate preset files are deduplicated."""
        batch_views = [
            BatchRenderView(name="view1", preset_file="C:/presets/shared.rps"),
            BatchRenderView(name="view2", preset_file="C:/presets/shared.rps"),
            BatchRenderView(name="view3", preset_file="C:/presets/shared.rps"),
        ]

        result = _collect_batch_render_attachments(batch_views)

        assert len(result) == 1
        assert result[0] == "C:/presets/shared.rps"

    def test_skips_nonexistent_files(self, mock_os_path):
        """Verify nonexistent preset files are skipped."""
        mock_os_path["exists"].side_effect = lambda p: p != "C:/presets/missing.rps"

        batch_views = [
            BatchRenderView(name="view1", preset_file="C:/presets/exists.rps"),
            BatchRenderView(name="view2", preset_file="C:/presets/missing.rps"),
        ]

        result = _collect_batch_render_attachments(batch_views)

        assert len(result) == 1
        assert result[0] == "C:/presets/exists.rps"

    def test_skips_directories(self, mock_os_path):
        """Verify directories are skipped (only files are collected)."""
        mock_os_path["isfile"].side_effect = lambda p: p != "C:/presets/folder"

        batch_views = [
            BatchRenderView(name="view1", preset_file="C:/presets/render.rps"),
            BatchRenderView(name="view2", preset_file="C:/presets/folder"),
        ]

        result = _collect_batch_render_attachments(batch_views)

        assert len(result) == 1
        assert result[0] == "C:/presets/render.rps"

    def test_resolves_relative_paths(self, mock_os_path, mock_max_utils):
        """Verify relative preset paths are resolved to absolute paths."""
        mock_os_path["isabs"].side_effect = lambda p: p.startswith("C:/")
        mock_max_utils.get_scene_path.return_value = "C:/scenes/project/test.max"

        batch_views = [
            BatchRenderView(name="view1", preset_file="presets/render.rps"),
        ]

        result = _collect_batch_render_attachments(batch_views)

        # Should resolve relative to scene directory
        assert len(result) == 1
        # The path should be absolute now
        assert os.path.isabs(result[0]) or result[0].startswith("C:\\") or result[0].startswith("/")

    def test_returns_sorted_list(self, mock_os_path):
        """Verify returned list is sorted for consistent ordering."""
        batch_views = [
            BatchRenderView(name="view1", preset_file="C:/presets/z_preset.rps"),
            BatchRenderView(name="view2", preset_file="C:/presets/a_preset.rps"),
            BatchRenderView(name="view3", preset_file="C:/presets/m_preset.rps"),
        ]

        result = _collect_batch_render_attachments(batch_views)

        assert result == sorted(result)
