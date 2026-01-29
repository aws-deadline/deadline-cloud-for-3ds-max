# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for shared max utilities to verify the shared module works correctly.
"""

import os

import pytest
from unittest.mock import MagicMock, Mock, patch

from deadline.max_shared.utilities.max_utils import (
    _configure_render_element_outputs_filename,
    _is_renderer_vray,
)


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


@pytest.mark.parametrize(
    "renderer_name,expected_is_vray",
    [
        ("V_Ray_6_Hotfix_3", True),
        ("V_Ray_Next", True),
        ("V_Ray_Adv_5_00_00", True),
        ("ART_Renderer", False),
        ("Default_Scanline_Renderer", False),
        ("Arnold", False),
    ],
)
def test_is_renderer_vray(renderer_name: str, expected_is_vray: bool) -> None:
    """Test _is_renderer_vray correctly identifies V-Ray and non-V-Ray renderers."""
    with patch("deadline.max_shared.utilities.max_utils.rt") as mock_rt:
        mock_rt.renderers.current = renderer_name

        is_vray, returned_name = _is_renderer_vray()

        assert is_vray is expected_is_vray
        assert returned_name == renderer_name


def test_is_renderer_vray_with_exception() -> None:
    """Test _is_renderer_vray handles exceptions gracefully."""
    with patch("deadline.max_shared.utilities.max_utils.rt") as mock_rt:
        # Mock exception when accessing renderer
        type(mock_rt.renderers).current = property(
            lambda self: (_ for _ in ()).throw(Exception("Test error"))
        )

        is_vray, renderer_name = _is_renderer_vray()

        assert is_vray is False
        assert renderer_name == "Unknown"


def _create_mock_vray_render_element(
    name: str, element_type: str, enabled: bool = True, index: int = 0
):
    """Helper to create mock VRay render element with proper structure."""
    from deadline.max_shared.utilities.max_utils import RenderElementInfo

    # Create mock pymxs object
    mock_element_obj = Mock()
    mock_element_obj.enabled = enabled
    mock_element_obj.elementName = name
    mock_element_obj.vrayVFB = False  # VRay specific property

    # Create RenderElementInfo
    return RenderElementInfo(
        index=index,
        name=name,
        type=element_type,
        enabled=enabled,
        output_filename=f"C:/output/{name}.png",
        has_output_path=True,
        vray_vfb=False,
        element_object=mock_element_obj,
    )


@pytest.mark.parametrize(
    "vfb_control,split_buffer",
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ],
)
@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_vray_render_elements(
    mock_rt: MagicMock, vfb_control: bool, split_buffer: bool
) -> None:
    """Test configure_vray_render_elements with different VFB and split buffer settings."""
    from deadline.max_shared.utilities.max_utils import (
        configure_vray_render_elements,
        VRayRenderElementSettings,
    )

    # GIVEN - Mock VRay renderer with actual renderer string
    # Set up renderer mock that returns string for str() but has properties
    mock_renderer = MagicMock()
    mock_renderer.__str__.return_value = "V_Ray_6_Hotfix_3"  # type: ignore[attr-defined]
    mock_renderer.output_on = True
    mock_renderer.output_splitgbuffer = False
    mock_renderer.output_splitfilename = ""
    mock_renderer.output_splitRGB = False
    mock_renderer.output_splitAlpha = False
    mock_rt.renderers.current = mock_renderer

    # Mock render element manager
    mock_re_manager = Mock()
    mock_rt.maxOps.GetCurRenderElementMgr.return_value = mock_re_manager
    mock_rt.classof.side_effect = lambda obj: obj.elementName  # Return element name as type

    # Create 5 VRay render elements
    vray_elements = [
        _create_mock_vray_render_element("VRayDiffuseFilter", "VRayDiffuseFilter", True, 0),
        _create_mock_vray_render_element("VRayReflection", "VRayReflection", True, 1),
        _create_mock_vray_render_element("VRaySpecular", "VRaySpecular", True, 2),
        _create_mock_vray_render_element("VRayLighting", "VRayLighting", True, 3),
        _create_mock_vray_render_element(
            "VRayGlobalIllumination", "VRayGlobalIllumination", True, 4
        ),
    ]

    # VRay settings
    settings = VRayRenderElementSettings(
        vray_render_elements_vfb_control=vfb_control,
        vray_split_buffer_support=split_buffer,
    )

    output_path = "C:/output"
    output_name = "test_render"
    output_format = ".png"

    # WHEN - Configure VRay render elements
    warnings = configure_vray_render_elements(
        vray_elements,
        settings,
        output_path=output_path,
        output_name=output_name,
        output_file_format=output_format,
        ignore_list=[],
    )

    # THEN - Verify configuration
    assert isinstance(warnings, list)

    # Verify VFB control was set correctly
    if vfb_control:
        assert mock_renderer.output_on is False
        # Verify all elements are enabled (no ignore list)
        for element in vray_elements:
            assert element.element_object.enabled is True
            assert element.enabled is True
            # Verify vrayVFB property was set
            assert element.element_object.vrayVFB is False  # Disabled when VFB control is on
    else:
        # VFB control not enabled, output_on should not be changed
        pass

    # Verify split buffer was configured correctly
    if split_buffer:
        assert mock_renderer.output_splitgbuffer is True
        assert mock_renderer.output_splitRGB is True
        assert mock_renderer.output_splitAlpha is True
        expected_base_path = os.path.join(output_path, f"{output_name}{output_format}")
        assert mock_renderer.output_splitfilename == expected_base_path

        # Verify filenames were set for all enabled elements with unique names
        assert mock_re_manager.SetRenderElementFilename.call_count == 5
        for i, element in enumerate(vray_elements):
            expected_element_path = os.path.join(
                output_path, f"{output_name}_{element.name}{output_format}"
            )
            mock_re_manager.SetRenderElementFilename.assert_any_call(i, expected_element_path)


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_vray_render_elements_with_ignore_list(mock_rt: MagicMock) -> None:
    """Test configure_vray_render_elements correctly disables ignored elements."""
    from deadline.max_shared.utilities.max_utils import (
        configure_vray_render_elements,
        VRayRenderElementSettings,
    )

    # GIVEN - Mock VRay renderer with actual renderer string
    # Set up renderer mock that returns string for str() but has properties
    mock_renderer = MagicMock()
    mock_renderer.__str__.return_value = "V_Ray_6_Hotfix_3"  # type: ignore[attr-defined]
    mock_renderer.output_on = True
    mock_rt.renderers.current = mock_renderer

    # Mock render element manager
    mock_re_manager = Mock()
    mock_rt.maxOps.GetCurRenderElementMgr.return_value = mock_re_manager
    mock_rt.classof.side_effect = lambda obj: obj.elementName

    # Create 5 VRay render elements
    vray_elements = [
        _create_mock_vray_render_element("VRayDiffuseFilter", "VRayDiffuseFilter", True, 0),
        _create_mock_vray_render_element("VRayReflection", "VRayReflection", True, 1),
        _create_mock_vray_render_element("VRaySpecular", "VRaySpecular", True, 2),
        _create_mock_vray_render_element("VRayLighting", "VRayLighting", True, 3),
        _create_mock_vray_render_element(
            "VRayGlobalIllumination", "VRayGlobalIllumination", True, 4
        ),
    ]

    # VRay settings with VFB control enabled
    settings = VRayRenderElementSettings(
        vray_render_elements_vfb_control=True,
        vray_split_buffer_support=False,
    )

    # Ignore list - disable VRayReflection and VRayLighting
    ignore_list = ["VRayReflection", "VRayLighting"]

    # WHEN - Configure VRay render elements with ignore list
    warnings = configure_vray_render_elements(
        vray_elements,
        settings,
        output_path="C:/output",
        output_name="test_render",
        output_file_format=".png",
        ignore_list=ignore_list,
    )

    # THEN - Verify ignored elements are disabled
    assert isinstance(warnings, list)

    # Check each element
    for element in vray_elements:
        if element.name in ignore_list:
            # Ignored elements should be disabled
            assert element.element_object.enabled is False
            assert element.enabled is False
        else:
            # Non-ignored elements should be enabled
            assert element.element_object.enabled is True
            assert element.enabled is True

    # Verify VFB control was applied
    assert mock_renderer.output_on is False


def _create_mock_standard_render_element(
    name: str, element_type: str, enabled: bool = True, index: int = 0
):
    """Helper to create mock standard (non-VRay) render element."""
    from deadline.max_shared.utilities.max_utils import RenderElementInfo

    # Create mock pymxs object
    mock_element_obj = Mock()
    mock_element_obj.enabled = enabled
    mock_element_obj.elementName = name

    # Create RenderElementInfo
    return RenderElementInfo(
        index=index,
        name=name,
        type=element_type,
        enabled=enabled,
        output_filename=f"C:/output/{name}.jpg",
        has_output_path=True,
        vray_vfb=False,
        element_object=mock_element_obj,
    )


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_render_element_outputs_filename(mock_rt: MagicMock) -> None:
    """Test _configure_render_element_outputs_filename sets unique filenames for each element."""
    # GIVEN - Mock render element manager
    mock_re_manager = Mock()
    mock_rt.maxOps.GetCurRenderElementMgr.return_value = mock_re_manager

    # Create 5 standard render elements (from ART renderer test)
    standard_elements = [
        _create_mock_standard_render_element("Diffuse", "Diffuse", True, 0),
        _create_mock_standard_render_element("Specular", "Specular", True, 1),
        _create_mock_standard_render_element("Reflection", "Reflection", True, 2),
        _create_mock_standard_render_element("Z Depth", "Z_Depth", True, 3),
        _create_mock_standard_render_element("Alpha", "Alpha", True, 4),
    ]

    output_path = "C:/output"
    output_name = "test_render"
    output_format = ".jpg"

    # WHEN - Configure standard render element filenames
    warnings = _configure_render_element_outputs_filename(
        standard_elements,
        output_path=output_path,
        output_name=output_name,
        output_file_format=output_format,
        ignore_list=[],
    )

    # THEN - Verify configuration
    assert isinstance(warnings, list)
    assert len(warnings) == 0  # No warnings expected

    # Verify unique filenames were set for all enabled elements
    assert mock_re_manager.SetRenderElementFilename.call_count == 5

    # Verify each element got a unique filename
    expected_filenames = [
        os.path.join(output_path, f"{output_name}_Diffuse{output_format}"),
        os.path.join(output_path, f"{output_name}_Specular{output_format}"),
        os.path.join(output_path, f"{output_name}_Reflection{output_format}"),
        os.path.join(output_path, f"{output_name}_Z Depth{output_format}"),  # Space preserved
        os.path.join(output_path, f"{output_name}_Alpha{output_format}"),
    ]

    for i, expected_filename in enumerate(expected_filenames):
        mock_re_manager.SetRenderElementFilename.assert_any_call(i, expected_filename)


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_render_element_outputs_filename_with_ignore_list(mock_rt: MagicMock) -> None:
    """Test _configure_render_element_outputs_filename skips ignored elements."""
    from deadline.max_shared.utilities.max_utils import (
        _configure_render_element_outputs_filename,
    )

    # GIVEN - Mock render element manager
    mock_re_manager = Mock()
    mock_rt.maxOps.GetCurRenderElementMgr.return_value = mock_re_manager

    # Create 5 standard render elements
    standard_elements = [
        _create_mock_standard_render_element("Diffuse", "Diffuse", True, 0),
        _create_mock_standard_render_element("Specular", "Specular", True, 1),
        _create_mock_standard_render_element("Reflection", "Reflection", True, 2),
        _create_mock_standard_render_element("Z Depth", "Z_Depth", True, 3),
        _create_mock_standard_render_element("Alpha", "Alpha", True, 4),
    ]

    output_path = "C:/output"
    output_name = "test_render"
    output_format = ".jpg"

    # Ignore Specular and Z Depth
    ignore_list = ["Specular", "Z Depth"]

    # WHEN - Configure standard render element filenames with ignore list
    warnings = _configure_render_element_outputs_filename(
        standard_elements,
        output_path=output_path,
        output_name=output_name,
        output_file_format=output_format,
        ignore_list=ignore_list,
    )

    # THEN - Verify configuration
    assert isinstance(warnings, list)
    assert len(warnings) == 0  # No warnings expected

    # Verify only non-ignored elements got filenames set (3 out of 5)
    assert mock_re_manager.SetRenderElementFilename.call_count == 3

    # Verify only non-ignored elements got unique filenames
    expected_calls = [
        (0, os.path.join(output_path, f"{output_name}_Diffuse{output_format}")),
        (2, os.path.join(output_path, f"{output_name}_Reflection{output_format}")),
        (4, os.path.join(output_path, f"{output_name}_Alpha{output_format}")),
    ]

    for index, expected_filename in expected_calls:
        mock_re_manager.SetRenderElementFilename.assert_any_call(index, expected_filename)

    # Verify ignored elements were NOT set
    not_expected_calls = [
        (1, os.path.join(output_path, f"{output_name}_Specular{output_format}")),
        (3, os.path.join(output_path, f"{output_name}_Z Depth{output_format}")),  # Space preserved
    ]

    for index, filename in not_expected_calls:
        # These calls should not have been made
        try:
            mock_re_manager.SetRenderElementFilename.assert_any_call(index, filename)
            assert False, f"Expected call for ignored element at index {index} should not exist"
        except AssertionError:
            pass  # Expected - the call should not exist


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_render_element_outputs_filename_with_special_characters(mock_rt):
    """Test _configure_render_element_outputs_filename handles special characters in element names."""
    from deadline.max_shared.utilities.max_utils import (
        _configure_render_element_outputs_filename,
    )

    # GIVEN - Mock render element manager
    mock_re_manager = Mock()
    mock_rt.maxOps.GetCurRenderElementMgr.return_value = mock_re_manager

    # Create render elements with special characters (from ART test)
    standard_elements = [
        _create_mock_standard_render_element("Hair and Fur", "Hair_and_Fur", True, 0),
        _create_mock_standard_render_element("Material ID", "Material_ID", True, 1),
        _create_mock_standard_render_element("Self-Illumination", "Self_Illumination", True, 2),
    ]

    output_path = "C:/output"
    output_name = "test_render"
    output_format = ".jpg"

    # WHEN - Configure standard render element filenames
    warnings = _configure_render_element_outputs_filename(
        standard_elements,
        output_path=output_path,
        output_name=output_name,
        output_file_format=output_format,
        ignore_list=[],
    )

    # THEN - Verify configuration
    assert isinstance(warnings, list)
    assert len(warnings) == 0

    # Verify filenames were set with purified names (spaces and special chars handled)
    assert mock_re_manager.SetRenderElementFilename.call_count == 3

    # The purify_render_element_name function preserves spaces, only removes invalid chars
    expected_filenames = [
        os.path.join(output_path, f"{output_name}_Hair and Fur{output_format}"),
        os.path.join(output_path, f"{output_name}_Material ID{output_format}"),
        os.path.join(output_path, f"{output_name}_Self-Illumination{output_format}"),
    ]

    for i, expected_filename in enumerate(expected_filenames):
        mock_re_manager.SetRenderElementFilename.assert_any_call(i, expected_filename)


# ============================================================================
# V-Ray RT Tests
# ============================================================================


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_set_vray_output_path_standard_vray(mock_rt: MagicMock) -> None:
    """Test set_vray_output_path sets path for standard V-Ray only."""
    from deadline.max_shared.utilities.max_utils import set_vray_output_path

    # GIVEN - Mock standard V-Ray renderer
    mock_renderer = MagicMock()
    mock_renderer.classid = "#(1941615238, 2012806412)"
    mock_renderer.__str__.return_value = "V_Ray_6"  # type: ignore[attr-defined]
    mock_rt.renderers.current = mock_renderer

    output_path: str = "C:/output"
    output_name: str = "test_render"
    output_format: str = ".exr"

    # WHEN - Set V-Ray output path
    set_vray_output_path(output_path, output_name, output_format)

    # THEN - Should set path on standard renderer only
    expected_path: str = f"C:/output{os.sep}test_render.exr"
    assert mock_renderer.output_splitfilename == expected_path


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_set_vray_output_path_vray_rt(mock_rt: MagicMock) -> None:
    """Test set_vray_output_path sets path for both standard V-Ray and V-Ray RT."""
    from deadline.max_shared.utilities.max_utils import set_vray_output_path

    # GIVEN - Mock V-Ray RT renderer
    mock_renderer = MagicMock()
    mock_renderer.classid = "#(1770671000, 1323107829)"
    mock_renderer.__str__.return_value = "V_Ray_GPU_6"  # type: ignore[attr-defined]
    mock_vray_settings = MagicMock()
    mock_renderer.V_Ray_settings = mock_vray_settings
    mock_rt.renderers.current = mock_renderer

    output_path: str = "C:/output"
    output_name: str = "test_render"
    output_format: str = ".png"

    # WHEN - Set V-Ray output path
    set_vray_output_path(output_path, output_name, output_format)

    # THEN - Should set path on both standard renderer and RT settings
    expected_path: str = f"C:/output{os.sep}test_render.png"
    assert mock_renderer.output_splitfilename == expected_path
    assert mock_vray_settings.output_splitfilename == expected_path


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_set_vray_output_path_raises_on_failure(mock_rt: MagicMock) -> None:
    """Test set_vray_output_path raises RuntimeError when setting path fails."""
    import pytest

    from deadline.max_shared.utilities.max_utils import set_vray_output_path

    # GIVEN - Mock renderer that raises exception when setting output_splitfilename
    mock_renderer = MagicMock()
    mock_renderer.classid = "#(1941615238, 2012806412)"
    mock_renderer.__str__.return_value = "V_Ray_6"  # type: ignore[attr-defined]
    type(mock_renderer).output_splitfilename = property(
        fget=lambda self: None,
        fset=MagicMock(side_effect=Exception("V-Ray API error")),
    )
    mock_rt.renderers.current = mock_renderer

    output_path: str = "C:/output"
    output_name: str = "test_render"
    output_format: str = ".exr"

    # WHEN/THEN - Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Failed to set V-Ray output path"):
        set_vray_output_path(output_path, output_name, output_format)


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_vray_render_elements_sets_rt_settings(mock_rt: MagicMock) -> None:
    """Test configure_vray_render_elements sets both standard and RT settings."""
    from deadline.max_shared.utilities.max_utils import (
        configure_vray_render_elements,
        VRayRenderElementSettings,
    )

    # GIVEN - Mock V-Ray RT renderer
    mock_renderer = MagicMock()
    mock_renderer.classid = "#(1770671000, 1323107829)"
    mock_renderer.__str__.return_value = "V_Ray_GPU_6"  # type: ignore[attr-defined]
    mock_renderer.output_on = True
    mock_renderer.output_splitgbuffer = False
    mock_renderer.output_splitRGB = False
    mock_renderer.output_splitAlpha = False

    mock_vray_settings = MagicMock()
    mock_vray_settings.output_on = True
    mock_vray_settings.output_splitgbuffer = False
    mock_vray_settings.output_splitRGB = False
    mock_vray_settings.output_splitAlpha = False
    mock_renderer.V_Ray_settings = mock_vray_settings

    mock_rt.renderers.current = mock_renderer

    # Mock render element manager
    mock_re_manager = Mock()
    mock_rt.maxOps.GetCurRenderElementMgr.return_value = mock_re_manager

    # Create VRay render element
    vray_element = _create_mock_vray_render_element(
        "VRayDiffuseFilter", "VRayDiffuseFilter", True, 0
    )

    settings = VRayRenderElementSettings(
        vray_render_elements_vfb_control=True,
        vray_split_buffer_support=True,
    )

    # WHEN - Configure VRay render elements
    warnings: list[str] = configure_vray_render_elements(
        [vray_element],
        settings,
        output_path="C:/output",
        output_name="test",
        output_file_format=".png",
    )

    # THEN - Both standard and RT settings should be configured
    assert mock_renderer.output_on is False
    assert mock_vray_settings.output_on is False

    assert mock_renderer.output_splitgbuffer is True
    assert mock_vray_settings.output_splitgbuffer is True

    assert mock_renderer.output_splitRGB is True
    assert mock_vray_settings.output_splitRGB is True

    assert mock_renderer.output_splitAlpha is True
    assert mock_vray_settings.output_splitAlpha is True

    assert isinstance(warnings, list)


# ============================================================================
# Tests for V-Ray Raw Output (.vrimg / .exr) Support
# ============================================================================


@pytest.mark.parametrize(
    "output_format,expected",
    [
        (".vrimg", True),
        (".VRIMG", True),
        (".VrImg", True),
        (".exr", True),
        (".EXR", True),
        (".Exr", True),
        (".png", False),
        (".jpg", False),
        (".tga", False),
        (".tiff", False),
        (".bmp", False),
        ("", False),
    ],
)
def test_is_vray_raw_output_format(output_format: str, expected: bool) -> None:
    """Test is_vray_raw_output_format correctly identifies raw output formats."""
    from deadline.max_shared.utilities.max_utils import is_vray_raw_output_format

    result = is_vray_raw_output_format(output_format)
    assert result == expected, f"Expected {expected} for format '{output_format}', got {result}"


def test_is_vray_raw_output_format_none() -> None:
    """Test is_vray_raw_output_format handles None input."""
    from deadline.max_shared.utilities.max_utils import is_vray_raw_output_format

    # Should return False for None (empty string check)
    result = is_vray_raw_output_format("")
    assert result is False


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_vray_raw_output_vrimg(mock_rt: MagicMock) -> None:
    """Test configure_vray_raw_output configures V-Ray for .vrimg output."""
    from deadline.max_shared.utilities.max_utils import configure_vray_raw_output

    # GIVEN - Mock V-Ray renderer
    mock_renderer = MagicMock()
    mock_renderer.configure_mock(__str__=MagicMock(return_value="V_Ray_7_Hotfix_2"))
    mock_renderer.classid = "#(1234, 5678)"
    mock_rt.renderers.current = mock_renderer

    output_path = "C:/output"
    output_name = "test_render"
    output_format = ".vrimg"

    # WHEN - Configure V-Ray raw output
    warnings = configure_vray_raw_output(output_path, output_name, output_format)

    # THEN - Verify all V-Ray raw output properties were set
    assert mock_renderer.output_userigbe is True, "VFB should be enabled"
    assert mock_renderer.output_on is True, "Raw output should be enabled"
    assert mock_renderer.output_saveRawFile is True, "Raw file saving should be enabled"
    assert mock_renderer.output_rawFileName == "C:/output\\test_render.vrimg"
    assert isinstance(warnings, list)
    assert len(warnings) == 0, f"Expected no warnings, got: {warnings}"


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_vray_raw_output_exr(mock_rt: MagicMock) -> None:
    """Test configure_vray_raw_output configures V-Ray for .exr output."""
    from deadline.max_shared.utilities.max_utils import configure_vray_raw_output

    # GIVEN - Mock V-Ray renderer
    mock_renderer = MagicMock()
    mock_renderer.configure_mock(__str__=MagicMock(return_value="V_Ray_7_Hotfix_2"))
    mock_renderer.classid = "#(1234, 5678)"
    mock_rt.renderers.current = mock_renderer

    output_path = "C:/renders/project"
    output_name = "frame_001"
    output_format = ".exr"

    # WHEN - Configure V-Ray raw output
    warnings = configure_vray_raw_output(output_path, output_name, output_format)

    # THEN - Verify all V-Ray raw output properties were set
    assert mock_renderer.output_userigbe is True, "VFB should be enabled"
    assert mock_renderer.output_on is True, "Raw output should be enabled"
    assert mock_renderer.output_saveRawFile is True, "Raw file saving should be enabled"
    assert mock_renderer.output_rawFileName == "C:/renders/project\\frame_001.exr"
    assert isinstance(warnings, list)
    assert len(warnings) == 0, f"Expected no warnings, got: {warnings}"


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_vray_raw_output_format_without_dot(mock_rt: MagicMock) -> None:
    """Test configure_vray_raw_output handles format without leading dot."""
    from deadline.max_shared.utilities.max_utils import configure_vray_raw_output

    # GIVEN - Mock V-Ray renderer
    mock_renderer = MagicMock()
    mock_renderer.configure_mock(__str__=MagicMock(return_value="V_Ray_7_Hotfix_2"))
    mock_renderer.classid = "#(1234, 5678)"
    mock_rt.renderers.current = mock_renderer

    output_path = "C:/output"
    output_name = "test"
    output_format = "vrimg"  # No leading dot

    # WHEN - Configure V-Ray raw output
    warnings = configure_vray_raw_output(output_path, output_name, output_format)

    # THEN - Should add the dot automatically
    assert mock_renderer.output_rawFileName == "C:/output\\test.vrimg"
    assert len(warnings) == 0


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_vray_raw_output_vray_gpu(mock_rt: MagicMock) -> None:
    """Test configure_vray_raw_output works with V-Ray GPU (RT)."""
    from deadline.max_shared.utilities.max_utils import configure_vray_raw_output

    # GIVEN - Mock V-Ray GPU renderer with nested V_Ray_settings
    mock_renderer = MagicMock()
    mock_renderer.configure_mock(__str__=MagicMock(return_value="V_Ray_GPU_7_Hotfix_2"))
    mock_renderer.classid = "#(1770671000, 1323107829)"  # V-Ray RT class ID

    mock_vray_settings = MagicMock()
    mock_renderer.V_Ray_settings = mock_vray_settings
    mock_rt.renderers.current = mock_renderer

    output_path = "C:/output"
    output_name = "gpu_render"
    output_format = ".exr"

    # WHEN - Configure V-Ray raw output
    warnings = configure_vray_raw_output(output_path, output_name, output_format)

    # THEN - Verify properties were set on both renderer and V_Ray_settings
    # V-Ray GPU sets on vray_rt_settings first, then on renderer
    assert mock_vray_settings.output_userigbe is True
    assert mock_vray_settings.output_on is True
    assert mock_vray_settings.output_saveRawFile is True
    assert mock_vray_settings.output_rawFileName == "C:/output\\gpu_render.exr"

    # Also set on renderer.current
    assert mock_renderer.output_userigbe is True
    assert mock_renderer.output_on is True
    assert mock_renderer.output_saveRawFile is True
    assert mock_renderer.output_rawFileName == "C:/output\\gpu_render.exr"

    assert len(warnings) == 0


@patch("deadline.max_shared.utilities.max_utils.rt")
def test_configure_vray_raw_output_handles_exception(mock_rt: MagicMock) -> None:
    """Test configure_vray_raw_output handles exceptions gracefully."""
    from deadline.max_shared.utilities.max_utils import configure_vray_raw_output

    # GIVEN - Mock renderer that raises exception on property set
    mock_renderer = MagicMock()
    mock_renderer.configure_mock(__str__=MagicMock(return_value="V_Ray_7_Hotfix_2"))
    mock_renderer.classid = "#(1234, 5678)"

    # Make setting output_userigbe raise an exception
    type(mock_renderer).output_userigbe = property(
        fget=lambda self: False,
        fset=Mock(side_effect=Exception("Property set failed")),
    )
    mock_rt.renderers.current = mock_renderer

    output_path = "C:/output"
    output_name = "test"
    output_format = ".vrimg"

    # WHEN - Configure V-Ray raw output
    warnings = configure_vray_raw_output(output_path, output_name, output_format)

    # THEN - Should return warnings instead of raising
    assert len(warnings) > 0
    assert any("Failed to set V-Ray property" in w for w in warnings)
