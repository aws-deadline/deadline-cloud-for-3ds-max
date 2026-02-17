# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for deadline.max_submitter.max_render_submitter

Covers the changes we made:
- output_filename_pattern is used (not old output_name) in on_create_job_bundle_callback
- get_render_output_info() is called instead of manual os.path.split in show_job_bundle_submitter
- last_rend_output_filename is no longer saved in on_create_job_bundle_callback
"""

from pathlib import Path

import pytest

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
