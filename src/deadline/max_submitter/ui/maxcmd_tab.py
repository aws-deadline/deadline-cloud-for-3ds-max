# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - 3dsmaxcmd Command-Line Render Tab UI
"""

from qtpy.QtWidgets import (  # type: ignore
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class MaxCmdSettingsWidget(QWidget):
    """3dsmaxcmd command-line render workflow settings tab.

    When enabled, the submitter builds a bundle that renders the scene with
    3dsmaxcmd.exe (the render server) instead of the standard 3dsmaxbatch
    adaptor. This is what lets network-licensed plugins such as Pencil+ (NTR)
    render without a watermark.
    """

    def __init__(self, initial_settings, parent=None):
        super().__init__(parent=parent)
        self._build_ui()
        self._configure_settings(initial_settings)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # Enable checkbox at the top
        self.enable_maxcmd_checkbox = QCheckBox("Enable 3dsmaxcmd Command-Line Render")
        self.enable_maxcmd_checkbox.setToolTip(
            "When enabled, submits a job that renders with 3dsmaxcmd.exe (the 3ds Max "
            "render server) instead of the standard adaptor. Required for network-licensed "
            "plugins such as Pencil+ (NTR) to render without a watermark.\n\n"
            "Note: V-Ray VFB raw output (raw/split-channel files) is NOT redirected by this "
            "workflow. For V-Ray, use the standard Output Filename field or the adaptor "
            "workflow, otherwise that output is written outside the captured job output."
        )
        self.enable_maxcmd_checkbox.setChecked(False)
        self.enable_maxcmd_checkbox.stateChanged.connect(self._on_enable_changed)
        main_layout.addWidget(self.enable_maxcmd_checkbox)

        # Job Options group
        self.job_options_group = QGroupBox("3dsmaxcmd Render Options")
        job_layout = QGridLayout()
        self.job_options_group.setLayout(job_layout)
        self.job_options_group.setEnabled(False)

        # Job Name, Comment and Priority are intentionally omitted here. They are
        # owned by the base dialog's "Shared job settings" tab and applied to the
        # job at submit time, so duplicating them here would be redundant.
        row = 0
        job_layout.addWidget(QLabel("Frame List:"), row, 0)
        self.frame_list_edit = QLineEdit()
        self.frame_list_edit.setToolTip("Frame range to render (e.g., 1-100 or 1,5,10-20)")
        job_layout.addWidget(self.frame_list_edit, row, 1, 1, 3)
        row += 1

        job_layout.addWidget(QLabel("Output Path:"), row, 0)
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setToolTip(
            "Directory where rendered images are saved. Required — the render output must "
            "go to a captured location, not the scene's baked local output path."
        )
        job_layout.addWidget(self.output_path_edit, row, 1, 1, 2)
        self.output_path_browse_btn = QPushButton("Browse...")
        self.output_path_browse_btn.clicked.connect(self._browse_output_path)
        job_layout.addWidget(self.output_path_browse_btn, row, 3)
        row += 1

        job_layout.addWidget(QLabel("Output Filename:"), row, 0)
        self.output_filename_edit = QLineEdit()
        self.output_filename_edit.setPlaceholderText("e.g. render.exr (blank uses scene output)")
        self.output_filename_edit.setToolTip(
            "Output file name with extension. Leave blank to use the scene's Render Setup output."
        )
        job_layout.addWidget(self.output_filename_edit, row, 1, 1, 3)
        row += 1

        job_layout.addWidget(QLabel("Camera:"), row, 0)
        self.camera_edit = QLineEdit()
        self.camera_edit.setPlaceholderText("Blank uses the scene's active view")
        self.camera_edit.setToolTip("Named camera to render. Leave blank to use the active view.")
        job_layout.addWidget(self.camera_edit, row, 1, 1, 3)
        row += 1

        job_layout.addWidget(QLabel("3dsmaxcmd Executable:"), row, 0)
        self.maxcmd_executable_edit = QLineEdit()
        self.maxcmd_executable_edit.setToolTip(
            "Path to 3dsmaxcmd.exe on the worker. Defaults to '3dsmaxcmd' (resolved on PATH)."
        )
        job_layout.addWidget(self.maxcmd_executable_edit, row, 1, 1, 3)
        row += 1

        # Task run timeout row (mirrors the standard scene-settings tab)
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
        job_layout.addWidget(timeout_row_widget, row, 0, 1, 4)
        row += 1

        self.task_timeout_chck.toggled.connect(self.task_timeout_spinbox.setEnabled)

        main_layout.addWidget(self.job_options_group)
        main_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _on_enable_changed(self, state):
        self.job_options_group.setEnabled(self.enable_maxcmd_checkbox.isChecked())

    def is_maxcmd_enabled(self):
        return self.enable_maxcmd_checkbox.isChecked()

    def _browse_output_path(self):
        from qtpy.QtWidgets import QFileDialog

        current_path = self.output_path_edit.text()
        if not current_path:
            from pymxs import runtime as rt

            current_path = rt.maxFilePath

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if directory:
            self.output_path_edit.setText(directory)

    def _configure_settings(self, settings):
        self.frame_list_edit.setText(settings.frame_list)
        self.output_path_edit.setText(settings.output_path)
        self.output_filename_edit.setText(settings.output_filename)
        self.camera_edit.setText(settings.camera)
        self.maxcmd_executable_edit.setText(settings.maxcmd_executable)

        timeout_enabled = settings.task_run_timeout_seconds > 0
        self.task_timeout_chck.setChecked(timeout_enabled)
        self.task_timeout_spinbox.setValue(
            settings.task_run_timeout_seconds if timeout_enabled else 3600
        )
        self.task_timeout_spinbox.setEnabled(timeout_enabled)

    def update_settings(self, settings=None):
        """Update settings object from current UI values."""
        if settings is None:
            from maxcmd_settings import MaxCmdSubmitterUISettings

            settings = MaxCmdSubmitterUISettings()

        settings.frame_list = self.frame_list_edit.text()
        settings.output_path = self.output_path_edit.text()
        settings.output_filename = self.output_filename_edit.text()
        settings.camera = self.camera_edit.text()
        settings.maxcmd_executable = self.maxcmd_executable_edit.text() or "3dsmaxcmd"

        if self.task_timeout_chck.isChecked():
            settings.task_run_timeout_seconds = self.task_timeout_spinbox.value()
        else:
            settings.task_run_timeout_seconds = 0
        return settings
