# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
3ds Max Deadline Cloud Submitter - 3ds Max Submission utilities
"""

import logging
import os

import pymxs  # separate import to initialize
from data_classes import RenderSubmitterUISettings
from data_const import SCENE_TWEAKS_MATS
from deadline.client.job_bundle.submission import AssetReferences
from pymxs import runtime as rt
from utilities import max_utils

_logger = logging.getLogger(__name__)

# Global variables to use for communication between on_submit_callback and submitter.close
backup_saved = False
backup_file = ""
clear_mat = False
cleared_materials: list = []
unlock_mat = False
custom_mat = False
overridden_materials = ""


def save_max_backup_file(dest: str, use_max_hold: bool = False):
    """
    Creates a copy of the current max scene to a chosen destination directory.
    Functionality and structure based on original 3ds Max Deadline Submitter.

    :param dest: the destination filepath of the to-be-made copy
    :type dest: filepath in str form
    :param use_max_hold: a boolean indicating what type of copy needs to be made. True indicates the use of a Max Hold.
    Max Hold saves the scene and its settings to a disk-based buffer.
    :type use_max_hold: bool
    """
    if use_max_hold:
        hold_dir = rt.execute("GetDir #autoback") + "\\"
        # For backwards compatibility
        if str(rt.maxOps.productAppID) == "max":
            hold_filename = hold_dir + "maxhold.mx"
        else:
            hold_filename = hold_dir + "vizhold.mx"
        hold_temp_filename = hold_dir + "maxhold.tmp"
        hold_exists = os.path.exists(hold_filename)

        # Delete the old temp hold and create a copy of the current hold
        if hold_exists:
            rt.deleteFile(hold_temp_filename)
            rt.renameFile(hold_filename, hold_temp_filename)

        # Save the Max scene to the hold
        rt.holdMaxFile()

        if not os.path.exists(hold_filename):
            _logger.error(f"Saving the file as '{hold_filename}' via hold() did not work")
            return f"Saving the file as '{hold_filename}' via hold() did not work"

        # Remove old file before copying over
        if os.path.exists(dest):
            rt.deleteFile(dest)

        if not rt.renameFile(hold_filename, dest):
            if not rt.copyFile(hold_filename, dest):
                _logger.error(f"Could not copy the saved scene file to '{dest}'")
                return f"Could not copy the saved scene file to '{dest}'"

        if hold_exists:
            rt.deleteFile(hold_filename)
            rt.renameFile(hold_temp_filename, hold_filename)
    else:
        rt.saveMaxFile(dest, clearNeedSaveFlag=False, useNewFile=False, quiet=True)
        if not os.path.exists(dest):
            _logger.error(f"Saving the file as '{dest}' did not work")
            return f"Saving the file as '{dest}' did not work"
    return "undefined"


def restore_max_copy(src: str):
    """
    Restores the original file. Uses Max Fetch to get the data stored in the Hold.
    Functionality and structure based on original 3ds Max Deadline Submitter.

    :param src: the backup filepath
    :type src: filepath in str format
    """
    hold_dir = rt.execute("GetDir #autoback") + "\\"
    # For backwards compatibility
    if str(rt.maxOps.productAppID) == "max":
        hold_filename = hold_dir + "maxhold.mx"
    else:
        hold_filename = hold_dir + "vizhold.mx"
    hold_temp_filename = hold_dir + "maxhold.tmp"
    hold_exists = os.path.exists(hold_filename)

    if hold_exists:
        rt.deleteFile(hold_temp_filename)
        rt.renameFile(hold_filename, hold_temp_filename)

    rt.copyFile(src, hold_filename)
    if not os.path.exists(hold_filename):
        _logger.error("Restoring the file via fetch() did not work")
        return "Restoring the file via fetch() did not work"

    rt.fetchMaxFile(quiet=True)

    if hold_exists:
        rt.deleteFile(hold_filename)
        rt.renameFile(hold_temp_filename, hold_filename)

    _logger.debug("Restored the file successfully")
    return "undefined"


def merge_xrefs(settings: RenderSubmitterUISettings, assets: AssetReferences):
    """
    Merges the chosen types of XRefs in a temporary copy of the scene.
    Functionality and structure based on original 3ds Max Deadline Submitter.

    :param settings: a data class object containing the submitter ui settings
    :type settings: an instance of the RenderSubmitterUISettings dataclass

    :param assets: the asset references from the job attachments tab
    :type assets: an instance of the AssetReferences class
    """
    # Check if there are XRefs in the scene
    xref_scenes_count = rt.xrefs.getXRefFileCount()
    xref_objects_count = rt.objXrefMgr.recordCount
    if (settings.merge_xref_scn and xref_scenes_count > 0) or (
        settings.merge_xref_obj and xref_objects_count > 0
    ):
        _logger.debug(f"Assets pre-merge: {assets.to_dict()}")
        if settings.merge_xref_scn:
            assets = merge_xref_scenes(assets)
        if settings.merge_xref_obj:
            assets = merge_xref_objects(assets)
        _logger.debug(f"Assets post-merge: {assets.to_dict()}")
    # Always return assets, whether merging was applied or not
    return assets


def merge_xref_scenes(assets: AssetReferences):
    """
    Merges the scene XRefs. Disabled and missing XRefs get removed from the file.
    Functionality and structure based on original 3ds Max Deadline Submitter.

    :param assets: the asset references from the job attachments tab
    :type assets: an instance of the AssetReferences class
    """
    done_merging = False
    iterations = 1
    input_files = assets.input_filenames
    while not done_merging:
        failed_files = []
        current_xrefs_count = rt.xrefs.getXRefFileCount()
        for i in range(current_xrefs_count, 0, -1):
            xref_file = rt.xrefs.getXRefFile(i)
            xref_filepath = xref_file.filename
            # Check that file exists
            if os.path.exists(xref_filepath):
                # Check if the XRef is enabled
                # If it is, merge
                if not xref_file.disabled:
                    result = rt.merge(xref_file)
                    if result:
                        input_files.discard(xref_filepath)
                        _logger.info(f"Merged Scene XRef File {i} [{xref_filepath}]")
                    else:
                        _logger.warning(f"Failed to merge Scene XRef {i} [{xref_filepath}]")
                        failed_files.append(xref_filepath)
                # If it is not, delete the XRef to avoid surprises at render time
                else:
                    result = rt.delete(xref_file)
                    if result:
                        _logger.info(f"Deleted Disabled Scene XRef File {i} [{xref_filepath}]")
                    else:  # should never happen
                        _logger.warning(
                            f"Failed to delete disabled Scene XRef {i} [{xref_filepath}]"
                        )
                        failed_files.append(xref_filepath)
            # When the file doesn't exist delete the XRef
            else:
                result = rt.delete(xref_file)
                if result:
                    _logger.info(f"Deleted Missing Scene XRef File {i} [{xref_filepath}]")
                else:  # should never happen
                    _logger.warning(f"Failed to delete missing Scene XRef {i} [{xref_filepath}]")
                    failed_files.append(xref_filepath)
        files_to_merge = 0
        current_xrefs_count = rt.xrefs.getXRefFileCount()
        for i in range(1, current_xrefs_count):
            xref_file = rt.xrefs.getXRefFile(i)
            if xref_file.filename in failed_files:
                files_to_merge += 1
        done_merging = files_to_merge == 0
        _logger.info(
            f"End of Scene XRef Merging iteration {iterations} - {files_to_merge} files left to merge"
        )
        iterations += 1
    assets.input_filenames = input_files
    _logger.info("Done merging Scene XRefs")
    return assets


def merge_xref_objects(assets: AssetReferences):
    """
    Merges the XRef objects. Disabled and missing XRefs get removed from the file.
    Functionality and structure based on original 3ds Max Deadline Submitter.

    :param assets: the asset references from the job attachments tab
    :type assets: an instance of the AssetReferences class
    """
    done_merging = False
    iterations = 1
    input_files = assets.input_filenames
    while not done_merging:
        failed_files = []
        current_xrefs_count = rt.objXrefMgr.recordCount
        for i in range(current_xrefs_count, 0, -1):
            xref_record = rt.objXrefMgr.GetRecord(i)
            xref_filepath = xref_record.srcFileName
            # Check that file exists
            if os.path.exists(xref_filepath):
                # Check if the XRef is enabled
                # If it is, merge
                if xref_record.enabled:
                    result = rt.objXrefMgr.MergeRecordIntoScene(xref_record)
                    if result:
                        input_files.discard(xref_filepath)
                        _logger.info(f"Merged XRef Object {i} [{xref_filepath}]")
                    else:
                        _logger.warning(f"Failed to merge XRef Object {i} [{xref_filepath}]")
                        failed_files.append(xref_filepath)
                # If it is not, delete the XRef to avoid surprises at render time
                else:
                    # Note: XRef objects have to be enabled before
                    #       operations can be done on them
                    xref_record.enabled = True
                    result = rt.objXrefMgr.RemoveRecordFromScene(xref_record)
                    if result:
                        _logger.info(f"Deleted Disabled XRef Object {i} [{xref_filepath}]")
                    else:  # should never happen
                        _logger.warning(
                            f"Failed to delete disabled XRef Object {i} [{xref_filepath}]"
                        )
                        failed_files.append(xref_filepath)
            # When the file doesn't exist delete the XRef
            else:
                # note: XRef objects have to be enabled before
                #       operations can be done on them
                xref_record.enabled = True
                result = rt.objXrefMgr.RemoveRecordFromScene(xref_record)
                if result:
                    _logger.info(f"Deleted Missing XRef Objects {i} [{xref_filepath}]")
                else:  # should never happen
                    _logger.warning(f"Failed to delete missing XRef Object {i} [{xref_filepath}]")
                    failed_files.append(xref_filepath)
        files_to_merge = 0
        current_xrefs_count = rt.objXrefMgr.recordCount
        for i in range(1, current_xrefs_count):
            xref_record = rt.objXrefMgr.GetRecord(i)
            if xref_record.srcFileName in failed_files:
                files_to_merge += 1
        done_merging = files_to_merge == 0
        _logger.info(
            f"End of XRef Object Merging iteration {iterations} - {files_to_merge} files left to merge"
        )
        iterations += 1
    assets.input_filenames = input_files
    _logger.info("Done merging XRefs Objects")
    return assets


def clear_material_editor() -> list:
    """
    Clears the Material Editor in the submitted file.
    Functionality and structure based on original 3ds Max Deadline Submitter.

    :returns: a list with the saved materials
    """
    editor_open = rt.MatEditor.isOpen()
    if editor_open:
        rt.MatEditor.Close()
        _logger.info("Closed the Material Editor")
    material_storage = []
    # Note: meditMaterials is a system global containing 24 sample slots in the Material Editor
    for i in range(24):
        material_storage.append(rt.meditMaterials[i])
        rt.meditMaterials[i] = rt.standard()
    _logger.info("Cleared the Material Editor")
    return material_storage


def restore_material_editor(materials: list):
    """
    Restores the Material Editor to the original state.
    Functionality and structure based on original 3ds Max Deadline Submitter.

    :param materials: the previously saved materials we want to restore
    """
    # Note: meditMaterials is a system global containing 24 sample slots in the Material Editor
    for i in range(24):
        rt.meditMaterials[i] = materials[i]
    _logger.info("Restored the Material Editor")


def unlock_material_editor_renderer():
    """
    Unlock the Material Editor's renderer to use Default Scanline Renderer.
    Functionality and structure based on original 3ds Max Deadline Submitter.
    """
    locked = rt.renderers.medit_locked
    if locked:
        rt.renderers.medit_locked = False
        _logger.info("Unlocked the Material Editor Renderer")


def lock_material_editor_renderer():
    """
    Locks the Material Editor's renderer.
    Functionality and structure based on original 3ds Max Deadline Submitter.
    """
    locked = rt.renderers.medit_locked
    if not locked:
        rt.renderers.medit_locked = True
        _logger.info("Locked the Material Editor Renderer")


def apply_custom_material(custom_mat_: str) -> str:
    """
    Applies a custom user-defined material to all geometry objects in the scene.
    Functionality and structure based on original 3ds Max Deadline Submitter.

    :param custom_mat_: a str representing the user-defined material from the ui

    :returns: a MaxScript list of the original materials applied to the objects in format
    #(#(object, material, colorByLayer bool)). Has to be a MaxScript list so that we can later restore them
    correctly in python
    """
    old_materials = rt.execute(
        "old_materials = for o in objects collect #(o, o.material, o.colorByLayer)"
    )
    if custom_mat_ == SCENE_TWEAKS_MATS[0]:
        rt.execute("objects.material = standard()")
        mat_type = SCENE_TWEAKS_MATS[0]
    if custom_mat_ == SCENE_TWEAKS_MATS[1]:
        rt.execute("objects.material = undefined")
        mat_type = SCENE_TWEAKS_MATS[1]
    if custom_mat_ == SCENE_TWEAKS_MATS[2]:
        rt.execute("objects.material = undefined \n" "objects.colorByLayer = true")
        mat_type = SCENE_TWEAKS_MATS[2]
    if custom_mat_ == SCENE_TWEAKS_MATS[3]:
        if rt.superClassOf(rt.meditmaterials[1]) == "material":
            rt.execute("objects.material = meditmaterial[1]")
            mat_type = SCENE_TWEAKS_MATS[3]
        else:
            rt.execute("objects.material = standard()")
            mat_type = "Standard Grayscale Material Instead Of Medit Slot 1"
    _logger.info(f"Assigned {mat_type} to Scene Objects")
    return old_materials


def restore_scene_materials(materials):
    """
    Restores the material on all geometry objects in the scene if they were previously overwritten with a
    custom user-defined material.
    Functionality and structure based on original 3ds Max Deadline Submitter.

    :param materials: the previously stored materials we want to revert back to in format
    [object, material, colorByLayer bool]
    """
    for obj in materials:
        obj[0].material = obj[1]
        obj[0].colorByLayer = obj[2]
    _logger.info("Restored the materials of the Scene Objects")


def save_scene():
    """
    Save scene to make scene sticky when submitting job
    """
    scene = rt.maxFilePath + rt.maxFileName
    rt.saveMaxFile(scene)


def make_paths_absolute():
    """
    Makes all relative filepaths in the scene absolute.
    When there are nested XRefs, new XRefs get created to guarantee their relative paths also become absolute.
    """
    # The DialogMonitorOPS.RegisterNotification() MAXScript callback takes a string as argument, meaning it can't
    # take a python function. This is a MAXScript function formatted as a string that automatically presses the
    # default button of a dialog
    close_error_mxs_function = """fn closeError = (
        local windowHandle = DialogMonitorOPS.GetWindowHandle()
        if (windowHandle != 0) then (
            UIAccessor.PressDefaultButton()
            true
        ) else false
    )
    """
    rt.execute(f"closeError={close_error_mxs_function}")

    # Check for deep references
    scene = max_utils.get_scene_path()

    # Refresh Asset Tracking panel to make sure it uses the correct references
    rt.ATSOps.Refresh()
    linked_files = rt.ATSOps.GetDependentFiles(scene, True, pymxs.byref(None))[1]
    nested_files: list[list[str]] = []
    for file in linked_files:
        nested_file = rt.ATSOps.GetDependentFiles(file, False, pymxs.byref(None))[1]
        for item in nested_file:
            # Only add to list if path is relative
            if item and not os.path.isabs(item) and os.path.splitext(item)[1] == ".max":
                # If the parent file of the current item is a nested file, join the path with its parent to get the
                # correct parent directory
                already_nested = [x[0] for x in nested_files]
                if file in already_nested:
                    index = already_nested.index(file)
                    relative_dir = os.path.split(nested_files[index][1])[0]
                    file = os.path.join(relative_dir, nested_files[index][0])
                nested_files += [[item, file]]

    # If there are deep references, remove from selection and create new xref
    if nested_files:
        for file in nested_files:
            linked_files.remove(file[0])
            relative_dir = os.path.split(file[1])[0]
            full_path = os.path.join(rt.maxFilePath, relative_dir, file[0])
            rt.xrefs.addNewXRefFile(full_path)
            _logger.debug(f"created xref for {full_path}")

    # Assign the MAXScript function we made to the error dialog that will pop up
    # Note: Error message that pops up is caused by any nested relative paths, we make new XRefs for each nested file
    # so this error has to be ignored
    rt.DialogMonitorOps.unRegisterNotification(id=rt.name("fileMan_closeErrorDialog"))
    rt.DialogMonitorOps.enabled = True
    rt.DialogMonitorOps.interactive = False
    rt.DialogMonitorOps.registerNotification(rt.closeError, id=rt.name("fileMan_closeErrorDialog"))

    # Select files we want to make absolute
    rt.ATSOps.SelectFiles(linked_files)
    rt.ATSOps.ResolveSelectionToAbsolute()

    # Remove the MAXScript callback to avoid unexpected behaviour with other errors
    rt.DialogMonitorOps.unRegisterNotification(id=rt.name("fileMan_closeErrorDialog"))
    rt.DialogMonitorOps.enabled = False
    rt.DialogMonitorOps.interactive = True
