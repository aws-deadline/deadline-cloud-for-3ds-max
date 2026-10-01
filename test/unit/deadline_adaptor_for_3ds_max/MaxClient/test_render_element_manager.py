# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest.mock import Mock, patch

from deadline.max_adaptor.MaxClient.render_element_manager import (
    RenderElementManager,
    RenderElementResult,
)
from deadline.max_shared.utilities.max_utils import RenderElementInfo


def _mock_render_element(name: str, element_type: str, enabled: bool = True, index: int = 0):
    """
    Helper function to create a mock render element with proper structure.

    Args:
        name: Name of the render element
        element_type: Type/class of the render element
        enabled: Whether the element is enabled
        index: Index of the element

    Returns:
        RenderElementInfo with mocked element_object
    """
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
        output_filename=f"C:/output/{name}.png",
        has_output_path=True,
        vray_vfb=False,
        element_object=mock_element_obj,
    )


class TestRenderElementManager:
    """Unit tests for RenderElementManager class."""

    @patch(
        "deadline.max_adaptor.MaxClient.render_element_manager.validate_render_element_configuration"
    )
    @patch("deadline.max_adaptor.MaxClient.render_element_manager.configure_vray_render_elements")
    @patch("deadline.max_adaptor.MaxClient.render_element_manager._is_renderer_vray")
    @patch(
        "deadline.max_adaptor.MaxClient.render_element_manager.store_original_render_element_state"
    )
    @patch("deadline.max_adaptor.MaxClient.render_element_manager.get_render_elements")
    @patch("deadline.max_adaptor.MaxClient.render_element_manager.rt")
    def test_configure_render_elements_vray_success(
        self,
        mock_rt: Mock,
        mock_get_render_elements: Mock,
        mock_store_state: Mock,
        mock_is_vray: Mock,
        mock_configure_vray: Mock,
        mock_validate: Mock,
    ) -> None:
        """Test successful configuration of VRay render elements."""
        # GIVEN - Setup mock render element manager
        mock_re_manager = Mock()
        mock_re_manager.SetElementsActive = Mock()
        mock_rt.maxOps.GetCurRenderElementMgr.return_value = mock_re_manager

        # Create 5 VRay render elements
        vray_elements = [
            _mock_render_element("VRayDiffuseFilter", "VRayDiffuseFilter", True, 0),
            _mock_render_element("VRayReflection", "VRayReflection", True, 1),
            _mock_render_element("VRaySpecular", "VRaySpecular", True, 2),
            _mock_render_element("VRayLighting", "VRayLighting", True, 3),
            _mock_render_element("VRayGlobalIllumination", "VRayGlobalIllumination", True, 4),
        ]
        mock_get_render_elements.return_value = vray_elements

        # Mock renderer detection to return VRay
        mock_is_vray.return_value = (True, "V_Ray_6_Hotfix_3")

        # Mock state storage
        mock_state = Mock()
        mock_store_state.return_value = mock_state

        # Mock VRay configuration (no warnings)
        mock_configure_vray.return_value = []

        # Mock validation (no warnings)
        mock_validate.return_value = []

        # Configuration data for VRay
        config_data = {
            "render_elements": "true",
            "vray_render_elements_vfb_control": "true",
            "vray_split_buffer_support": "true",
            "render_elements_update_paths": "true",
            "ignore_render_elements_by_name": "",
        }

        # Create manager instance
        manager = RenderElementManager(
            output_file_path="C:/output",
            output_file_name="test_render",
            output_file_format=".png",
        )

        # WHEN - Configure render elements
        result = manager.configure_render_elements(config_data)

        # THEN - Verify success
        assert result.success is True
        assert result.message == "Render elements configured successfully"
        assert result.element_count == 5
        assert result.error is None

        # Verify render element manager was retrieved
        mock_rt.maxOps.GetCurRenderElementMgr.assert_called_once()

        # Verify render elements were retrieved
        mock_get_render_elements.assert_called_once()

        # Verify elements were set active
        mock_re_manager.SetElementsActive.assert_called_once_with(True)

        # Verify original state was stored
        mock_store_state.assert_called_once_with(vray_elements)

        # Verify VRay renderer was detected
        mock_is_vray.assert_called_once()

        # Verify VRay configuration was called
        mock_configure_vray.assert_called_once()
        call_args = mock_configure_vray.call_args
        assert call_args[0][0] == vray_elements  # render_elements
        assert call_args[1]["output_path"] == "C:/output"
        assert call_args[1]["output_name"] == "test_render"
        assert call_args[1]["output_file_format"] == ".png"

        # Verify validation was called
        mock_validate.assert_called_once()

        # Verify manager state
        assert manager.is_configured is True
        assert manager.is_vray is True
        assert manager.current_renderer == "V_Ray_6_Hotfix_3"

    @patch(
        "deadline.max_adaptor.MaxClient.render_element_manager.validate_render_element_configuration"
    )
    @patch(
        "deadline.max_adaptor.MaxClient.render_element_manager._configure_render_element_outputs_filename"
    )
    @patch("deadline.max_adaptor.MaxClient.render_element_manager._is_renderer_vray")
    @patch(
        "deadline.max_adaptor.MaxClient.render_element_manager.store_original_render_element_state"
    )
    @patch("deadline.max_adaptor.MaxClient.render_element_manager.get_render_elements")
    @patch("deadline.max_adaptor.MaxClient.render_element_manager.rt")
    def test_configure_render_elements_art_renderer_success(
        self,
        mock_rt: Mock,
        mock_get_render_elements: Mock,
        mock_store_state: Mock,
        mock_is_vray: Mock,
        mock_configure_outputs: Mock,
        mock_validate: Mock,
    ) -> None:
        """Test successful configuration of ART renderer render elements."""
        # GIVEN - Setup mock render element manager
        mock_re_manager = Mock()
        mock_re_manager.SetElementsActive = Mock()
        mock_rt.maxOps.GetCurRenderElementMgr.return_value = mock_re_manager

        # Create 5 ART render elements
        art_elements = [
            _mock_render_element("Diffuse", "Diffuse", True, 0),
            _mock_render_element("Specular", "Specular", True, 1),
            _mock_render_element("Reflection", "Reflection", True, 2),
            _mock_render_element("Z Depth", "Z_Depth", True, 3),
            _mock_render_element("Alpha", "Alpha", True, 4),
        ]
        mock_get_render_elements.return_value = art_elements

        # Mock renderer detection to return ART (not VRay)
        mock_is_vray.return_value = (False, "ART_Renderer")

        # Mock state storage
        mock_state = Mock()
        mock_store_state.return_value = mock_state

        # Mock standard output configuration (no warnings)
        mock_configure_outputs.return_value = []

        # Mock validation (no warnings)
        mock_validate.return_value = []

        # Configuration data for ART renderer
        config_data = {
            "render_elements": "true",
            "render_elements_update_paths": "true",
            "render_elements_include_name_in_filename": "true",
            "ignore_render_elements_by_name": "",
        }

        # Create manager instance
        manager = RenderElementManager(
            output_file_path="C:/output",
            output_file_name="test_render",
            output_file_format=".jpg",
        )

        # WHEN - Configure render elements
        result = manager.configure_render_elements(config_data)

        # THEN - Verify success
        assert result.success is True
        assert result.message == "Render elements configured successfully"
        assert result.element_count == 5
        assert result.error is None

        # Verify render element manager was retrieved
        mock_rt.maxOps.GetCurRenderElementMgr.assert_called_once()

        # Verify render elements were retrieved
        mock_get_render_elements.assert_called_once()

        # Verify elements were set active
        mock_re_manager.SetElementsActive.assert_called_once_with(True)

        # Verify original state was stored
        mock_store_state.assert_called_once_with(art_elements)

        # Verify renderer was detected as non-VRay
        mock_is_vray.assert_called_once()

        # Verify standard output configuration was called (not VRay-specific)
        mock_configure_outputs.assert_called_once()
        call_args = mock_configure_outputs.call_args
        assert call_args[0][0] == art_elements  # render_elements
        assert call_args[0][1] == "C:/output"  # output_file_path
        assert call_args[0][2] == "test_render"  # output_file_name
        assert call_args[0][3] == ".jpg"  # output_file_format

        # Verify validation was called
        mock_validate.assert_called_once()

        # Verify manager state
        assert manager.is_configured is True
        assert manager.is_vray is False
        assert manager.current_renderer == "ART_Renderer"


