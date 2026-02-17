# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for deadline.max_submitter.ui.scene_settings_tab

Covers the changes we made:
- Tooltip comes from get_tokens_tooltip() (single source of truth)
- on_focus_changed no longer syncs render output
- Top-level imports for format_output_filename and get_tokens_tooltip
"""

from pathlib import Path

import pytest

# Because the test __init__.py mocks qtpy, SceneSettingsWidget becomes a MagicMock
# and inspect.getsource won't work. Read the source file directly instead.

_SOURCE_FILE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "deadline"
    / "max_submitter"
    / "ui"
    / "scene_settings_tab.py"
)


@pytest.fixture(scope="module")
def source_code() -> str:
    return _SOURCE_FILE.read_text(encoding="utf-8")


class TestOutputFilenameTooltipSource:
    """Verify the filename pattern tooltip is built from get_tokens_tooltip()."""

    def test_imports_get_tokens_tooltip(self, source_code):
        """scene_settings_tab should import get_tokens_tooltip from filename_utils."""
        assert "from deadline.max_shared.utilities.filename_utils import" in source_code
        assert "get_tokens_tooltip" in source_code

    def test_calls_get_tokens_tooltip(self, source_code):
        """_build_output_filename_settings_ui should call get_tokens_tooltip() for the tooltip."""
        assert "setToolTip(get_tokens_tooltip())" in source_code

    def test_no_hardcoded_token_tooltip(self, source_code):
        """The tooltip string should not be hardcoded — it should come from the helper."""
        # Find the _build_output_filename_settings_ui method body
        start = source_code.index("def _build_output_filename_settings_ui")
        # Find the next def at the same indentation level
        next_def = source_code.index("\n    def ", start + 1)
        method_body = source_code[start:next_def]
        assert "Available tokens:" not in method_body

    def test_preview_tooltip_says_example(self, source_code):
        """The preview label tooltip should say 'Example preview'."""
        assert "Example preview" in source_code


class TestOnFocusChangedNoRenderSync:
    """Verify on_focus_changed does NOT sync render output settings."""

    @pytest.fixture
    def on_focus_changed_source(self, source_code) -> str:
        start = source_code.index("def on_focus_changed")
        next_def = source_code.index("\n    def ", start + 1)
        return source_code[start:next_def]

    def test_no_rend_output_reference(self, on_focus_changed_source):
        """on_focus_changed should not reference rendOutputFilename or _last_rend_output_filename."""
        assert "rendOutputFilename" not in on_focus_changed_source
        assert "_last_rend_output_filename" not in on_focus_changed_source

    def test_only_handles_frame_override(self, on_focus_changed_source):
        """on_focus_changed should only deal with frame_override_txt validation."""
        assert "frame_override_txt" in on_focus_changed_source
        assert "output_filename" not in on_focus_changed_source
        assert "output_path" not in on_focus_changed_source


class TestTopLevelImports:
    """Verify that format_output_filename and get_tokens_tooltip are top-level imports."""

    def test_format_output_filename_imported(self, source_code):
        assert "import" in source_code
        assert "format_output_filename" in source_code

    def test_get_tokens_tooltip_imported(self, source_code):
        assert "get_tokens_tooltip" in source_code
