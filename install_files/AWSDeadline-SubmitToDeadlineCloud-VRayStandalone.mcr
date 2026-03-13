-- AWS Deadline Cloud - V-Ray Standalone Submitter Macro
-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

macroScript SubmitToDeadlineCloudVRayStandalone
	category:"AWS Deadline Cloud"
	buttonText:"Submit V-Ray Standalone"
	toolTip:"Submit V-Ray Standalone Render Job To Deadline Cloud"
	icon:#("Deadline",1)
(
	-- Check if V-Ray is the current renderer
	local isVRay = false
	try
	(
		local rendererName = (classof renderers.current) as string
		isVRay = (findString rendererName "VRay" != undefined) or (findString rendererName "V_Ray" != undefined)
	)
	catch
	(
		isVRay = false
	)
	
	if not isVRay then
	(
		messageBox "V-Ray Standalone workflow requires V-Ray as the active renderer.\n\nPlease set V-Ray as your current renderer to use this workflow." title:"V-Ray Not Active"
		return false
	)
	
	-- Import the Python module and run the UI
	python.Execute "import sys"
	python.Execute "import os"
	
	-- Try development path first, then installed path
	local devPath = "C:\\Users\\Administrator\\gitrepos\\deadline-cloud-for-3ds-max\\src\\deadline\\max_submitter"
	local installedPath = (getDir #scripts) + "\\deadline\\max_submitter"
	
	local submitterPath = installedPath
	if (doesFileExist (devPath + "\\run_vray_standalone_ui.py")) then (
		submitterPath = devPath
		format "Using development path: %\n" submitterPath
	) else (
		format "Using installed path: %\n" submitterPath
	)
	
	python.Execute ("sys.path.insert(0, r'" + submitterPath + "')")
	
	-- Launch the V-Ray Standalone submitter
	python.Execute "from run_vray_standalone_ui import main"
	python.Execute "main()"
)
