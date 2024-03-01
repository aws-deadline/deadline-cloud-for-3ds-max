"""
3ds Max Deadline Cloud Submitter - UI widgets for the Scene Settings tab.

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os
import logging

import pymxs  # noqa
from pymxs import runtime as rt

from PySide2.QtGui import QRegularExpressionValidator
from PySide2.QtCore import QSize, Qt, QRegularExpression  # type: ignore
from PySide2.QtWidgets import (  # type: ignore
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
    QGroupBox,
    QMessageBox,
    QApplication,
)

from deadline.client.ui import block_signals

from utilities import max_utils
from data_const import (
    ALLOWED_RENDERERS,
    ALLOWED_EXTENSIONS,
    SCENE_TWEAKS_MATS,
    STEREO_CAMERA_OPTIONS,
    ALL_STATE_SETS_STR,
)

_logger = logging.getLogger(__name__)


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
        lyt.setMargin(0)

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

        # Project path
        self.proj_path_txt = QLineEdit(self)
        self.proj_path_txt.setEnabled(False)
        lyt.addWidget(QLabel("Project Path"), 0, 0)
        lyt.addWidget(self.proj_path_txt, 0, 1)

        # Output path
        self.output_path_txt = FileSearchLineEdit(directory_only=True)
        lyt.addWidget(QLabel("Output Path"), 1, 0)
        lyt.addWidget(self.output_path_txt, 1, 1)

        # Output filename
        self.output_name_txt = QLineEdit(self)
        lyt.addWidget(QLabel("Output Filename"), 2, 0)
        lyt.addWidget(self.output_name_txt, 2, 1)

        # Output extension
        self.output_ext_box = QComboBox(self)
        for ext in ALLOWED_EXTENSIONS:
            self.output_ext_box.addItem(ext[0], ext[1])
        lyt.addWidget(QLabel("Output File Extension"), 3, 0)
        lyt.addWidget(self.output_ext_box, 3, 1)

        # State Set selection
        self.state_sets_box = QComboBox(self)
        self.state_sets_box.addItem("All State Sets", "All State Sets")
        self.state_sets_box.setToolTip(
            "Updating this selection also updates the active state set of your scene."
        )
        for state_set in self.state_sets:
            self.state_sets_box.addItem(state_set[0], state_set[1])
        lyt.addWidget(QLabel("State Sets"), 4, 0)
        lyt.addWidget(self.state_sets_box, 4, 1)
        (self.state_sets_box.currentIndexChanged.connect(self._update_state_set))

        # Renderer
        self.renderers_box = QComboBox(self)
        self.renderers_box.setEnabled(False)
        self.renderers_box.setToolTip(
            "Needs to be set in Render Settings! \n"
            "If you are using State Sets, be sure to record any changes in the State Set."
        )
        self.renderers_box.addItem("Current Renderer not supported by Submitter")
        for renderer in self.renderers:
            if renderer in ALLOWED_RENDERERS:
                self.renderers_box.addItem(renderer.replace("_", " "), renderer)
        lyt.addWidget(QLabel("Renderer"), 5, 0)
        lyt.addWidget(self.renderers_box, 5, 1)

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
        lyt.addWidget(QLabel("Stereo Cameras Selection"), 6, 0)
        lyt.addWidget(self.stereo_cameras_box, 6, 1)
        self.stereo_cameras_box.currentIndexChanged.connect(self._fill_cameras_box)

        # Cameras to render selection
        self.cameras_box = QComboBox(self)
        lyt.addWidget(QLabel("Cameras To Render"), 7, 0)
        lyt.addWidget(self.cameras_box, 7, 1)

        # Override frame range
        self.frame_override_chck = QCheckBox("Override Frame Range", self)
        self.frame_override_txt = QLineEdit(self)
        self.frame_override_txt.setToolTip(
            "Frame range you want to use as override. \n" "E.g. 1,3,5-10 or 1, 3, 5-10"
        )
        self.style_sheet = self.frame_override_txt.styleSheet()
        lyt.addWidget(self.frame_override_chck, 8, 0)
        lyt.addWidget(self.frame_override_txt, 8, 1)
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
        lyt.addWidget(self.scene_tweaks_grp_box, 9, 0, 3, 5)

        if self.developer_options:
            self.include_adaptor_wheels = QCheckBox(
                "Developer Option: Include Adaptor Wheels", self
            )
            lyt.addWidget(self.include_adaptor_wheels, 12, 0)

        lyt.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), 13, 0)

        self._fill_cameras_box(0)

    def _build_scene_tweaks_ui(self):
        """
        Create a QGroupBox for the scene tweaks
        """
        # Create groupbox
        self.scene_tweaks_grp_box = QGroupBox()
        self.scene_tweaks_grp_box.setTitle("Scene Tweaks")
        scene_tweaks_lyt = QGridLayout(self)
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
        Checks for valid frame range in frame_override_txt QLineEdit.

        :param old_widget: widget that lost focus
        :type old_widget: any QWidget
        :param new_widget: widget that gained focus
        :type new_widget: any QWidget
        """
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
        self.output_name_txt.setText(settings.output_name)
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

    def update_settings(self, settings):
        """
        Update a scene settings object with the latest values.
        """
        settings.project_path = self.proj_path_txt.text()
        settings.output_path = self.output_path_txt.text()
        settings.output_name = self.output_name_txt.text()
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

    def activate_frame_override_changed(self, state):
        """
        Set the activated/deactivated status of the Frame override text box
        """
        self.frame_override_txt.setEnabled(state == Qt.Checked)

    def activate_custom_material_changed(self, state):
        """
        Set the activated/deactivated status of the Custom material combo box
        """
        self.custom_mat_box.setEnabled(state == Qt.Checked)

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
