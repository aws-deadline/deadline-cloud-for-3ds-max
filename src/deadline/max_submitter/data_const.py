# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Constants for populating and querying the UI
"""

# Strings for populating and checking data from UI fields
ALL_CAMERAS_STR = "All Cameras"
ALL_STEREO_CAMERAS_STR = "All Stereo Cameras"
ALL_STATE_SETS_STR = "All State Sets"

# Standard group label for job parameters
UI_GROUP_LABEL = "3dsMax Settings"

# Sticky settings filename
RENDER_SUBMITTER_SETTINGS_FILE_EXT = ".deadline_render_settings.json"

# Filename for backup created at submission
TEMP_BACKUP_FILENAME = "max_backup_file.mx"

# Renderers currently supported by Deadline Cloud
# Add new renderers to the README when adding to here
ALLOWED_RENDERERS = [
    "Default_Scanline_Renderer",
    "ART_Renderer",
    "Corona",
    "V_Ray_6",
    "V_Ray_GPU_6",
    "V_Ray_7",
    "V_Ray_GPU_7",
    "Redshift_Renderer",
]

# Possible output extensions
ALLOWED_EXTENSIONS = [
    ["AVI File (*.avi)", ".avi"],
    ["BMP Image File (*.bmp)", ".bmp"],
    ["Kodak Cineon (*.cin)", ".cin"],
    ["Encapsulated PostScript File (*.eps)", ".eps"],
    ["OpenEXR Image File (*.exr)", ".exr"],
    ["Radiance Image File (HDRI) (*.hdr)", ".hdr"],
    ["JPEG File (*.jpg)", ".jpg"],
    ["PNG Image File (*.png)", ".png"],
    ["RLA Image File (*.rla)", ".rla"],
    ["RPF Image File (*.rpf)", ".rpf"],
    ["Targa Image File (*.tga)", ".tga"],
    ["TIF Image File (*.tif)", ".tif"],
    ["DDS Image File (*.dds)", ".dds"],
    ["Corona EXR Image Format (*.cxr)", ".cxr"],
    ["V-Ray Image Format (*.vrimg)", ".vrimg"],
]

# Render Elements Preset Configurations
# Each preset defines the render element settings values
RENDER_ELEMENTS_PRESETS: dict[str, dict[str, bool]] = {
    "Default": {
        "enabled_modify_render_elements": False,
        "render_elements": True,
        "render_elements_update_paths": True,
        "render_elements_include_name_in_path": True,
        "render_elements_include_type_in_path": False,
        "render_elements_include_name_in_filename": True,
        "render_elements_include_type_in_filename": False,
        "vray_render_elements_vfb_control": True,
        "vray_split_buffer_support": True,
    },
    "VRay with 3dsMax Render Buffer": {
        # Uses 3ds Max framebuffer (disables V-Ray VFB)
        # Split buffer enabled for render element output
        "enabled_modify_render_elements": True,
        "render_elements": True,
        "render_elements_update_paths": True,
        "render_elements_include_name_in_path": True,
        "render_elements_include_type_in_path": False,
        "render_elements_include_name_in_filename": True,
        "render_elements_include_type_in_filename": False,
        "vray_render_elements_vfb_control": True,  # Disables V-Ray VFB (output_on = False)
        "vray_split_buffer_support": True,  # Enables split buffer for render elements
    },
    "VRay Render Buffer": {
        # Uses V-Ray VFB (frame buffer) for output
        # Split buffer enabled for render elements to save to individual files
        "enabled_modify_render_elements": True,
        "render_elements": True,
        "render_elements_update_paths": True,
        "render_elements_include_name_in_path": True,
        "render_elements_include_type_in_path": False,
        "render_elements_include_name_in_filename": True,
        "render_elements_include_type_in_filename": False,
        "vray_render_elements_vfb_control": False,  # Keeps V-Ray VFB enabled (output_on = True)
        "vray_split_buffer_support": True,  # Enables split buffer for render elements
    },
}

# Materials allowed for custom override on submit
SCENE_TWEAKS_MATS = [
    "Standard Grayscale Material",
    "Object Wireframe Color",
    "Layer Color",
    "Material Editor Slot 1",
]

# All options for stereo camera submissions
STEREO_CAMERA_OPTIONS = [
    ["Left Eye Only", "Left"],
    ["Right Eye Only", "Right"],
    ["Center Only", "Center"],
    ["Left and Right Eye", "Left_Right"],
    ["Left, Right and Center", "All"],
    ["Disable Stereo Camera Submission", "None"],
]

# V-Ray Standalone Workflow Constants
VRSCENE_EXPORT_MODES = [
    ["Export VRSCENE On This Workstation", 1],
    ["Export VRSCENE On Deadline", 2],
]

VRSCENE_EXPORT_ANIMATION_MODES = [
    ["Single File", 1],
    ["File Per Frame", 2],
    ["File Per Frame (Incremental)", 3],
]

VRSCENE_SUBMITTER_SETTINGS_FILE_EXT = ".deadline_vrscene_settings.json"