class TestRenderElementResult:
    """Unit tests for RenderElementResult dataclass."""

    def test_render_element_result_success_with_message(self) -> None:
        """Test RenderElementResult creation with success and message."""
        # WHEN
        result = RenderElementResult(
            success=True,
            message="Configuration successful",
            element_count=5,
        )

        # THEN
        assert result.success is True
        assert result.message == "Configuration successful"
        assert result.element_count == 5
        assert result.error is None
        assert result.warnings is None

    def test_render_element_result_failure_with_error(self) -> None:
        """Test RenderElementResult creation with failure and error."""
        # WHEN
        result = RenderElementResult(
            success=False,
            error="Failed to configure render elements",
        )

        # THEN
        assert result.success is False
        assert result.error == "Failed to configure render elements"
        assert result.message is None
        assert result.element_count is None
        assert result.warnings is None

    def test_render_element_result_success_default_message(self) -> None:
        """Test RenderElementResult auto-generates success message."""
        # WHEN
        result = RenderElementResult(success=True)

        # THEN
        assert result.success is True
        assert result.message == "Operation completed successfully"
        assert result.error is None

    def test_render_element_result_failure_default_error(self) -> None:
        """Test RenderElementResult auto-generates error message."""
        # WHEN
        result = RenderElementResult(success=False)

        # THEN
        assert result.success is False
        assert result.error == "Unknown error occurred"
        assert result.message is None
