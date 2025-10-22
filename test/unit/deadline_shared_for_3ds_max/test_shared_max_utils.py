# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for shared max utilities to verify the shared module works correctly.
"""

import pytest
from unittest.mock import patch


# Test that imports work correctly from both shared and submitter modules
def test_shared_utilities_import():
    """Test that shared utilities can be imported correctly."""
    try:
        from deadline.max_shared.utilities.max_utils import (
            get_render_elements,
            validate_render_element_paths,
            get_render_elements_output_directories,
            purify_render_element_name,
        )

        assert callable(get_render_elements)
        assert callable(validate_render_element_paths)
        assert callable(get_render_elements_output_directories)
        assert callable(purify_render_element_name)
    except ImportError as e:
        pytest.fail(f"Failed to import shared utilities: {e}")


def test_submitter_utilities_import():
    """Test that submitter utilities can import the shared functions."""
    try:
        from deadline.max_shared.utilities.max_utils import (
            get_render_elements,
            validate_render_element_paths,
            get_render_elements_output_directories,
        )

        assert callable(get_render_elements)
        assert callable(validate_render_element_paths)
        assert callable(get_render_elements_output_directories)
    except ImportError as e:
        pytest.fail(f"Failed to import from submitter utilities: {e}")


def test_purify_render_element_name():
    """Test the render element name purification function."""
    from deadline.max_shared.utilities.max_utils import purify_render_element_name

    # Test normal name
    assert purify_render_element_name("Normal_Name") == "Normal_Name"

    # Test name with invalid characters
    assert purify_render_element_name(r'Name<>:"|\?*/\\') == "Name___________"

    # Test empty name
    assert purify_render_element_name("") == "Element"

    # Test name with only spaces and dots
    assert purify_render_element_name("  . . ") == "Element"

    # Test name with leading/trailing spaces and dots
    assert purify_render_element_name(" .Valid_Name. ") == "Valid_Name"


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_get_render_elements_no_manager(mock_rt):
    """Test get_render_elements when no render element manager is available."""
    from deadline.max_shared.utilities.max_utils import get_render_elements

    # Mock no render element manager
    mock_rt.maxOps.GetCurRenderElementMgr.return_value = None

    result = get_render_elements()
    assert result == []


def test_validate_render_element_configuration():
    """Test render element configuration validation."""
    from deadline.max_shared.utilities.max_utils import (
        validate_render_element_configuration,
        RenderElementConfigurationSettings,
    )

    # Test with empty render elements
    warnings = validate_render_element_configuration([], RenderElementConfigurationSettings())
    assert warnings == []

    # Test with ignore by name settings
    from deadline.max_shared.utilities.max_utils import RenderElementInfo

    render_elements = [
        RenderElementInfo(
            index=0,
            name="Element1",
            type="TestType",
            enabled=True,
            output_filename="",
            has_output_path=False,
            vray_vfb=False,
            element_object=None,
        ),
        RenderElementInfo(
            index=1,
            name="Element2",
            type="TestType",
            enabled=True,
            output_filename="",
            has_output_path=False,
            vray_vfb=False,
            element_object=None,
        ),
    ]
    settings = RenderElementConfigurationSettings(
        ignore_render_elements_by_name=["Element1", "NonExistent"],
        render_elements_update_paths=False,
    )

    warnings = validate_render_element_configuration(render_elements, settings)
    assert len(warnings) == 1
    assert "NonExistent" in warnings[0]
    assert "not found in scene" in warnings[0]
