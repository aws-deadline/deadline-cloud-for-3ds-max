-- V-Ray Standalone Export MAXScript Job
-- Runs on Deadline workers to export vrscene files
-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

try
(
	local du = DeadlineUtil  -- Interface provided by Deadline 3ds Max plugin
	if du == undefined do
	(
		-- Stand-in struct for testing outside Deadline
		struct DeadlineUtilStruct
		(
			fn SetTitle title = ( format "Title: %\n" title ),
			fn SetProgress percent = (true),
			fn FailRender msg = ( throw msg ),
			fn GetJobInfoEntry key = ( undefined ),
			fn LogMessage msg = ( format "INFO: %\n" msg ),
			fn WarnMessage msg = ( format "WARNING: %\n" msg ),
			CurrentFrame = ((sliderTime as string) as integer),
			CurrentTask = ( -1 ),
			SceneFileName = ( maxFilePath + maxFileName ),
			SceneFilePath = ( maxFilePath )
		)
		du = DeadlineUtilStruct()
	)
	
	fn ExportToVRayStd exportPath startFrame endFrame incrBaseFrame: =
	(
		-- Create output directory
		makeDir (getFileNamePath exportPath) all:true
		sysinfo.currentdir = getFileNamePath exportPath
		
		-- Ensure VRayRT is the active shade renderer
		if not (iskindof renderers.activeShade VRayRT) do 
			renderers.activeShade = VRayRT()
		
		-- Export based on frame range
		if startFrame == endFrame then
			-- Single frame export
			vrayExportRTScene exportPath separateFiles:false
		else if incrBaseFrame != unsupplied and incrBaseFrame != startFrame then
			-- Incremental export (not first frame)
			vrayExportRTScene exportPath separateFiles:false startFrame:startFrame endFrame:endFrame incrBaseFrame:incrBaseFrame
		else
			-- Full animation or first frame of incremental
			vrayExportRTScene exportPath separateFiles:false startFrame:startFrame endFrame:endFrame
	)
	
	local st = timestamp()
	
	du.SetTitle "VRSCENE Export MAXScript Job"
	du.LogMessage ">Starting VRSCENE Export MAXScript Job..."
	
	-- Get job parameters
	local startFrame = (du.GetJobInfoEntry "Render_StartFrame") as integer
	local endFrame = (du.GetJobInfoEntry "Render_EndFrame") as integer
	local vrsceneName = du.GetJobInfoEntry "Render_InputFilename"
	local exportAnimationMode = du.GetJobInfoEntry "Render_ExportAnimationMode"
	
	-- Default to Single File mode
	if exportAnimationMode == "" do
		exportAnimationMode = "1"
	exportAnimationMode = exportAnimationMode as integer
	
	du.LogMessage ">Exporting VRSCENE File..."
	
	case exportAnimationMode of
	(
		1: (
			-- Single File: Export entire animation to one vrscene
			ExportToVRayStd vrsceneName startFrame endFrame
		)
		2: (
			-- File Per Frame: Export current frame to separate vrscene
			local frameVrsceneName = (getFilenamePath vrsceneName) + (getFilenameFile vrsceneName) + "." + (formattedPrint du.CurrentFrame format:"04i") + (getFilenameType vrsceneName)
			ExportToVRayStd frameVrsceneName du.CurrentFrame (du.CurrentFrame + 1)
		)
		3: (
			-- File Per Frame (Incremental): Export with reference to first frame
			local frameVrsceneName = (getFilenamePath vrsceneName) + (getFilenameFile vrsceneName) + "." + (formattedPrint du.CurrentFrame format:"04i") + (getFilenameType vrsceneName)
			ExportToVRayStd frameVrsceneName du.CurrentFrame (du.CurrentFrame + 1) incrBaseFrame:startFrame
		)
	)
	
	du.LogMessage ("+Finished VRSCENE Export MAXScript Job in "+ ((timestamp() - st)/1000.0) as string + " sec.")
	true
)
catch
(
	-- Error handling with stack trace (Max 2017+)
	if ((maxVersion())[1]/1000 as integer) >= 19 then
	(
		if hasCurrentExceptionStackTrace() then
		(
			local errorMessage = getCurrentException()
			DeadlineUtil.WarnMessage("MaxScript Error: " + errorMessage)
			local stackTrace = getCurrentExceptionStackTrace()
			stackTrace = filterString stackTrace "\n"
			for line in stackTrace do
				DeadlineUtil.WarnMessage(line)
		)
	)
	throw()
)
