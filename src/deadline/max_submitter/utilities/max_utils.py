# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - Deadline Cloud 3ds Max utilities
"""

import logging
import os
from pathlib import Path

import pymxs  # separate import to initialize
from pymxs import runtime as rt

_logger = logging.getLogger(__name__)


def get_referenced_files() -> list:
    """
    Finds all referenced files (bitmap textures, xrefs).

    :returns: list with paths to all referenced files
    :return_type: list
    """
    # Refresh Asset Tracking to make sure we have the latest version
    rt.ATSOps.Refresh()

    # Convert result from usedMaps MAXScript function into a python list
    maps = rt.ATSOps.GetFiles(pymxs.byref(None))
    # Note: ATSOps returns list[int, [file paths]]
    maps_in_scene = [str(x.replace("\\", "/")) for x in list(maps)[1]]

    # Check for nested files to make sure the path correctly gets converted when it's relative
    nested_files: list[list] = []
    for i, map_ in enumerate(maps_in_scene):
        if os.path.normpath(map_) == get_scene_path():
            continue
        nested = rt.ATSOps.GetDependentFiles(map_, False, pymxs.byref(None))[1]
        if not nested:
            continue
        for item in nested:
            index = maps_in_scene.index(item.replace("\\", "/"))
            # Pass along the nested file, the index of that nested file and the index of the parent
            # in maps_in_scene
            nested_files += [[item, index, i]]

    # Update the path in the maps_in_scene
    for file in nested_files:
        relative_dir = os.path.split(maps_in_scene[file[2]])[0]
        maps_in_scene[file[1]] = os.path.join(relative_dir, file[0])

    return maps_in_scene


def get_renderers() -> list:
    """
    Finds all existing renderers.

    :returns: list containing all usable renderers from 3ds Max
    :return_type: list
    """
    # Convert result from rendererClass.classes MAXScript into a python list
    renderers = [str(x) for x in list(rt.rendererClass.classes)]
    # Remove unusable renderers from list
    # A360 Cloud rendering is only selectable in Target, not in Renderer itself
    try:
        renderers.remove("A360_Cloud_Rendering")
    except ValueError:
        pass
    try:
        renderers.remove("Missing_Renderer")
    except ValueError:
        pass
    return renderers


def get_scene_path() -> str:
    """
    Get the full path of the current 3ds Max scene.
    Returned path replaces all \\ with /.

    :returns: current scene path
    :return_type: str
    """
    return (rt.maxFilePath + rt.maxFileName).replace("\\", "/")


def get_scene_name() -> str:
    """
    Get filename of current 3ds Max instance and remove extensions.

    :returns: current scene name without extension
    :return_type: str
    """
    return Path(rt.maxFileName).stem


def get_scene_dir() -> str:
    """
    Get file directory of current 3ds Max instance.
    Returned path replaces all \\ with /.

    :returns: current scene directory
    :return_type: str
    """
    max_dir = rt.maxFilePath
    return max_dir.replace("\\", "/")


def get_frames() -> str:
    """
    Gets the scenes current framelist for rendering from the render settings.

    :return: returns a frame range in string format.
            Possible return values:
                - a single frame: e.g. '5'
                - a frame range: e.g. '1-10'
                - multiple frames and/or ranges in one string: e.g. '1,3,5-12'
    """
    if rt.rendTimeType == 1:  # Single frame
        current_frame = int(rt.sliderTime)
        return str(current_frame)
    if rt.rendTimeType == 2:  # Active time segment
        start_frame = int(rt.animationrange.start)
        end_frame = int(rt.animationrange.end)
        return f"{start_frame}-{end_frame}"
    if rt.rendTimeType == 3:  # User chosen range
        start_frame = int(rt.rendStart)
        end_frame = int(rt.rendEnd)
        return f"{start_frame}-{end_frame}"
    if rt.rendTimeType == 4:  # Pick up frames
        return rt.rendPickupFrames

    raise ValueError(f"Unknown render time type: {rt.rendTimeType}")


def is_correct_frame_range(frames: str) -> bool:
    """
    Check if first number in range is smaller than the second.
    Input from text field can only have numbers, commas or dashes due to regex validator on field.

    :param frames: frame range you want to check
    :type frames: str
    :returns: boolean that indicates whether the frame range was valid
    :return_type: bool
    """
    frames_input = frames.strip()
    override_frames = frames_input.split(",")
    # only need to check for ranges, not single frames
    frame_ranges = [pair for pair in override_frames if "-" in pair]
    for range_ in frame_ranges:
        numbers = range_.split("-")
        if int(numbers[1]) <= int(numbers[0]):
            return False
    return True


def get_duplicate_frames(frames: str) -> str:
    """
    Gets all repeating numbers in the given frame range.
    Input from text field can only have numbers, commas or dashes due to regex validator on field.

    :param frames: frame range you want to check
    :type frames: str
    :returns: a list in string format containing the duplicate numbers
    :return_type: str
    """
    # remove any spaces and split into groups
    frames_input = frames.strip()
    override_frames = frames_input.split(",")
    frames_to_render: list[int] = []
    duplicates: list[str] = []
    for frames in override_frames:
        try:
            if frames_to_render:
                if int(frames) in frames_to_render:
                    duplicates.append(frames)
            frames_to_render.append(int(frames))
        # when there is a dash in the frame string it can't be converted to an int
        # this way we can easily split single frames from ranges
        except ValueError:
            numbers = frames.split("-")
            for i in range(int(numbers[0]), int(numbers[1]) + 1):
                if frames_to_render:
                    if i in frames_to_render:
                        duplicates.append(str(i))
                frames_to_render.append(i)
    return ", ".join(duplicates)


def get_camera_names() -> list:
    """
    Gets all cameras present in the max scene and removes the target objects from the list.

    :returns: a list with cameras
    """
    cameras = [camera.name for camera in rt.cameras if "$Target:" not in str(camera)]
    return cameras


def get_stereo_cameras() -> list:
    """
    Gets the name all stereo cameras and their parent object present in the max scene. It also removes the target objects from
    the list.

    :returns: a list with stereo cameras and their relative position to their parent
    """
    all_cameras = [
        [camera.name, camera.parent, camera]
        for camera in rt.cameras
        if "$Target:" not in str(camera)
    ]
    stereo_cameras = []
    for camera in all_cameras:
        # Stereo camera plugin creates object of type StereoCameraAssemblyHead
        # When the plugin isn't loaded but used it changes that object to Helper_Stand_in
        if "StereoCameraAssemblyHead" in str(camera[1]) or "$Helper_Stand_in:" in str(camera[1]):
            relative_pos = list((camera[2].transform * rt.inverse(camera[1].transform)).position)
            stereo_cameras.append([camera[0], relative_pos])
    return stereo_cameras


def get_stereo_camera_names() -> list:
    """
    Gets the name all stereo cameras present in the max scene. It also removes the target objects from the list.

    :returns: a list with stereo cameras
    """
    all_cameras = [
        [camera.name, camera.parent, camera]
        for camera in rt.cameras
        if "$Target:" not in str(camera)
    ]
    stereo_cameras = []
    for camera in all_cameras:
        # Stereo camera plugin creates object of type StereoCameraAssemblyHead
        # When the plugin isn't loaded but used it changes that object to Helper_Stand_in
        if "StereoCameraAssemblyHead" in str(camera[1]) or "$Helper_Stand_in:" in str(camera[1]):
            stereo_cameras.append(camera[0])
    return stereo_cameras


def get_left_stereo_camera_names() -> list:
    """
    Gets the name all left stereo cameras. Cameras get isolated based on their relative position.

    :returns: a list with left stereo cameras
    """
    all_stereo_cameras = get_stereo_cameras()
    left_cams = [cam[0] for cam in all_stereo_cameras if cam[1][0] < 0]
    return left_cams


def get_right_stereo_camera_names() -> list:
    """
    Gets the name all right stereo cameras. Cameras get isolated based on their relative position.

    :returns: a list with right stereo cameras
    """
    all_stereo_cameras = get_stereo_cameras()
    right_cams = [cam[0] for cam in all_stereo_cameras if cam[1][0] > 0]
    return right_cams


def get_center_stereo_camera_names() -> list:
    """
    Gets the name all center stereo cameras. Cameras get isolated based on their relative position.

    :returns: a list with center stereo cameras
    """
    all_stereo_cameras = get_stereo_cameras()
    center_cams = [cam[0] for cam in all_stereo_cameras if cam[1][0] == 0]
    return center_cams


def stereo_plugin_used_but_not_loaded() -> bool:
    """
    Checks if a file uses the stereo camera plugin but isn't installed on the machine.
    Plugin: https://apps.autodesk.com/3DSMAX/en/Detail/Index?id=7617801885196793148&appLang=en&os=Win64

    :returns: a boolean indicating if the plugin is used but not installed
    """
    if rt.fileProperties.getItems("Used Plug-Ins"):
        used_plugins = [plugin for plugin in rt.fileProperties.getItems("Used Plug-Ins")]
        system_classes = [str(class_) for class_ in rt.system.classes]
        return "stereocamera.dlo" in used_plugins and "StereoCamera" not in system_classes
    return False


def stereo_plugin_used_and_loaded() -> bool:
    """
    Checks if a file uses the stereo camera plugin and installed on the machine.
    Plugin: https://apps.autodesk.com/3DSMAX/en/Detail/Index?id=7617801885196793148&appLang=en&os=Win64

    :returns: a boolean indicating if the plugin is used and installed
    """
    if rt.fileProperties.getItems("Used Plug-Ins"):
        used_plugins = [plugin for plugin in rt.fileProperties.getItems("Used Plug-Ins")]
        system_classes = [str(class_) for class_ in rt.system.classes]
        return "stereocamera.dlo" in used_plugins and "StereoCameraRig" in system_classes
    return False


def get_state_set_names() -> list:
    """
    Gets all state sets present in the max scene.

    :returns: a list with state set names and their index
    """
    state_sets_dot_net_object = rt.dotNetObject("Autodesk.Max.StateSets.Plugin")
    state_sets_instance = state_sets_dot_net_object.Instance
    master_state = state_sets_instance.EntityManager.RootEntity.MasterStateSet

    state_sets = []
    for i in range(-1, master_state.Children.count - 2):
        state_sets.append([master_state.Children.Item[i].Name, i + 1])
    return state_sets
