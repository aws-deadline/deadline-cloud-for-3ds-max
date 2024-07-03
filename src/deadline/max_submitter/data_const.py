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
ALLOWED_RENDERERS = ["Default_Scanline_Renderer", "ART_Renderer", "Corona"]

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
    ["Corona EXR Image Format (*.cxr)",".cxr"]
]

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
