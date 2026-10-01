-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
-- V-Ray Local Export Script
-- Exports the current scene to a vrscene file using the specified animation mode.
-- Placeholders are filled in by Python's str.format() before passing to rt.execute().

fn ExportToVRayStd exportPath startFrame endFrame incrBaseFrame: =
(
    makeDir (getFileNamePath exportPath) all:true
    sysinfo.currentdir = getFileNamePath exportPath

    if not (iskindof renderers.activeShade VRayRT) do
        renderers.activeShade = VRayRT()

    if startFrame == endFrame then
        vrayExportRTScene exportPath separateFiles:false
    else if incrBaseFrame != unsupplied and incrBaseFrame != startFrame then
        vrayExportRTScene exportPath separateFiles:false startFrame:startFrame endFrame:endFrame incrBaseFrame:incrBaseFrame
    else
        vrayExportRTScene exportPath separateFiles:false startFrame:startFrame endFrame:endFrame
)

try (
    case {export_animation_mode} of
    (
        1: (
            -- Single File
            ExportToVRayStd @"{vrscene_path_escaped}" {start_frame} {end_frame}
        )
        2: (
            -- File Per Frame
            for i = {start_frame} to {end_frame} do
            (
                local paddedFrame = formattedPrint i format:"04i"
                local frameVrsceneName = @"{output_dir_escaped}\\" + "{base_name}." + paddedFrame + ".vrscene"
                ExportToVRayStd frameVrsceneName i (i + 1)
            )
        )
        3: (
            -- File Per Frame (Incremental)
            local paddedFrame = formattedPrint {start_frame} format:"04i"
            local frameVrsceneName = @"{output_dir_escaped}\\" + "{base_name}." + paddedFrame + ".vrscene"
            ExportToVRayStd frameVrsceneName {start_frame} ({start_frame} + 1)

            local vrsceneFileHandle = createfile @"{vrscene_path_escaped}"
            for i = ({start_frame} + 1) to {end_frame} do
            (
                paddedFrame = formattedPrint i format:"04i"
                frameVrsceneName = @"{output_dir_escaped}\\" + "{base_name}." + paddedFrame + ".vrscene"
                ExportToVRayStd frameVrsceneName i (i + 1) incrBaseFrame:{start_frame}
                format "#include \"%\"\n" frameVrsceneName to:vrsceneFileHandle
            )
            close vrsceneFileHandle
        )
    )
    "SUCCESS"
) catch (
    getCurrentException()
)
