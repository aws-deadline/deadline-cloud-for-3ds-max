# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations
from unittest.mock import patch, Mock

import pytest
from deadline.max_adaptor.MaxClient.render_handlers import DefaultMaxHandler
from deadline.max_adaptor.MaxClient.render_element_manager import RenderElementResult
from deadline.max_adaptor.executable_handler import MaxExecutableHandler


@pytest.fixture
def maxhandlerbase():
    return DefaultMaxHandler()


class TestDefaultMaxHandler:
    @pytest.mark.parametrize("args", [{"output_file_path": "C:/Users/Sandie/Desktop"}])
    def test_set_output_file_path(self, maxhandlerbase: DefaultMaxHandler, args: dict):
        """Tests that setting the image height calls the correct functions"""
        # WHEN
        maxhandlerbase.set_output_file_path(args)

        # THEN
        assert maxhandlerbase.output_dir == args["output_file_path"]

    @pytest.mark.parametrize("args", [{"output_file_name": "Output__#####"}])
    def test_set_output_file_name(self, maxhandlerbase: DefaultMaxHandler, args: dict):
        """Tests that setting the image height calls the correct functions"""
        # WHEN
        maxhandlerbase.set_output_file_name(args)

        # THEN
        assert maxhandlerbase.output_name == args["output_file_name"]

    @pytest.mark.parametrize("args", [{"output_file_format": ".png"}])
    def test_set_output_file_format(self, maxhandlerbase: DefaultMaxHandler, args: dict):
        """Tests that setting the image height calls the correct functions"""
        # WHEN
        maxhandlerbase.set_output_file_format(args)

        # THEN
        assert maxhandlerbase.output_format == args["output_file_format"]

    @patch("deadline.max_adaptor.MaxClient.render_handlers.default_max_handler.rt")
    @patch.object(MaxExecutableHandler, "is_executable_type")
    def test_log_to_console(
        self,
        mock_executable_handler: Mock,
        mock_rt: Mock,
        maxhandlerbase: DefaultMaxHandler,
        capsys: pytest.CaptureFixture,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_executable_handler.return_value = False
        test_message_3dsmax: str = "3dsmax test message"

        maxhandlerbase.log_to_console(test_message_3dsmax)

        captured_result = capsys.readouterr()
        assert captured_result.out == f"{test_message_3dsmax}\n"
        assert mock_rt.logsystem.logEntry.called

        mock_executable_handler.return_value = True
        test_message_3dsmaxbatch: str = "3dsmaxbatch test message"

        maxhandlerbase.log_to_console(test_message_3dsmaxbatch)

        captured_result = capsys.readouterr()
        assert test_message_3dsmaxbatch in captured_result.out

    @patch("deadline.max_adaptor.MaxClient.render_element_manager.RenderElementManager")
    def test_configure_render_elements_success(
        self, mock_render_element_manager_class: Mock, maxhandlerbase: DefaultMaxHandler
    ):
        """Tests that configure_render_elements works correctly with render element manager"""
        # GIVEN
        mock_render_element_manager = Mock()
        mock_render_element_manager.configure_render_elements.return_value = RenderElementResult(
            success=True,
            message="Success",
        )
        mock_render_element_manager_class.return_value = mock_render_element_manager

        data = {"RenderElements": "true"}

        # WHEN
        maxhandlerbase.configure_render_elements(data)

        # THEN
        mock_render_element_manager.configure_render_elements.assert_called_once_with(data)
        assert maxhandlerbase.render_element_manager == mock_render_element_manager

    @patch("deadline.max_adaptor.MaxClient.render_element_manager.RenderElementManager")
    def test_configure_render_elements_failure(
        self, mock_render_element_manager_class: Mock, maxhandlerbase: DefaultMaxHandler
    ):
        """Tests that configure_render_elements handles failure correctly"""
        # GIVEN
        mock_render_element_manager = Mock()
        mock_render_element_manager.configure_render_elements.return_value = RenderElementResult(
            success=False,
            error="Test error",
        )
        mock_render_element_manager_class.return_value = mock_render_element_manager

        data = {"RenderElements": "true"}

        # WHEN/THEN
        with pytest.raises(RuntimeError, match="Render elements configuration failed: Test error"):
            maxhandlerbase.configure_render_elements(data)

    def test_cleanup_render_elements_no_manager(self, maxhandlerbase: DefaultMaxHandler):
        """Tests that cleanup_render_elements handles missing render element manager gracefully"""
        # GIVEN
        data = {"RenderElements": "true"}

        # WHEN/THEN - Should not raise exception
        maxhandlerbase.cleanup_render_elements(data)

    @pytest.mark.parametrize(
        "name,number,expected",
        [
            # With hash padding — zero-padded frame number replaces hashes
            ("output_#####", 1, "output_00001"),
            ("output_####", 42, "output_0042"),
            ("output_###", 100, "output_100"),
            # No hashes — return name as-is (single-frame, no numbering needed)
            ("output", 0, "output"),
            ("output", 7, "output"),
        ],
    )
    def test_reformat_framenumber_padding(
        self, maxhandlerbase: DefaultMaxHandler, name: str, number: int, expected: str
    ) -> None:
        assert maxhandlerbase.reformat_framenumber_padding(name, number) == expected

    def test_cleanup_render_elements_not_configured(self, maxhandlerbase: DefaultMaxHandler):
        """Tests that cleanup_render_elements handles unconfigured render elements gracefully"""
        # GIVEN
        mock_render_element_manager = Mock()
        mock_render_element_manager.has_render_elements_configured.return_value = False
        maxhandlerbase.render_element_manager = mock_render_element_manager

        data = {"RenderElements": "true"}

        # WHEN/THEN - Should not raise exception
        maxhandlerbase.cleanup_render_elements(data)

    def test_cleanup_render_elements_success(self, maxhandlerbase: DefaultMaxHandler):
        """Tests that cleanup_render_elements calls render element manager correctly"""
        # GIVEN
        mock_render_element_manager = Mock()
        mock_render_element_manager.has_render_elements_configured.return_value = True
        mock_render_element_manager.restore_render_elements.return_value = RenderElementResult(
            success=True,
            message="Restored",
        )
        maxhandlerbase.render_element_manager = mock_render_element_manager

        data = {"RenderElements": "true"}

        # WHEN
        maxhandlerbase.cleanup_render_elements(data)

        # THEN
        mock_render_element_manager.restore_render_elements.assert_called_once()
