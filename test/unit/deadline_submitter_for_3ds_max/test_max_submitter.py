# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import sys
from unittest.mock import Mock


def test_text_elements_enforce_length_checks() -> None:
    try:
        # Create new mocks. We need to use a real class for QWidget instead of a Mock() so that the
        # SceneSettingsWidget which is a subclass of QWidget actually runs its methods (instead its
        # methods being mocked out).
        class MockQWidget:
            setEnabled = Mock()

            def __init__(self, parent):
                pass

        mock_q_widgets = Mock()
        mock_line_edit = Mock()

        sys.modules["PySide2.QtWidgets"] = mock_q_widgets
        mock_q_widgets.QWidget = MockQWidget
        mock_q_widgets.QLineEdit = mock_line_edit

        # Load SceneSettingsWidget with the new mocks in place.
        from deadline.max_submitter.ui.scene_settings_tab import SceneSettingsWidget

        # Stub out a method
        SceneSettingsWidget._configure_settings = Mock()  # type: ignore
        SceneSettingsWidget._fill_cameras_box = Mock()  # type: ignore

        # Create the scene widget
        SceneSettingsWidget(initial_settings=Mock())

        # Verify that every line edit UI element has a max legnth constraint applied
        assert mock_line_edit.call_count == mock_line_edit.return_value.setMaxLength.call_count
        # Make sure the mock is working and there's at least 1 call (because there's at least 1 line edit element)
        assert mock_line_edit.call_count > 0
    finally:
        # Reset QtWidgets mock
        sys.modules["PySide2.QtWidgets"] = Mock()
