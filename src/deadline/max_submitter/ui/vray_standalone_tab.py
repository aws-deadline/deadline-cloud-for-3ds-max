# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - V-Ray Standalone Tab UI
"""

import os

from data_const import (
    VRSCENE_EXPORT_ANIMATION_MODES,
    VRAY_ENGINE_CPU,
    VRAY_ENGINE_CUDA,
    VRAY_ENGINE_RTX,
)
from utilities.vrscene_utils import is_vray_renderer
from qtpy.QtCore import Qt  # type: ignore
from qtpy.QtWidgets import (  # type: ignore
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class VRayStandaloneSettingsWidget(QWidget):
    """V-Ray Standalone workflow settings tab."""

    def __init__(self, initial_settings, parent=None):
        super().__init__(parent=parent)

        self.developer_options = (
            os.environ.get("DEADLINE_ENABLE_DEVELOPER_OPTIONS", "").upper() == "TRUE"
        )

        self._build_ui(initial_settings)
        self._configure_settings(initial_settings)
        self._update_rollout_title()

    def _build_ui(self, settings):
        main_layout = QVBoxLayout(self)

        # Enable V-Ray Export checkbox at the top
        self.enable_vray_export_checkbox = QCheckBox("Enable V-Ray Standalone Export")
        self.enable_vray_export_checkbox.setToolTip(
            "When enabled, submits a V-Ray Standalone export and render job instead of a 3ds Max render job."
        )
        self.enable_vray_export_checkbox.setChecked(False)
        self.enable_vray_export_checkbox.stateChanged.connect(self._on_enable_changed)
        main_layout.addWidget(self.enable_vray_export_checkbox)

        # Submit To V-Ray Standalone Group
        self.vray_export_group = QGroupBox("Submit To V-Ray Standalone")
        vray_export_layout = QVBoxLayout()
        self.vray_export_group.setLayout(vray_export_layout)
        self.vray_export_group.setEnabled(False)  # Disabled by default

        # Export mode radio buttons
        self.radio_local_export = QRadioButton("Export VRSCENE On This Workstation")
        self.radio_local_export.setToolTip(
            "Exporting on the Workstation can block it for a while, but has no 3ds Max startup overhead.\n\n"
            "Exporting On Deadline offsets the processing time to the network, but requires a Worker running Windows and 3ds Max."
        )
        self.radio_farm_export = QRadioButton("Export VRSCENE On Deadline")
        self.radio_farm_export.setToolTip(
            "Exporting on the Workstation can block it for a while, but has no 3ds Max startup overhead.\n\n"
            "Exporting On Deadline offsets the processing time to the network, but requires a Worker running Windows and 3ds Max."
        )

        vray_export_layout.addWidget(self.radio_local_export)
        vray_export_layout.addWidget(self.radio_farm_export)

        # Export Animation dropdown
        export_anim_layout = QHBoxLayout()
        export_anim_label = QLabel("Export Animation:")
        self.export_animation_combo = QComboBox()
        for mode_label, mode_value in VRSCENE_EXPORT_ANIMATION_MODES:
            self.export_animation_combo.addItem(mode_label, mode_value)
        self.export_animation_combo.setToolTip(
            "'Single File' will create one VRSCENE file for the entire animation sequence.\n\n"
            "'File Per Frame' will create one VRSCENE file for each frame in the animation. "
            "Each VRSCENE file will be self-contained. This usually produces larger files, but is better suited "
            "for parallel rendering since rendering each frame depends on exactly one VRSCENE file.\n\n"
            "'File Per Frame (Incremental)' will produce an initial VRSCENE for the first frame which contains "
            "all of the initial geometry, materials, and renderer settings. VRSCENE files created for subsequent "
            "frames will reference the first frame and only specify differential changes for the frame. "
            "This often reduces the size of the VRSCENE files but the rendering of all frames will depend on "
            "the first VRSCENE file. When the scene is heavily animated with geometry modifiers this export mode "
            "degrades and 'Files Per Frame' is preferrable."
        )
        export_anim_layout.addWidget(export_anim_label)
        export_anim_layout.addWidget(self.export_animation_combo)
        export_anim_layout.addStretch()
        vray_export_layout.addLayout(export_anim_layout)

        main_layout.addWidget(self.vray_export_group)

        # Job Options Group
        self.job_options_group = QGroupBox("Job Options")
        job_options_layout = QGridLayout()
        self.job_options_group.setLayout(job_options_layout)
        self.job_options_group.setEnabled(False)  # Disabled by default

        row = 0

        # Job Name
        job_options_layout.addWidget(QLabel("Job Name:"), row, 0)
        self.job_name_edit = QLineEdit()
        job_options_layout.addWidget(self.job_name_edit, row, 1, 1, 3)
        row += 1

        # Comment
        job_options_layout.addWidget(QLabel("Comment:"), row, 0)
        self.comment_edit = QLineEdit()
        job_options_layout.addWidget(self.comment_edit, row, 1, 1, 3)
        row += 1

        # Priority
        job_options_layout.addWidget(QLabel("Priority:"), row, 0)
        self.priority_spin = QSpinBox()
        self.priority_spin.setMinimum(0)
        self.priority_spin.setMaximum(100)
        self.priority_spin.setValue(50)
        job_options_layout.addWidget(self.priority_spin, row, 1)
        row += 1

        # Frame List
        job_options_layout.addWidget(QLabel("Frame List:"), row, 0)
        self.frame_list_edit = QLineEdit()
        self.frame_list_edit.setToolTip("Frame range to render (e.g., 1-100 or 1,5,10-20)")
        job_options_layout.addWidget(self.frame_list_edit, row, 1, 1, 3)
        row += 1

        # Output Path
        job_options_layout.addWidget(QLabel("Output Path:"), row, 0)
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setToolTip(
            "Directory where vrscene files and rendered images will be saved"
        )
        job_options_layout.addWidget(self.output_path_edit, row, 1, 1, 2)

        # Browse button for output path
        self.output_path_browse_btn = QPushButton("Browse...")
        self.output_path_browse_btn.clicked.connect(self._browse_output_path)
        job_options_layout.addWidget(self.output_path_browse_btn, row, 3)
        row += 1

        main_layout.addWidget(self.job_options_group)

        # Region Rendering Group
        self.region_group = QGroupBox("Region Rendering")
        region_layout = QGridLayout()
        self.region_group.setLayout(region_layout)
        self.region_group.setEnabled(False)  # Disabled by default

        region_layout.addWidget(QLabel("Columns:"), 0, 0)
        self.region_columns_spin = QSpinBox()
        self.region_columns_spin.setMinimum(1)
        self.region_columns_spin.setMaximum(10)
        self.region_columns_spin.setValue(2)
        self.region_columns_spin.setToolTip("Number of columns to divide the image into")
        region_layout.addWidget(self.region_columns_spin, 0, 1)

        region_layout.addWidget(QLabel("Rows:"), 0, 2)
        self.region_rows_spin = QSpinBox()
        self.region_rows_spin.setMinimum(1)
        self.region_rows_spin.setMaximum(10)
        self.region_rows_spin.setValue(2)
        self.region_rows_spin.setToolTip("Number of rows to divide the image into")
        region_layout.addWidget(self.region_rows_spin, 0, 3)

        # Render Engine dropdown
        region_layout.addWidget(QLabel("Render Engine:"), 1, 0)
        self.render_engine_combo = QComboBox()
        self.render_engine_combo.addItem("CPU", VRAY_ENGINE_CPU)
        self.render_engine_combo.addItem("CUDA (NVIDIA GPU)", VRAY_ENGINE_CUDA)
        self.render_engine_combo.addItem("RTX (NVIDIA RTX GPU)", VRAY_ENGINE_RTX)
        self.render_engine_combo.setToolTip(
            "CPU: Standard V-Ray CPU rendering.\n"
            "CUDA: GPU rendering on all NVIDIA GPUs.\n"
            "RTX: GPU rendering on NVIDIA RTX GPUs only (fastest for supported scenes)."
        )
        region_layout.addWidget(self.render_engine_combo, 1, 1, 1, 3)
        self.render_engine_combo.currentIndexChanged.connect(self._on_render_engine_changed)

        # RT Engine settings (GPU only) — control when the progressive renderer stops.
        # Only visible when CUDA or RTX engine is selected.
        # Timeout: max render time in minutes (0=no limit)
        # Noise: stop when image noise drops below threshold (lower = higher quality, longer render)
        # Samples: max samples per pixel (0=no limit, noise threshold controls stopping)
        self._rt_timeout_label = QLabel("Frame Timeout (min):")
        self._rt_timeout_label.setVisible(False)
        region_layout.addWidget(self._rt_timeout_label, 2, 0)
        self.rt_timeout_spin = QDoubleSpinBox()
        self.rt_timeout_spin.setMinimum(0.0)
        self.rt_timeout_spin.setMaximum(9999.0)
        self.rt_timeout_spin.setValue(0.0)
        self.rt_timeout_spin.setDecimals(2)
        self.rt_timeout_spin.setToolTip("Maximum render time in minutes. 0 = no limit.")
        self.rt_timeout_spin.setVisible(False)
        region_layout.addWidget(self.rt_timeout_spin, 2, 1)

        self._rt_noise_label = QLabel("Noise Threshold:")
        self._rt_noise_label.setVisible(False)
        region_layout.addWidget(self._rt_noise_label, 2, 2)
        self.rt_noise_spin = QDoubleSpinBox()
        self.rt_noise_spin.setMinimum(0.0)
        self.rt_noise_spin.setMaximum(1.0)
        self.rt_noise_spin.setValue(0.001)
        self.rt_noise_spin.setDecimals(4)
        self.rt_noise_spin.setSingleStep(0.0001)  # Fine-grained control for noise threshold
        self.rt_noise_spin.setToolTip("Stop rendering when noise drops below this threshold.")
        self.rt_noise_spin.setVisible(False)
        region_layout.addWidget(self.rt_noise_spin, 2, 3)

        self._rt_sample_label = QLabel("Max Samples:")
        self._rt_sample_label.setVisible(False)
        region_layout.addWidget(self._rt_sample_label, 3, 0)
        self.rt_sample_spin = QSpinBox()
        self.rt_sample_spin.setMinimum(0)
        self.rt_sample_spin.setMaximum(999999)
        self.rt_sample_spin.setValue(0)
        self.rt_sample_spin.setToolTip("Maximum number of samples per pixel. 0 = no limit.")
        self.rt_sample_spin.setVisible(False)
        region_layout.addWidget(self.rt_sample_spin, 3, 1)

        # Movie creation (deferred to future release)
        self.create_movie_check = QCheckBox("Create Movie from Frames")
        self.create_movie_check.setToolTip("Coming in a future release")
        self.create_movie_check.setVisible(False)
        self.create_movie_check.stateChanged.connect(self._on_create_movie_changed)
        region_layout.addWidget(self.create_movie_check, 1, 0, 1, 4)

        self._movie_filename_label = QLabel("  Movie Filename:")
        self._movie_filename_label.setVisible(False)
        region_layout.addWidget(self._movie_filename_label, 2, 0)
        self.movie_filename_edit = QLineEdit()
        self.movie_filename_edit.setText("output.mp4")
        self.movie_filename_edit.setVisible(False)
        region_layout.addWidget(self.movie_filename_edit, 2, 1, 1, 3)

        self._movie_framerate_label = QLabel("  Frame Rate:")
        self._movie_framerate_label.setVisible(False)
        region_layout.addWidget(self._movie_framerate_label, 3, 0)
        self.movie_framerate_spin = QSpinBox()
        self.movie_framerate_spin.setMinimum(1)
        self.movie_framerate_spin.setMaximum(120)
        self.movie_framerate_spin.setValue(24)
        self.movie_framerate_spin.setVisible(False)
        region_layout.addWidget(self.movie_framerate_spin, 3, 1)

        # Output format
        region_layout.addWidget(QLabel("Output Format:"), 4, 0)
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItem("Auto-detect", "auto")
        self.output_format_combo.addItem("PNG", "png")
        self.output_format_combo.addItem("EXR", "exr")
        self.output_format_combo.addItem("TIFF", "tiff")
        self.output_format_combo.addItem("JPG", "jpg")
        self.output_format_combo.setToolTip(
            "Output image format for rendered frames. Auto-detect uses the format from 3ds Max render settings."
        )
        region_layout.addWidget(self.output_format_combo, 4, 1, 1, 3)

        # Output filename override
        region_layout.addWidget(QLabel("Output Filename:"), 5, 0)
        self.output_filename_edit = QLineEdit()
        self.output_filename_edit.setPlaceholderText("Leave empty to use scene name")
        self.output_filename_edit.setToolTip(
            "Override the output filename (without extension). Leave empty to use the scene name."
        )
        region_layout.addWidget(self.output_filename_edit, 5, 1, 1, 3)

        main_layout.addWidget(self.region_group)

        # Developer options
        if self.developer_options:
            self.include_adaptor_wheels = QCheckBox(
                "Developer Option: Include Adaptor Wheels", self
            )
            main_layout.addWidget(self.include_adaptor_wheels)

        # Spacer
        main_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Check if V-Ray is available
        if not is_vray_renderer():
            self.setEnabled(False)
            status_label = QLabel(
                "V-Ray Standalone workflow is only available when V-Ray is the active renderer"
            )
            status_label.setStyleSheet("QLabel { color: #cc6600; font-style: italic; }")
            main_layout.addWidget(status_label)

        # Connect signals
        self.radio_local_export.toggled.connect(self._update_rollout_title)
        self.radio_farm_export.toggled.connect(self._update_rollout_title)

    def _on_render_engine_changed(self, index):
        """Show/hide RT settings based on selected engine."""
        is_gpu = self.render_engine_combo.currentData() != 0
        self._rt_timeout_label.setVisible(is_gpu)
        self.rt_timeout_spin.setVisible(is_gpu)
        self._rt_noise_label.setVisible(is_gpu)
        self.rt_noise_spin.setVisible(is_gpu)
        self._rt_sample_label.setVisible(is_gpu)
        self.rt_sample_spin.setVisible(is_gpu)

    def _on_enable_changed(self, state):
        enabled = state == 2
        self.vray_export_group.setEnabled(enabled)
        self.job_options_group.setEnabled(enabled)
        self.region_group.setEnabled(enabled)

    def is_vray_export_enabled(self):
        return self.enable_vray_export_checkbox.isChecked()

    def _configure_settings(self, settings):
        # Set export mode
        if settings.export_mode == 1:
            self.radio_local_export.setChecked(True)
        else:
            self.radio_farm_export.setChecked(True)

        # Set export animation mode
        index = self.export_animation_combo.findData(settings.export_animation_mode)
        if index >= 0:
            self.export_animation_combo.setCurrentIndex(index)

        # Set job options
        self.job_name_edit.setText(settings.name)
        self.comment_edit.setText(settings.description)
        self.priority_spin.setValue(settings.priority)
        self.frame_list_edit.setText(settings.frame_list)
        self.output_path_edit.setText(settings.output_path)

        # Set region settings
        self.region_columns_spin.setValue(settings.vrscene_render_region_columns)
        self.region_rows_spin.setValue(settings.vrscene_render_region_rows)

        # Set render engine
        index = self.render_engine_combo.findData(settings.vrscene_render_engine)
        if index >= 0:
            self.render_engine_combo.setCurrentIndex(index)
        self._on_render_engine_changed(index)

        # Set RT settings
        self.rt_timeout_spin.setValue(settings.vrscene_rt_timeout)
        self.rt_noise_spin.setValue(settings.vrscene_rt_noise)
        self.rt_sample_spin.setValue(settings.vrscene_rt_sample_level)

        # Set movie settings
        self.create_movie_check.setChecked(settings.vrscene_create_movie)
        self.movie_filename_edit.setText(settings.vrscene_movie_filename)
        self.movie_framerate_spin.setValue(settings.vrscene_movie_framerate)

        # Set output settings
        index = self.output_format_combo.findData(settings.output_format)
        if index >= 0:
            self.output_format_combo.setCurrentIndex(index)
        self.output_filename_edit.setText(settings.output_filename_override)

        if self.developer_options:
            self.include_adaptor_wheels.setChecked(settings.include_adaptor_wheels)

    def _update_rollout_title(self):
        title = "Submit To V-Ray Standalone"
        if not self.vray_export_group.isChecked():
            if self.radio_local_export.isChecked():
                title += " [Local Export]"
            else:
                title += " [On Deadline]"
        self.vray_export_group.setTitle(title)

    def _on_create_movie_changed(self, state):
        enabled = state == Qt.Checked
        self.movie_filename_edit.setEnabled(enabled)
        self.movie_framerate_spin.setEnabled(enabled)

    def _browse_output_path(self):
        """Open a directory browser for output path."""
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

    def update_settings(self, settings=None):
        """Update settings object from current UI values."""
        # Create new settings if not provided
        if settings is None:
            from vrscene_settings import VRSceneRenderSubmitterUISettings

            settings = VRSceneRenderSubmitterUISettings()

        # Export settings
        settings.export_mode = 1 if self.radio_local_export.isChecked() else 2
        settings.export_animation_mode = self.export_animation_combo.currentData()

        # Job options
        settings.name = self.job_name_edit.text()
        settings.description = self.comment_edit.text()
        settings.priority = self.priority_spin.value()
        settings.frame_list = self.frame_list_edit.text()
        settings.output_path = self.output_path_edit.text()

        # Region settings
        settings.vrscene_render_region_columns = self.region_columns_spin.value()
        settings.vrscene_render_region_rows = self.region_rows_spin.value()
        settings.vrscene_render_engine = self.render_engine_combo.currentData()
        settings.vrscene_rt_timeout = self.rt_timeout_spin.value()
        settings.vrscene_rt_noise = self.rt_noise_spin.value()
        settings.vrscene_rt_sample_level = self.rt_sample_spin.value()

        # Movie settings
        settings.vrscene_create_movie = self.create_movie_check.isChecked()
        settings.vrscene_movie_filename = self.movie_filename_edit.text()
        settings.vrscene_movie_framerate = self.movie_framerate_spin.value()

        # Output settings
        settings.output_format = self.output_format_combo.currentData()
        settings.output_filename_override = self.output_filename_edit.text()

        if self.developer_options:
            settings.include_adaptor_wheels = self.include_adaptor_wheels.isChecked()
        else:
            settings.include_adaptor_wheels = False

        return settings
