# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Deadline 10 lookalike Render Elements Widget for 3ds Max Deadline Cloud Submitter.

This widget provides render elements controls matching the exact Deadline 10 interface
with a single unified group box and only authentic UI elements.
"""

import logging

from qtpy.QtCore import Qt, Signal  # type: ignore
from qtpy.QtWidgets import (  # type: ignore
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from deadline.max_shared.utilities.max_utils import (
    get_render_elements,
    validate_render_element_paths,
)

_logger = logging.getLogger(__name__)


class RenderElementsWidget(QWidget):
    """
    Deadline 10 lookalike render elements widget with exact UI fidelity.

    This widget matches the original Deadline 10 render elements interface exactly,
    using a single unified group box with only authentic controls.
    """

    # Signals for communicating changes to parent
    settings_changed = Signal()
    validation_changed = Signal(list)  # Emits list of validation warnings

    def __init__(self, initial_settings, parent=None):
        super().__init__(parent=parent)
        self.settings = initial_settings
        self._build_render_elements_ui()
        self._connect_signals()
        self._refresh_ui_state()  # Ensure UI matches the default state
        self._refresh_detected_elements()

    def _remove_emojis(self, text):
        """
        Remove status emoji characters from render element text to prevent Unicode encoding issues.

        Specifically removes the status indicator emojis used in the render elements widget:
        - 🟢 (Green circle) = Enabled with output path
        - 🟡 (Yellow circle) = Enabled without output path
        - 🔴 (Red circle) = Disabled
        - ❌ (Cross mark) = Error indicator

        Args:
            text (str): Text that may contain status emoji characters

        Returns:
            str: Text with status emojis removed and whitespace cleaned up
        """
        # Remove specific status emojis used in this widget
        clean_text = text.replace("🟢", "").replace("🟡", "").replace("🔴", "").replace("❌", "")
        # Clean up extra whitespace
        return " ".join(clean_text.split())

    def _build_render_elements_ui(self):
        """
        Build the authentic Deadline 10 render elements UI with single unified group box.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Single unified group box matching Deadline 10
        render_elements_group = QGroupBox("Render Elements")
        layout = QGridLayout(render_elements_group)
        main_layout.addWidget(render_elements_group)

        # Row 0: Modify Render Elements checkbox (main control)
        self.modify_render_elements_checkbox = QCheckBox("Modify Render Elements")
        self.modify_render_elements_checkbox.setChecked(False)  # Default unchecked
        self.modify_render_elements_checkbox.setToolTip(
            "Enable or disable modification of render elements settings. "
            "When unchecked, all render elements setting changes on the worker will be disabled."
        )
        layout.addWidget(self.modify_render_elements_checkbox, 0, 0, 1, 2)

        # Row 1: Output Render Elements checkbox
        self.render_elements_checkbox = QCheckBox("Output Render Elements")
        self.render_elements_checkbox.setToolTip(
            "Enable or disable render elements output during rendering"
        )
        layout.addWidget(self.render_elements_checkbox, 1, 0, 1, 2)

        # Row 2: Update Render Element Paths checkbox
        self.update_paths_checkbox = QCheckBox("Update Render Element Paths")
        self.update_paths_checkbox.setToolTip(
            "Automatically update render element output paths based on naming settings"
        )
        layout.addWidget(self.update_paths_checkbox, 2, 0, 1, 2)

        # Row 3: Path naming options
        self.include_name_in_path_checkbox = QCheckBox("Include Render Element Name in Path")
        self.include_name_in_path_checkbox.setToolTip(
            "Add render element name as subdirectory in output path"
        )
        layout.addWidget(self.include_name_in_path_checkbox, 3, 0)

        self.include_type_in_path_checkbox = QCheckBox("Include Render Element Type in Path")
        self.include_type_in_path_checkbox.setToolTip(
            "Add render element type as subdirectory in output path"
        )
        layout.addWidget(self.include_type_in_path_checkbox, 3, 1)

        # Row 4: Filename naming options
        self.include_name_in_filename_checkbox = QCheckBox(
            "Include Render Element Name in Filename"
        )
        self.include_name_in_filename_checkbox.setToolTip(
            "Add render element name to output filename"
        )
        layout.addWidget(self.include_name_in_filename_checkbox, 4, 0)

        self.include_type_in_filename_checkbox = QCheckBox(
            "Include Render Element Type in Filename"
        )
        self.include_type_in_filename_checkbox.setToolTip(
            "Add render element type to output filename"
        )
        layout.addWidget(self.include_type_in_filename_checkbox, 4, 1)

        # Row 5: V-Ray specific options
        self.vray_vfb_control_checkbox = QCheckBox("V-Ray Render Elements VFB Control")
        self.vray_vfb_control_checkbox.setToolTip(
            "Automatically control V-Ray VFB settings for render elements during rendering"
        )
        layout.addWidget(self.vray_vfb_control_checkbox, 5, 0)

        self.vray_split_buffer_checkbox = QCheckBox("V-Ray Split Buffer Support")
        self.vray_split_buffer_checkbox.setToolTip(
            "Enable V-Ray split buffer support for render elements"
        )
        layout.addWidget(self.vray_split_buffer_checkbox, 5, 1)

        # Row 6: Ignore by Name section
        ignore_label = QLabel("Ignore Render Elements by Name:")
        layout.addWidget(ignore_label, 6, 0, 1, 2)

        # Row 7: Ignore elements list
        self.ignore_elements_list = QListWidget()
        self.ignore_elements_list.setMaximumHeight(80)
        self.ignore_elements_list.setToolTip(
            "List of render element names to ignore during rendering"
        )
        layout.addWidget(self.ignore_elements_list, 7, 0, 1, 2)

        # Row 8: Ignore list management buttons
        ignore_buttons_layout = QHBoxLayout()
        self.add_ignore_btn = QPushButton("Add Element")
        self.add_ignore_btn.setToolTip("Add selected detected element to ignore list")
        self.remove_ignore_btn = QPushButton("Remove Selected")
        self.remove_ignore_btn.setToolTip("Remove selected element from ignore list")

        ignore_buttons_layout.addWidget(self.add_ignore_btn)
        ignore_buttons_layout.addWidget(self.remove_ignore_btn)
        ignore_buttons_layout.addStretch()

        ignore_buttons_widget = QWidget()
        ignore_buttons_widget.setLayout(ignore_buttons_layout)
        layout.addWidget(ignore_buttons_widget, 8, 0, 1, 2)

        # Row 9: Detected elements list
        detected_label = QLabel("Detected Render Elements:")
        layout.addWidget(detected_label, 9, 0, 1, 2)

        self.detected_elements_list = QListWidget()
        self.detected_elements_list.setMaximumHeight(120)
        self.detected_elements_list.setToolTip(
            "List of render elements detected in the current scene"
        )
        layout.addWidget(self.detected_elements_list, 10, 0, 1, 2)

        # Row 11: Refresh button
        self.refresh_elements_btn = QPushButton("Refresh Detected Elements")
        self.refresh_elements_btn.setToolTip("Refresh the list of detected render elements")
        layout.addWidget(self.refresh_elements_btn, 11, 0, 1, 2)

        # Row 12: Validation feedback
        self.validation_feedback_label = QLabel("")
        self.validation_feedback_label.setStyleSheet("color: red;")
        self.validation_feedback_label.setWordWrap(True)
        self.validation_feedback_label.setMinimumHeight(40)
        layout.addWidget(self.validation_feedback_label, 12, 0, 1, 2)

        # Store all controllable widgets for easy enable/disable
        self._controllable_widgets = [
            self.render_elements_checkbox,
            self.update_paths_checkbox,
            self.include_name_in_path_checkbox,
            self.include_type_in_path_checkbox,
            self.include_name_in_filename_checkbox,
            self.include_type_in_filename_checkbox,
            self.vray_vfb_control_checkbox,
            self.vray_split_buffer_checkbox,
            ignore_label,
            self.ignore_elements_list,
            self.add_ignore_btn,
            self.remove_ignore_btn,
            detected_label,
            self.detected_elements_list,
            self.refresh_elements_btn,
            self.validation_feedback_label,
        ]

    def _connect_signals(self):
        """
        Connect all widget signals to their respective handlers.
        """
        # main control
        self.modify_render_elements_checkbox.stateChanged.connect(
            self._on_modify_render_elements_changed
        )

        # Main controls
        self.render_elements_checkbox.stateChanged.connect(self._on_render_elements_changed)
        self.update_paths_checkbox.stateChanged.connect(self._on_settings_changed)
        self.include_name_in_path_checkbox.stateChanged.connect(self._on_settings_changed)
        self.include_type_in_path_checkbox.stateChanged.connect(self._on_settings_changed)
        self.include_name_in_filename_checkbox.stateChanged.connect(self._on_settings_changed)
        self.include_type_in_filename_checkbox.stateChanged.connect(self._on_settings_changed)
        self.vray_vfb_control_checkbox.stateChanged.connect(self._on_settings_changed)
        self.vray_split_buffer_checkbox.stateChanged.connect(self._on_settings_changed)

        # Ignore list management
        self.add_ignore_btn.clicked.connect(self._add_ignore_element)
        self.remove_ignore_btn.clicked.connect(self._remove_ignore_element)

        # Detection and validation
        self.refresh_elements_btn.clicked.connect(self._refresh_detected_elements)

    def _refresh_ui_state(self):
        """
        Refresh the UI state to match the current checkbox values.
        This ensures all controls are properly enabled/disabled on initialization.
        """
        # Trigger the main control handler to set initial state
        self._on_modify_render_elements_changed(self.modify_render_elements_checkbox.checkState())

    def _on_modify_render_elements_changed(self, state):
        """
        Handle changes to the main modify render elements checkbox.
        When unchecked, disables all other render elements controls.
        When checked, enables all other render elements controls.
        """
        enabled = Qt.CheckState(state) == Qt.Checked

        # Enable/disable all controllable widgets
        for widget in self._controllable_widgets:
            widget.setEnabled(enabled)

        # If we're enabling, also respect the render elements checkbox state
        if enabled:
            self._on_render_elements_changed(self.render_elements_checkbox.checkState())

        self._on_settings_changed()

    def _on_render_elements_changed(self, state):
        """
        Handle changes to the main render elements checkbox.
        Only affects controls if the main modify checkbox is enabled.
        """
        # Only enable/disable controls if the main modify checkbox is checked
        if not self.modify_render_elements_checkbox.isChecked():
            return

        enabled = Qt.CheckState(state) == Qt.Checked

        # Enable/disable only the controls that are dependent on render elements output
        self.update_paths_checkbox.setEnabled(enabled)
        self.include_name_in_path_checkbox.setEnabled(enabled)
        self.include_type_in_path_checkbox.setEnabled(enabled)
        self.include_name_in_filename_checkbox.setEnabled(enabled)
        self.include_type_in_filename_checkbox.setEnabled(enabled)
        self.vray_vfb_control_checkbox.setEnabled(enabled)
        self.vray_split_buffer_checkbox.setEnabled(enabled)

        self._on_settings_changed()

    def _on_settings_changed(self):
        """
        Handle any settings change and trigger validation.
        """
        self._validate_render_elements()
        self.settings_changed.emit()

    def _add_ignore_element(self):
        """
        Add a render element name to the ignore list.
        """
        current_item = self.detected_elements_list.currentItem()
        if not current_item:
            return

        # Get the actual element name from stored item data
        element_name = current_item.data(Qt.UserRole)
        if not element_name:
            # Fallback: extract clean name from display text
            element_name = self._remove_emojis(current_item.text())
            # Further clean up if there's a " - " separator
            if " - " in element_name:
                element_name = element_name.split(" - ")[0].strip()

        # Check if already in ignore list (compare clean names)
        for i in range(self.ignore_elements_list.count()):
            existing_item = self.ignore_elements_list.item(i)
            existing_name = existing_item.data(Qt.UserRole) or self._remove_emojis(
                existing_item.text()
            )
            if existing_name == element_name:
                return  # Already in list

        # Add to ignore list with clean name
        ignore_item = QListWidgetItem(element_name)
        ignore_item.setData(Qt.UserRole, element_name)  # Store clean name as data
        self.ignore_elements_list.addItem(ignore_item)
        self._on_settings_changed()

    def _remove_ignore_element(self):
        """
        Remove selected render element name from the ignore list.
        """
        current_row = self.ignore_elements_list.currentRow()
        if current_row >= 0:
            self.ignore_elements_list.takeItem(current_row)
            self._on_settings_changed()

    def _refresh_detected_elements(self):
        """
        Refresh the list of detected render elements from the scene.
        """
        self.detected_elements_list.clear()

        try:
            # Get render elements using shared utilities
            render_elements = get_render_elements()

            if not render_elements:
                item = QListWidgetItem("No render elements detected in scene")
                item.setToolTip("No render elements found in the current 3ds Max scene")
                self.detected_elements_list.addItem(item)
                return

            # Display render elements with enhanced information
            for element in render_elements:
                name = element.name
                element_type = element.type
                enabled = element.enabled
                has_output = element.has_output_path
                output_filename = element.output_filename

                # Status indicators
                status_parts = []
                status_icon = "🟢"  # Default green for enabled with output

                if not enabled:
                    status_parts.append("DISABLED")
                    status_icon = "🔴"
                elif not has_output:
                    status_parts.append("NO OUTPUT PATH")
                    status_icon = "🟡"

                # V-Ray specific indicator
                if element.vray_vfb:
                    status_parts.append("V-RAY VFB")

                status_text = f" ({', '.join(status_parts)})" if status_parts else ""
                display_text = f"{status_icon} {name} - {element_type}{status_text}"

                item = QListWidgetItem(display_text)
                # Store the actual element name as item data for easy retrieval
                item.setData(Qt.UserRole, name)
                tooltip = (
                    f"Name: {name}\n"
                    f"Type: {element_type}\n"
                    f"Enabled: {enabled}\n"
                    f"Output: {output_filename or 'Not set'}\n"
                    f"Index: {element.index}"
                )
                item.setToolTip(tooltip)
                self.detected_elements_list.addItem(item)

        except Exception as e:
            _logger.error(f"Error refreshing render elements: {e}")
            item = QListWidgetItem(f"❌ Error detecting render elements: {e}")
            self.detected_elements_list.addItem(item)

        self._validate_render_elements()

    def _validate_render_elements(self):
        """
        Validate render elements settings and show feedback.
        """
        feedback_messages = []

        try:
            # Get current render elements
            render_elements = get_render_elements()

            # Validate paths
            path_warnings = validate_render_element_paths(render_elements)
            feedback_messages.extend(path_warnings)

            # Validate ignore list - use clean names without emojis
            ignore_names = []
            for i in range(self.ignore_elements_list.count()):
                item = self.ignore_elements_list.item(i)
                # Get clean name from item data, fallback to text without emojis
                clean_name = item.data(Qt.UserRole)
                if not clean_name:
                    # Fallback: remove emojis from display text
                    clean_name = self._remove_emojis(item.text())
                ignore_names.append(clean_name)

            if ignore_names:
                scene_element_names = [elem.name for elem in render_elements]
                invalid_names = [name for name in ignore_names if name not in scene_element_names]

                for invalid_name in invalid_names:
                    # Use clean name in feedback message to avoid Unicode issues
                    clean_invalid_name = self._remove_emojis(invalid_name)
                    feedback_messages.append(
                        f"Ignored element '{clean_invalid_name}' not found in scene"
                    )

        except Exception as e:
            _logger.error(f"Error validating render elements: {e}")
            feedback_messages.append(f"Error validating render elements: {e}")

        # Display feedback
        if feedback_messages:
            self.validation_feedback_label.setText("\n".join(feedback_messages))
            self.validation_feedback_label.setStyleSheet("color: orange;")
        else:
            self.validation_feedback_label.setText("✓ Render elements configuration is valid")
            self.validation_feedback_label.setStyleSheet("color: green;")

        # Emit validation signal
        self.validation_changed.emit(feedback_messages)

    def get_settings_dict(self):
        """
        Get current widget settings as dictionary for parameter generation.
        """
        return {
            "enabled_modify_render_elements": self.modify_render_elements_checkbox.isChecked(),
            "render_elements": self.render_elements_checkbox.isChecked(),
            "render_elements_update_paths": self.update_paths_checkbox.isChecked(),
            "render_elements_include_name_in_path": self.include_name_in_path_checkbox.isChecked(),
            "render_elements_include_type_in_path": self.include_type_in_path_checkbox.isChecked(),
            "render_elements_include_name_in_filename": self.include_name_in_filename_checkbox.isChecked(),
            "render_elements_include_type_in_filename": self.include_type_in_filename_checkbox.isChecked(),
            "vray_render_elements_vfb_control": self.vray_vfb_control_checkbox.isChecked(),
            "vray_split_buffer_support": self.vray_split_buffer_checkbox.isChecked(),
            "ignore_render_elements_by_name": [
                self.ignore_elements_list.item(i).data(Qt.UserRole)
                or self._remove_emojis(self.ignore_elements_list.item(i).text())
                for i in range(self.ignore_elements_list.count())
            ],
        }

    def update_settings_from_data_class(self, settings):
        """
        Update widget controls from data class settings.
        """
        self.modify_render_elements_checkbox.setChecked(settings.enabled_modify_render_elements)
        self.render_elements_checkbox.setChecked(settings.render_elements)
        self.update_paths_checkbox.setChecked(settings.render_elements_update_paths)
        self.include_name_in_path_checkbox.setChecked(settings.render_elements_include_name_in_path)
        self.include_type_in_path_checkbox.setChecked(settings.render_elements_include_type_in_path)
        self.include_name_in_filename_checkbox.setChecked(
            settings.render_elements_include_name_in_filename
        )
        self.include_type_in_filename_checkbox.setChecked(
            settings.render_elements_include_type_in_filename
        )
        self.vray_vfb_control_checkbox.setChecked(settings.vray_render_elements_vfb_control)
        self.vray_split_buffer_checkbox.setChecked(settings.vray_split_buffer_support)

        # Update ignore list with clean names
        self.ignore_elements_list.clear()
        for name in settings.ignore_render_elements_by_name:
            clean_name = self._remove_emojis(name)  # Ensure name is clean
            ignore_item = QListWidgetItem(clean_name)
            ignore_item.setData(Qt.UserRole, clean_name)  # Store clean name as data
            self.ignore_elements_list.addItem(ignore_item)

    def update_data_class_from_settings(self, settings):
        """
        Update data class settings from widget controls.
        """
        settings.enabled_modify_render_elements = self.modify_render_elements_checkbox.isChecked()
        settings.render_elements = self.render_elements_checkbox.isChecked()
        settings.render_elements_update_paths = self.update_paths_checkbox.isChecked()
        settings.render_elements_include_name_in_path = (
            self.include_name_in_path_checkbox.isChecked()
        )
        settings.render_elements_include_type_in_path = (
            self.include_type_in_path_checkbox.isChecked()
        )
        settings.render_elements_include_name_in_filename = (
            self.include_name_in_filename_checkbox.isChecked()
        )
        settings.render_elements_include_type_in_filename = (
            self.include_type_in_filename_checkbox.isChecked()
        )
        settings.vray_render_elements_vfb_control = self.vray_vfb_control_checkbox.isChecked()
        settings.vray_split_buffer_support = self.vray_split_buffer_checkbox.isChecked()

        # Update ignore list
        settings.ignore_render_elements_by_name = [
            self.ignore_elements_list.item(i).text()
            for i in range(self.ignore_elements_list.count())
        ]
