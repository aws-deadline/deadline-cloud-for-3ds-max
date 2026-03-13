-- V-Ray Standalone Export Script for Deadline Cloud
-- This script is run via 3dsmaxcmd.exe with the scene file already specified

fn ExportToVRayStd exportPath startFrame endFrame incrBaseFrame: =
(
    makeDir (getFileNamePath exportPath) all:true
    sysinfo.currentdir = getFileNamePath exportPath
    
    -- Ensure V-Ray RT is active shade renderer
    if not (iskindof renderers.activeShade VRayRT) do 
        renderers.activeShade = VRayRT()
    
    -- Export based on frame range
    if startFrame == endFrame then
        vrayExportRTScene exportPath separateFiles:false
    else if incrBaseFrame != unsupplied and incrBaseFrame != startFrame then
        vrayExportRTScene exportPath separateFiles:false startFrame:startFrame endFrame:endFrame incrBaseFrame:incrBaseFrame
    else
        vrayExportRTScene exportPath separateFiles:false startFrame:startFrame endFrame:endFrame
)

try (
    format "=== V-Ray Export Script Starting ===\n"
    format "Renderer: %\n" (classof renderers.current)
    format "ActiveShade: %\n" (classof renderers.activeShade)
    
    -- VRSceneOutputPath is resolved by OpenJD at runtime to the session path
    local vrsceneOutputPath = @"{{{{Param.VRSceneOutputPath}}}}"
    local exportAnimationMode = {export_animation_mode}
    local startFrame = {start_frame}
    local endFrame = {end_frame}
    
    format "Output: %\n" vrsceneOutputPath
    format "Mode: %\n" exportAnimationMode
    format "Range: % - %\n" startFrame endFrame
    
    case exportAnimationMode of
    (
        1: (
            -- Single File
            format "Exporting single vrscene file...\n"
            ExportToVRayStd vrsceneOutputPath startFrame endFrame
        )
        2: (
            -- File Per Frame
            local currentFrame = {start_frame}
            local paddedFrame = formattedPrint currentFrame format:"04i"
            local frameVrsceneName = (getFilenamePath vrsceneOutputPath) + (getFilenameFile vrsceneOutputPath) + "." + paddedFrame + ".vrscene"
            format "Exporting per-frame vrscene: %\n" frameVrsceneName
            ExportToVRayStd frameVrsceneName currentFrame (currentFrame + 1)
        )
        3: (
            -- File Per Frame (Incremental)
            local currentFrame = {start_frame}
            local paddedFrame = formattedPrint currentFrame format:"04i"
            local frameVrsceneName = (getFilenamePath vrsceneOutputPath) + (getFilenameFile vrsceneOutputPath) + "." + paddedFrame + ".vrscene"
            format "Exporting incremental vrscene: %\n" frameVrsceneName
            ExportToVRayStd frameVrsceneName currentFrame (currentFrame + 1) incrBaseFrame:startFrame
        )
    )
    
    format "=== Export completed successfully ===\n"
    quitMax #noPrompt exitCode:0
) catch (
    local errMsg = getCurrentException()
    format "ERROR: %\n" errMsg
    quitMax #noPrompt exitCode:1
)
