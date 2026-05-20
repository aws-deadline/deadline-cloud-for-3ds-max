"""
3ds Max Deadline Cloud Submitter - UI widgets for the Scene Settings tab.

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import logging
import os

import pymxs  # noqa
from deadline.max_submitter.data_const import (
    ALL_CAMERAS_STR,
    ALL_STATE_SETS_STR,
    ALL_STEREO_CAMERAS_STR,
    ALLOWED_EXTENSIONS,
    ALLOWED_RENDERERS,
    SCENE_TWEAKS_MATS,
    STEREO_CAMERA_OPTIONS,
)
from deadline.max_shared.utilities.filename_utils import format_output_filename, get_tokens_tooltip
from deadline.client.ui import block_signals
from pymxs import runtime as rt
from qtpy.QtCore import QRegularExpression, QSize, Qt  # type: ignore
from qtpy.QtGui import QRegularExpressionValidator  # type: ignore
from qtpy.QtWidgets import (  # type: ignore
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from deadline.max_shared.utilities.max_utils import get_batch_render_views
from deadline.max_submitter.data_classes import SubmissionMode
from deadline.max_submitter.utilities import max_utils
from deadline.max_submitter.ui.render_elements_widget import RenderElementsWidget

_logger = logging.getLogger(__name__)


class ElideMiddleDelegate(QStyledItemDelegate):
    """Item delegate that elides text in the middle (e.g. long file paths)."""

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.textElideMode = Qt.ElideMiddle


class FileSearchLineEdit(QWidget):
    """
    Widget used to contain a line edit and a button which opens a file search box.
    """

    def __init__(self, file_format=None, directory_only=False, parent=None):
        super().__init__(parent=parent)

        if directory_only and file_format is not None:
            raise ValueError("")

        self.file_format = file_format
        self.directory_only = directory_only

        lyt = QHBoxLayout(self)
        lyt.setContentsMargins(0, 0, 0, 0)

        self.edit = QLineEdit(self)
        self.btn = QPushButton("...", parent=self)
        self.btn.setMaximumSize(QSize(100, 40))
        self.btn.clicked.connect(self.get_file)

        lyt.addWidget(self.edit)
        lyt.addWidget(self.btn)

    def get_file(self):
        """
        Open a file picker to allow users to choose a file.
        """
        if self.directory_only:
            new_txt = QFileDialog.getExistingDirectory(
                self,
                "Open Directory",
                self.edit.text(),
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )
        else:
            new_txt = QFileDialog.getOpenFileName(self, "Select File", self.edit.text())

        if new_txt:
            self.edit.setText(new_txt)

    def setText(self, txt: str) -> None:  # pylint: disable=invalid-name
        """
        Sets the text of the internal line edit.
        Naming for function is analogous to the QWidget function with the same purpose.
        """
        self.edit.setText(txt)

    def text(self) -> str:
        """
        Retrieves the text from the internal line edit.
        Naming for function is analogous to the QWidget function with the same purpose.
        """
        return self.edit.text()


class SceneSettingsWidget(QWidget):
    """
    Widget containing all top level scene settings.
    """

    def __init__(self, initial_settings, parent=None):
        super().__init__(parent=parent)

        self.developer_options = (
            os.environ.get("DEADLINE_ENABLE_DEVELOPER_OPTIONS", "").upper() == "TRUE"
        )

        # Get 3ds Max specific lists for populating combo boxes
        self.renderers = max_utils.get_renderers()
        self.state_sets = max_utils.get_state_set_names()

        self._build_ui(initial_settings)
        self._configure_settings(initial_settings)

        # Assign callback that updates the renderer in the UI each time it changes in the render settings
        rt.pyCallback = self._update_renderer
        rt.callbacks.addScript(rt.Name("postRendererChange"), "pyCallback()")
        QApplication.instance().focusChanged.connect(self.on_focus_changed)

    def _build_ui(self, settings):
        """
        Function that creates all the Qt UI elements for the job specific settings tab
        """
        lyt = QGridLayout(self)
        lyt.setColumnStretch(0, 0)
        lyt.setColumnStretch(1, 1)

        # Project path
        self.proj_path_txt = QLineEdit(self)
        self.proj_path_txt.setEnabled(False)
        lyt.addWidget(QLabel("Project Path"), 0, 0)
        lyt.addWidget(self.proj_path_txt, 0, 1)

        # Submission Mode selection
        submission_mode_grp_box = QGroupBox("Submission Mode", self)
        submission_mode_lyt = QHBoxLayout()
        submission_mode_grp_box.setLayout(submission_mode_lyt)
        self.mode_default_radio = QRadioButton("Default", self)
        self.mode_batch_render_radio = QRadioButton("Batch Render", self)
        self.mode_default_radio.setChecked(True)
        submission_mode_lyt.addWidget(self.mode_default_radio)
        submission_mode_lyt.addWidget(self.mode_batch_render_radio)
        # Button group ensures mutual exclusivity
        self._submission_mode_group = QButtonGroup(self)
        self._submission_mode_group.addButton(self.mode_default_radio)
        self._submission_mode_group.addButton(self.mode_batch_render_radio)
        self.mode_default_radio.toggled.connect(lambda _: self._on_submission_mode_changed())
        self.mode_batch_render_radio.toggled.connect(lambda _: self._on_submission_mode_changed())
        lyt.addWidget(submission_mode_grp_box, 1, 0, 1, 2)

        # Default mode controls group box (State Sets + Stereo Cameras + Cameras + Output)
        self.default_mode_grp_box = QGroupBox("Default Mode", self)
        default_mode_lyt = QGridLayout()
        default_mode_lyt.setColumnStretch(0, 0)
        default_mode_lyt.setColumnStretch(1, 1)
        self.default_mode_grp_box.setLayout(default_mode_lyt)

        # Output path
        self.output_path_txt = FileSearchLineEdit(directory_only=True)
        default_mode_lyt.addWidget(QLabel("Output Path"), 0, 0)
        default_mode_lyt.addWidget(self.output_path_txt, 0, 1)

        # Output filename settings (pattern + preview)
        self._build_output_filename_settings_ui()
        default_mode_lyt.addWidget(self.output_filename_grp_box, 1, 0, 1, 2)

        # Output extension
        self.output_ext_box = QComboBox(self)
        for ext in ALLOWED_EXTENSIONS:
            self.output_ext_box.addItem(ext[0], ext[1])
        default_mode_lyt.addWidget(QLabel("Output File Extension"), 2, 0)
        default_mode_lyt.addWidget(self.output_ext_box, 2, 1)

        # State Set selection
        self.state_sets_box = QComboBox(self)
        self.state_sets_box.addItem("All State Sets", "All State Sets")
        self.state_sets_box.setToolTip(
            "Updating this selection also updates the active state set of your scene."
        )
        for state_set in self.state_sets:
            self.state_sets_box.addItem(state_set[0], state_set[1])
        default_mode_lyt.addWidget(QLabel("State Sets"), 3, 0)
        default_mode_lyt.addWidget(self.state_sets_box, 3, 1)
        (self.state_sets_box.currentIndexChanged.connect(self._update_state_set))
        self.state_sets_box.currentIndexChanged.connect(lambda _: self._update_filename_preview())

        # Stereo Cameras selection
        self.stereo_cameras_box = QComboBox(self)
        # Checks for use and installation of the stereo camera plugin
        # If it is used and loaded: give user all stereo camera options
        if max_utils.stereo_plugin_used_and_loaded():
            for option in STEREO_CAMERA_OPTIONS:
                self.stereo_cameras_box.addItem(option[0], option[1])
            self.stereo_cameras_box.setEnabled(True)
        # If it is used but not loaded: only give all or none option
        # Note: in this case left and right only get displaced visually, so there's no way to differentiate between
        #       the eyes code wise
        elif max_utils.stereo_plugin_used_but_not_loaded():
            self.stereo_cameras_box.addItem("Left, Right and Center", "All")
            self.stereo_cameras_box.addItem("Disable Stereo Camera Submission", "None")
            self.stereo_cameras_box.setEnabled(True)
        # If it is not used: no options, field gets disabled
        else:
            self.stereo_cameras_box.addItem("Disable Stereo Camera Submission", "None")
            self.stereo_cameras_box.setEnabled(False)
        default_mode_lyt.addWidget(QLabel("Stereo Cameras Selection"), 4, 0)
        default_mode_lyt.addWidget(self.stereo_cameras_box, 4, 1)
        self.stereo_cameras_box.currentIndexChanged.connect(self._fill_cameras_box)

        # Cameras to render selection
        self.cameras_box = QComboBox(self)
        default_mode_lyt.addWidget(QLabel("Cameras To Render"), 5, 0)
        default_mode_lyt.addWidget(self.cameras_box, 5, 1)
        self.cameras_box.currentIndexChanged.connect(lambda _: self._update_filename_preview())

        lyt.addWidget(self.default_mode_grp_box, 2, 0, 1, 2)

        # Batch Rendering section
        self._build_batch_rendering_ui()
        lyt.addWidget(self.batch_rendering_grp_box, 3, 0, 1, 2)

        # Renderer
        self.renderers_box = QComboBox(self)
        self.renderers_box.setEnabled(False)
        self.renderers_box.setToolTip(
            "Needs to be set in Render Settings! \n"
            "If you are using State Sets, be sure to record any changes in the State Set."
        )
        self.renderers_box.addItem("Current Renderer not supported by Submitter")
        for renderer in self.renderers:

            if str(renderer).split("__")[0] in ALLOWED_RENDERERS:
                self.renderers_box.addItem(renderer.replace("_", " "), renderer)
        lyt.addWidget(QLabel("Renderer"), 4, 0)
        lyt.addWidget(self.renderers_box, 4, 1)

        # Override frame range
        self.frame_override_chck = QCheckBox("Override Frame Range", self)
        self.frame_override_txt = QLineEdit(self)
        self.frame_override_txt.setToolTip(
            "Frame range you want to use as override. \n" "E.g. 1,3,5-10 or 1, 3, 5-10"
        )
        self.style_sheet = self.frame_override_txt.styleSheet()
        lyt.addWidget(self.frame_override_chck, 5, 0)
        lyt.addWidget(self.frame_override_txt, 5, 1)
        self.frame_override_chck.stateChanged.connect(self.activate_frame_override_changed)

        # Frame range validation
        # E.g.: 1-4,6,8,9-12
        # Note: ?: in regex groups all together as one result
        regex = QRegularExpression(
            r"\d+"  # unlimited numbers
            r"(?:-\d+)?"  # optional dash (-) and one or more digits
            r"(?:,(\s)?\d+"  # new parts split by commas (,) , allow 1 space for readability
            r"(?:-\d+)?)*"
        )  # can be repeated endlessly
        validator = QRegularExpressionValidator(regex, self.frame_override_txt)
        self.frame_override_txt.setValidator(validator)

        # Scene tweaks group box
        self._build_scene_tweaks_ui()
        lyt.addWidget(self.scene_tweaks_grp_box, 6, 0, 1, 2)

        # Render elements widget
        self.render_elements_widget = RenderElementsWidget(settings, self)
        self.render_elements_widget.validation_changed.connect(
            self._on_render_elements_validation_changed
        )
        lyt.addWidget(self.render_elements_widget, 7, 0, 1, 2)

        if self.developer_options:
            self.include_adaptor_wheels = QCheckBox(
                "Developer Option: Include Adaptor Wheels. Add the 'wheels' directory from Job Attachments Tab.",
                self,
            )
            lyt.addWidget(self.include_adaptor_wheels, 8, 0, 1, 2)

        # Task run timeout row
        timeout_row_widget = QWidget(self)
        timeout_row_lyt = QHBoxLayout(timeout_row_widget)
        timeout_row_lyt.setContentsMargins(0, 0, 0, 0)

        self.task_timeout_chck = QCheckBox("Override Task Run Timeout", self)
        self.task_timeout_chck.setToolTip(
            "When checked, a frame render that exceeds the timeout will be cancelled.\n"
            "Leave unchecked to allow renders to run until complete."
        )

        self.task_timeout_spinbox = QSpinBox(self)
        self.task_timeout_spinbox.setMinimum(1)
        self.task_timeout_spinbox.setMaximum(86400)
        self.task_timeout_spinbox.setSingleStep(60)
        self.task_timeout_spinbox.setSuffix(" s")
        self.task_timeout_spinbox.setToolTip(
            "Maximum seconds a single frame render may run before it is cancelled.\n"
            "Examples: 3600 = 1 hour, 7200 = 2 hours, 86400 = 24 hours."
        )

        timeout_row_lyt.addWidget(self.task_timeout_chck)
        timeout_row_lyt.addWidget(self.task_timeout_spinbox)
        timeout_row_lyt.addStretch()

        lyt.addWidget(timeout_row_widget, 9, 0, 1, 2)

        self.task_timeout_chck.toggled.connect(self._on_task_timeout_toggled)
        self.task_timeout_spinbox.valueChanged.connect(self._on_task_timeout_value_changed)

        lyt.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), 10, 0)

        self._fill_cameras_box(0)

    def _build_scene_tweaks_ui(self):
        """
        Create a QGroupBox for the scene tweaks
        """
        # Create groupbox
        self.scene_tweaks_grp_box = QGroupBox()
        self.scene_tweaks_grp_box.setTitle("Scene Tweaks")
        scene_tweaks_lyt = QGridLayout()
        self.scene_tweaks_grp_box.setLayout(scene_tweaks_lyt)

        # Merge XRef Objects check box
        self.merge_xref_obj_chck = QCheckBox("Merge Object XRefs", self)
        scene_tweaks_lyt.addWidget(self.merge_xref_obj_chck, 1, 0)

        # Merge XRef Scene check box
        self.merge_xref_scn_chck = QCheckBox("Merge Scene XRefs", self)
        scene_tweaks_lyt.addWidget(self.merge_xref_scn_chck, 1, 1)

        # Clear Material Editor check box
        self.clear_mat_chck = QCheckBox("Clear Material Editor In The Submitted File", self)
        scene_tweaks_lyt.addWidget(self.clear_mat_chck, 2, 0)

        # Unlock Material Editor Renderer check box
        self.unlock_mat_chck = QCheckBox("Unlock Material Editor Renderer", self)
        scene_tweaks_lyt.addWidget(self.unlock_mat_chck, 2, 1)

        # Apply Custom Material check box
        self.custom_mat_chck = QCheckBox("Apply Custom Material To Scene", self)
        self.custom_mat_chck.setToolTip(
            "Custom Material does not get applied on any not-merged XRefs in the " "scene."
        )
        scene_tweaks_lyt.addWidget(self.custom_mat_chck, 3, 0)
        self.custom_mat_chck.stateChanged.connect(self.activate_custom_material_changed)

        # Custom Material combo box
        self.custom_mat_box = QComboBox(self)
        for mat in SCENE_TWEAKS_MATS:
            self.custom_mat_box.addItem(mat, mat)
        scene_tweaks_lyt.addWidget(self.custom_mat_box, 3, 1)

    def _build_output_filename_settings_ui(self):
        """
        Create a QGroupBox for the output filename pattern settings.
        Output filename settings shows a token-based
        pattern field and a live preview label, allowing users
        to customize filenames according to scene tokens
        """
        self.output_filename_grp_box = QGroupBox()
        self.output_filename_grp_box.setTitle("Output Filename Settings")
        fn_lyt = QGridLayout()
        fn_lyt.setColumnStretch(0, 0)
        fn_lyt.setColumnStretch(1, 1)
        self.output_filename_grp_box.setLayout(fn_lyt)

        # Filename Pattern
        self.output_filename_pattern_txt = QLineEdit(self)
        self.output_filename_pattern_txt.setToolTip(get_tokens_tooltip())
        fn_lyt.addWidget(QLabel("Filename Pattern"), 0, 0)
        fn_lyt.addWidget(self.output_filename_pattern_txt, 0, 1)
        self.output_filename_pattern_txt.textChanged.connect(self._update_filename_preview)

        # Filename Preview
        self.filename_preview_label = QLabel(self)
        self.filename_preview_label.setStyleSheet("color: gray; font-style: italic;")
        self.filename_preview_label.setToolTip("Example preview of the resolved output filename")
        fn_lyt.addWidget(QLabel("Filename Preview"), 1, 0)
        fn_lyt.addWidget(self.filename_preview_label, 1, 1)

    def _update_filename_preview(self):
        """
        Update the filename preview label based on current UI values.
        """

        pattern = self.output_filename_pattern_txt.text()

        # Get state set name from current selection
        state_set_text = self.state_sets_box.currentText()
        state_set_name = "" if state_set_text == "All State Sets" else state_set_text

        # For "All State Sets", show first state set as example if available
        if state_set_text == "All State Sets" and self.state_sets:
            state_set_name = self.state_sets[0][0]

        # Get camera name from current selection
        camera_data = self.cameras_box.currentData()
        is_all_cameras = camera_data in (ALL_CAMERAS_STR, ALL_STEREO_CAMERAS_STR)

        if is_all_cameras and hasattr(self, "cameras") and self.cameras:
            camera_name = self.cameras[0]
        elif not is_all_cameras and camera_data:
            camera_name = camera_data
        else:
            camera_name = ""

        # Get scene name
        scene_name = max_utils.get_scene_name()

        preview = format_output_filename(
            pattern=pattern,
            camera_name=camera_name,
            state_set_name=state_set_name,
            scene_name=scene_name,
        )

        self.filename_preview_label.setText(preview)

    def _build_batch_rendering_ui(self):
        """
        Create a QGroupBox for the batch rendering controls
        """
        # Create groupbox
        self.batch_rendering_grp_box = QGroupBox()
        self.batch_rendering_grp_box.setTitle("Batch Rendering")
        batch_rendering_lyt = QGridLayout()
        batch_rendering_lyt.setColumnStretch(0, 1)
        batch_rendering_lyt.setColumnStretch(1, 1)
        self.batch_rendering_grp_box.setLayout(batch_rendering_lyt)

        # Open Batch Render Dialog button
        self.open_batch_dialog_btn = QPushButton("Open Batch Render Dialog", self)
        self.open_batch_dialog_btn.setToolTip("Open 3ds Max's native Batch Render Manager dialog")
        batch_rendering_lyt.addWidget(self.open_batch_dialog_btn, 0, 0, 1, 2)
        self.open_batch_dialog_btn.clicked.connect(self._open_batch_render_dialog)

        # Info label showing enabled item count
        self.batch_views_info_label = QLabel("No batch views configured", self)
        batch_rendering_lyt.addWidget(self.batch_views_info_label, 1, 0, 1, 2)

        # batch views table widget (read-only)
        self.batch_views_table = QTableWidget(self)
        self.batch_views_table.setColumnCount(7)
        self.batch_views_table.setHorizontalHeaderLabels(
            [
                "",
                "Name",
                "Camera",
                "Scene\nState",
                "Preset",
                "Output\nPath",
                "Override\nPreset",
            ]
        )
        self.batch_views_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.batch_views_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_views_table.setAlternatingRowColors(True)
        # Enable horizontal scrolling so columns can size to content
        self.batch_views_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.batch_views_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # First column (enabled checkmark) is fixed narrow width
        header = self.batch_views_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.batch_views_table.setColumnWidth(0, 20)
        # Remaining columns are user-resizable; last column stretches to fill
        for col in range(1, 6):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        # Set initial widths so all columns are visible without horizontal scrolling
        self.batch_views_table.setColumnWidth(1, 80)  # Name
        self.batch_views_table.setColumnWidth(2, 60)  # Camera
        self.batch_views_table.setColumnWidth(3, 70)  # Scene State
        self.batch_views_table.setColumnWidth(4, 60)  # Preset
        self.batch_views_table.setColumnWidth(5, 70)  # Output Path
        self.batch_views_table.setWordWrap(False)
        self.batch_views_table.setMinimumHeight(120)
        self.batch_views_table.setMaximumHeight(300)
        self.batch_views_table.setToolTip("Batch render views from 3ds Max Batch Render Manager")
        # Use middle-elide for path columns so long paths show as "start…end"
        elide_delegate = ElideMiddleDelegate(self.batch_views_table)
        self.batch_views_table.setItemDelegateForColumn(4, elide_delegate)  # Preset
        self.batch_views_table.setItemDelegateForColumn(5, elide_delegate)  # Output Path
        batch_rendering_lyt.addWidget(self.batch_views_table, 2, 0, 1, 2)

    def _on_render_elements_validation_changed(self, warnings):
        """
        Handle validation changes from the enhanced render elements widget.

        :param warnings: List of validation warning messages
        :type warnings: list[str]
        """
        # Log validation warnings
        if warnings:
            _logger.warning(f"Render elements validation warnings: {warnings}")
        else:
            _logger.debug("Render elements validation passed")

    def _update_state_set(self, _):
        """
        Set the active state set based on the currently selected option in the ui
        """
        index = self.state_sets_box.currentData()
        if index == ALL_STATE_SETS_STR:
            _logger.debug("All State Sets selected in UI")
            return
        # Set the current state set
        rt.execute(
            f"stateSetsDotNetObject = dotNetObject "
            f'"Autodesk.Max.StateSets.Plugin" \n'
            f"stateSets = stateSetsDotNetObject.Instance \n"
            f"masterState = stateSets.EntityManager.RootEntity."
            f"MasterStateSet \n"
            f"needState = masterState.Children.Item[{index}]\n"
            f"masterState.CurrentState = #(needState)"
        )

    def _fill_cameras_box(self, _):
        """
        Fill the Cameras combo box based on the selected value in the Stereo
        Cameras combo box
        """
        with block_signals(self.cameras_box):
            # Save previously selected camera to be able to reselect it later
            saved_camera = self.cameras_box.currentData()

            # Clear the list and re-add the 'All' option
            self.cameras_box.clear()
            self.cameras_box.addItem("All Cameras in List", "All Cameras")

            # Collect all cameras in the scene
            self.cameras = max_utils.get_camera_names()

            # Collect all stereo cameras in the scene
            all_stereo_cameras = max_utils.get_stereo_camera_names()

            # Check if there are any stereo cameras present in the scene
            if not all_stereo_cameras:
                _logger.info("There are no stereo cameras in the scene")
                for camera_name in self.cameras:
                    self.cameras_box.addItem(camera_name, camera_name)

                # if previously selected still in list, reselect
                index = self.cameras_box.findData(saved_camera)
                if index >= 0:
                    self.cameras_box.setCurrentIndex(index)

                # Assign all cameras to the stereo cameras to prevent error in update_settings function
                self.stereo_cameras = self.cameras
                return

            self._fill_cameras_box_stereo(all_stereo_cameras)

            # Append the selectable cameras to the combo box
            for camera_name in self.cameras:
                self.cameras_box.addItem(camera_name, camera_name)

            # If previously selected still in list, reselect
            index = self.cameras_box.findData(saved_camera)
            if index >= 0:
                self.cameras_box.setCurrentIndex(index)

    def _fill_cameras_box_stereo(self, all_stereo_cameras):
        """
        Update the cameras and stereo_cameras variables according to the stereo camera selection.
        """
        # Split up the stereo cameras
        left_cams = max_utils.get_left_stereo_camera_names()
        right_cams = max_utils.get_right_stereo_camera_names()
        center_cams = max_utils.get_center_stereo_camera_names()

        # Value for easily assigning them to scene settings object
        self.stereo_cameras = max_utils.get_stereo_camera_names()

        _logger.debug(
            f"Changing Camera Selection filter: '{self.stereo_cameras_box.currentText()}'"
        )
        cams_to_remove = []
        # Determine the list of selectable cameras
        if self.stereo_cameras_box.currentData() == "None":
            _logger.info("Changing Camera Selection filter to include No Stereo Cameras")
            cams_to_remove = all_stereo_cameras
        # Only add all stereo cameras option if stereo cameras are allowed for submission
        else:
            self.cameras_box.addItem("All Stereo Cameras in List", "All Stereo Cameras")
            _logger.info(
                "Changing Camera Selection filter to include "
                f"{self.stereo_cameras_box.currentText()} from the Stereo Cameras"
            )

        if self.stereo_cameras_box.currentData() == "Left":
            cams_to_remove = right_cams + center_cams

        if self.stereo_cameras_box.currentData() == "Right":
            cams_to_remove = left_cams + center_cams

        if self.stereo_cameras_box.currentData() == "Center":
            cams_to_remove = right_cams + left_cams

        if self.stereo_cameras_box.currentData() == "Left_Right":
            cams_to_remove = center_cams

        if cams_to_remove:
            for cam in cams_to_remove:
                self.cameras.remove(cam)
                self.stereo_cameras.remove(cam)

    def on_focus_changed(self, old_widget, new_widget):
        """
        Event handler for when the active widget changes.
        Auto-refreshes batch views when the submitter regains focus,
        and validates frame range in frame_override_txt QLineEdit.

        :param old_widget: widget that lost focus
        :type old_widget: any QWidget
        :param new_widget: widget that gained focus
        :type new_widget: any QWidget
        """

        # Auto-refresh batch views when the submitter regains focus
        if new_widget is not None and self.isAncestorOf(new_widget):
            if self.mode_batch_render_radio.isChecked():
                self._refresh_batch_views()

        if self.frame_override_txt is not old_widget:
            return

        if not self.frame_override_txt.text():
            # color text field red and show a message box
            _logger.error("No frame range inputted")
            self.frame_override_txt.setStyleSheet("background-color: red")
            QMessageBox.warning(
                self,
                "Empty Frame Range",
                "You entered no frame range. Please enter a valid frame range",
            )
            return

        if not max_utils.is_correct_frame_range(self.frame_override_txt.text()):
            # color text field red and show a message box
            _logger.error("Not a correct frame range")
            self.frame_override_txt.setStyleSheet("background-color: red")
            QMessageBox.warning(
                self,
                "Invalid Frame Range",
                "You entered an invalid frame range. Please make sure that the first number in "
                "the range is smaller than the second number. \n"
                "E.g.: 10-5 is invalid, 5-10 is valid",
            )
            return

        if max_utils.get_duplicate_frames(self.frame_override_txt.text()):
            # color text field red and show a message box
            _logger.error("Not a correct frame range")
            self.frame_override_txt.setStyleSheet("background-color: red")
            QMessageBox.warning(
                self,
                "Invalid Frame Range",
                "You have duplicate frames. Duplicate frames: "
                f"{max_utils.get_duplicate_frames(self.frame_override_txt.text())}",
            )
            return

        self.frame_override_txt.setStyleSheet(self.style_sheet)

    def _configure_settings(self, settings):
        """
        Set the initial status of the ui fields
        """
        settings.renderer = str(rt.renderers.current).split(":")[0]
        self.proj_path_txt.setText(settings.project_path)
        self.output_path_txt.setText(settings.output_path)
        self.output_filename_pattern_txt.setText(settings.output_filename_pattern)
        self.frame_override_chck.setChecked(settings.override_frame_range)
        self.frame_override_txt.setEnabled(settings.override_frame_range)
        self.frame_override_txt.setText(settings.frame_list)

        index = self.output_ext_box.findData(settings.output_ext)
        if index >= 0:
            self.output_ext_box.setCurrentIndex(index)

        index = self.state_sets_box.findData(settings.state_set)
        if index >= 0:
            self.state_sets_box.setCurrentIndex(index)

        index = self.renderers_box.findData(settings.renderer)
        if index >= 0:
            self.renderers_box.setCurrentIndex(index)

        index = self.stereo_cameras_box.findData(settings.stereo_camera)
        if index >= 0:
            self.stereo_cameras_box.setCurrentIndex(index)

        index = self.cameras_box.findData(settings.camera_selection)
        if index >= 0:
            self.cameras_box.setCurrentIndex(index)

        self.merge_xref_obj_chck.setChecked(settings.merge_xref_obj)
        self.merge_xref_scn_chck.setChecked(settings.merge_xref_scn)
        self.clear_mat_chck.setChecked(settings.clear_mat)
        self.unlock_mat_chck.setChecked(settings.unlock_mat)
        self.custom_mat_chck.setChecked(settings.custom_mat_chck)
        self.custom_mat_box.setEnabled(settings.custom_mat_chck)

        index = self.custom_mat_box.findData(settings.custom_mat)
        if index >= 0:
            self.custom_mat_box.setCurrentIndex(index)

        if self.developer_options:
            (self.include_adaptor_wheels.setChecked(settings.include_adaptor_wheels))

        # Update render elements widget from settings
        self.render_elements_widget.update_settings_from_data_class(settings)

        # Update batch rendering settings — restore radio button state from submission_mode
        if settings.submission_mode == SubmissionMode.BATCH_RENDER.value:
            self.mode_batch_render_radio.setChecked(True)
        else:
            self.mode_default_radio.setChecked(True)
        # Refresh batch views list on initial load
        if settings.submission_mode == SubmissionMode.BATCH_RENDER.value:
            self._refresh_batch_views()

        # Restore task run timeout state
        timeout_enabled = settings.task_run_timeout_seconds > 0
        self.task_timeout_chck.setChecked(timeout_enabled)
        self.task_timeout_spinbox.setValue(
            settings.task_run_timeout_seconds if timeout_enabled else 3600
        )
        self.task_timeout_spinbox.setEnabled(timeout_enabled)

        # Sync group box enabled states with the selected radio button
        self._on_submission_mode_changed()

    def update_settings(self, settings):
        """
        Update a scene settings object with the latest values.
        """
        settings.project_path = self.proj_path_txt.text()
        settings.output_path = self.output_path_txt.text()
        settings.output_name = self.output_filename_pattern_txt.text()
        settings.output_filename_pattern = self.output_filename_pattern_txt.text()
        settings.output_ext = self.output_ext_box.currentData()

        settings.override_frame_range = self.frame_override_chck.isChecked()
        settings.frame_list = self.frame_override_txt.text()

        settings.state_set = self.state_sets_box.currentText()
        settings.state_set_index = self.state_sets_box.currentData()
        settings.renderer = self.renderers_box.currentData()

        settings.stereo_camera = self.stereo_cameras_box.currentData()
        settings.camera_selection = self.cameras_box.currentData()
        settings.all_cameras = self.cameras
        settings.all_stereo_cameras = self.stereo_cameras

        settings.merge_xref_obj = self.merge_xref_obj_chck.isChecked()
        settings.merge_xref_scn = self.merge_xref_scn_chck.isChecked()
        settings.clear_mat = self.clear_mat_chck.isChecked()
        settings.unlock_mat = self.unlock_mat_chck.isChecked()
        settings.custom_mat_chck = self.custom_mat_chck.isChecked()
        settings.custom_mat = self.custom_mat_box.currentData()

        if self.developer_options:
            settings.include_adaptor_wheels = self.include_adaptor_wheels.isChecked()
        else:
            settings.include_adaptor_wheels = False

        # Update render elements settings from widget
        self.render_elements_widget.update_data_class_from_settings(settings)

        # Update render element output filenames from detected elements
        # Keep render_element_output_filenames empty for now
        settings.render_element_output_filenames = []

        # Update batch rendering settings
        settings.submission_mode = (
            SubmissionMode.BATCH_RENDER.value
            if self.mode_batch_render_radio.isChecked()
            else SubmissionMode.DEFAULT.value
        )

        # Query 3ds Max directly for enabled batch views
        try:
            batch_views = get_batch_render_views()
            enabled_views = [item.name for item in batch_views if item.enabled]
        except Exception as e:
            _logger.warning(f"Failed to get batch views from 3ds Max: {e}")
            enabled_views = []
        settings.batch_render.enabled_views = enabled_views

        # Task run timeout
        if self.task_timeout_chck.isChecked():
            settings.task_run_timeout_seconds = self.task_timeout_spinbox.value()
        else:
            settings.task_run_timeout_seconds = 0

    def activate_frame_override_changed(self, state):
        """
        Set the activated/deactivated status of the Frame override text box
        """
        self.frame_override_txt.setEnabled(Qt.CheckState(state) == Qt.Checked)

    def activate_custom_material_changed(self, state):
        """
        Set the activated/deactivated status of the Custom material combo box
        """
        self.custom_mat_box.setEnabled(Qt.CheckState(state) == Qt.Checked)

    def _on_task_timeout_toggled(self, checked: bool) -> None:
        """
        Enable/disable the timeout spin box and update the settings value.
        """
        self.task_timeout_spinbox.setEnabled(checked)

    def _on_task_timeout_value_changed(self, value: int) -> None:
        """
        Keep the spin box value in sync (actual settings write happens in update_settings).
        """
        pass  # update_settings reads the widget state; no extra action needed here

    def _update_renderer(self):
        """
        Gets the current renderer from the render settings and set it in the UI
        """
        _logger.debug("Renderer updated in Render Settings")
        renderer = str(rt.renderers.current).split(":")[0]
        index = self.renderers_box.findData(renderer)
        if index >= 0:
            self.renderers_box.setCurrentIndex(index)
        # If the selected renderer isn't in the list set it to the 'Renderer not supported' option
        else:
            self.renderers_box.setCurrentIndex(0)

    def _on_batch_render_enabled_changed(self, state):
        """
        Handle batch render checkbox state change
        """
        enabled = Qt.CheckState(state) == Qt.Checked
        _logger.debug(f"Batch render enabled changed to: {enabled}")

        if enabled:
            self._refresh_batch_views()
        else:
            self._clear_batch_views()

    def _on_submission_mode_changed(self):
        """Show/hide controls based on the selected submission mode.

        Uses a map to correlate modes with their associated control groups,
        making it easy to add new modes in the future.
        """
        mode_controls = {
            self.mode_default_radio: [self.default_mode_grp_box],
            self.mode_batch_render_radio: [self.batch_rendering_grp_box],
        }

        for radio, controls in mode_controls.items():
            visible = radio.isChecked()
            for control in controls:
                control.setVisible(visible)

        if self.mode_batch_render_radio.isChecked():
            self._refresh_batch_views()
        else:
            self._clear_batch_views()

        self._update_filename_preview()

    def _open_batch_render_dialog(self):
        """
        Open 3ds Max's native Batch Render Manager dialog
        """
        try:
            # Use actionMan to execute the Batch Render menu action
            # This is the same method Deadline 10 used
            rt.actionMan.executeAction(-43434444, "4096")
            _logger.debug("Opened Batch Render Manager dialog")
        except Exception as e:
            _logger.error(f"Failed to open Batch Render Manager dialog: {e}")
            QMessageBox.warning(
                self,
                "Error Opening Batch Render Dialog",
                f"Failed to open the Batch Render Manager dialog:\n{str(e)}",
            )

    def _clear_batch_views(self):
        """Clear the batch views table and reset the info label."""
        self.batch_views_table.setRowCount(0)
        self.batch_views_info_label.setText("No batch views configured")

    def _refresh_batch_views(self):
        """
        Refresh the list of batch views from the Batch Render Manager
        """
        try:
            batch_views = get_batch_render_views()
            self._populate_batch_views_list(batch_views)
            _logger.debug(f"Refreshed batch items list: {len(batch_views)} views found")
        except Exception as e:
            _logger.error(f"Failed to refresh batch views: {e}")
            QMessageBox.warning(
                self,
                "Error Refreshing batch views",
                f"Failed to refresh batch views from the Batch Render Manager:\n{str(e)}",
            )

    def _populate_batch_views_list(self, batch_views):
        """
        Populate the batch items table widget with batch view data.

        Shows all batch views in a read-only table with columns for each field.
        """
        self.batch_views_table.setRowCount(0)  # Clear existing rows

        enabled_count = 0
        total_count = len(batch_views)

        for row, item in enumerate(batch_views):
            self.batch_views_table.insertRow(row)

            if item.enabled:
                enabled_count += 1

            # Column 0: Enabled (checkbox-style text)
            enabled_item = QTableWidgetItem("✓" if item.enabled else "")
            enabled_item.setTextAlignment(Qt.AlignCenter)
            self.batch_views_table.setItem(row, 0, enabled_item)

            # Column 1: Name
            name_item = QTableWidgetItem(item.name)
            name_item.setToolTip(item.name)
            self.batch_views_table.setItem(row, 1, name_item)

            # Column 2: Camera
            camera = item.camera or "Viewport"
            camera_item = QTableWidgetItem(camera)
            camera_item.setToolTip(camera)
            self.batch_views_table.setItem(row, 2, camera_item)

            # Column 3: Scene State
            scene_state = item.scene_state or ""
            scene_state_item = QTableWidgetItem(scene_state)
            scene_state_item.setToolTip(scene_state)
            self.batch_views_table.setItem(row, 3, scene_state_item)

            # Column 4: Preset file
            preset = item.preset_file or ""
            preset_item = QTableWidgetItem(preset)
            preset_item.setToolTip(preset)
            self.batch_views_table.setItem(row, 4, preset_item)

            # Column 5: Output Path
            output_path = item.output_filename or ""
            output_path_item = QTableWidgetItem(output_path)
            output_path_item.setToolTip(output_path)
            self.batch_views_table.setItem(row, 5, output_path_item)

            # Column 6: Override Preset (combined frame range, resolution, pixel aspect)
            override_parts = []
            if item.override_preset:
                if item.frame_start is not None and item.frame_end is not None:
                    override_parts.append(f"{item.frame_start}-{item.frame_end}")
                if item.width is not None and item.height is not None:
                    override_parts.append(f"{item.width}x{item.height}")
                if item.pixel_aspect is not None:
                    override_parts.append(str(item.pixel_aspect))
            override_text = " \u2013 ".join(override_parts)
            override_item = QTableWidgetItem(override_text)
            override_item.setToolTip("Frame Range \u2013 Resolution \u2013 Pixel Aspect")
            self.batch_views_table.setItem(row, 6, override_item)

            # Store full item data in first column for later retrieval
            enabled_item.setData(Qt.UserRole, item)

        # Update info label
        if total_count == 0:
            self.batch_views_info_label.setText("No batch views found")
        else:
            self.batch_views_info_label.setText(
                f"{enabled_count} of {total_count} batch views enabled"
            )

        # Resize rows to fit content after populating
        if total_count > 0:
            self.batch_views_table.resizeRowsToContents()
