-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
(
	-- change to true for development install
	local DEBUG = false
	
	-- runs python script to add repo path to max script locations
	python.Execute "import sys"
	python.Execute "import os"
    python.Execute "sys.path.append(os.path.expanduser(r'~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts'))"
	if DEBUG do
	(
		-- change to <reporoot>/src/deadline/max_submitter
		-- TODO: Update to find local dev repo
		python.Execute "sys.path.append(r'C:\Workspace\deadline-cloud-for-3ds-max\src\deadline\max_submitter')"
	)
	
	local theMainMenu = menuMan.getMainMenuBar()
	local theDeadlineCloudMenu = menuMan.findMenu "AWS Deadline"
	
	-- check if the AWS Deadline menu exists, if not make menu
	if theDeadlineCloudMenu != undefined do
	(
		menuMan.unRegisterMenu theDeadlineCloudMenu
		menuMan.updateMenuBar() 
	)	
	theDeadlineCloudMenu = menuMan.createMenu "AWS Deadline"

	local theMenuDefinitionArray = #(
			#(#menuitem,"SubmitToDeadlineCloud","DeadlineCloud","Submit to Deadline Cloud")
	)
	if DEBUG do
	(
		theMenuDefinitionArray = #(
			#(#menuitem,"SubmitToDeadlineCloud","DeadlineCloud","Submit to Deadline Cloud"),
			#(#menuitem,"TestJobBundleOutput","DeadlineCloud","Run Job Bundle Tests")
		)
	)

	for aDef in theMenuDefinitionArray do
	(
		-- check if it's a menu item or seperator
		case aDef[1] of
		(
			default:
			(
				try
				(
					-- create menu item and assign it to the AWS Deadline menu
					-- createActionItem 'macroScriptName' 'macroScriptCategory'
					theAction = menuMan.createActionItem aDef[2] aDef[3]
					theAction.setTitle aDef[4]
					theAction.setUseCustomTitle true
					theDeadlineCloudMenu.addItem theAction -1
				)catch()
			)
			#separator: 
			(
				try
				(
					theAction = menuMan.createSeparatorItem()
					theDeadlineCloudMenu.addItem theAction -1
				)catch()
			)
		)--end case
	)--end aDef loop
	
	-- assign AWS Deadline menu to the main menu
	theSubMenu = menuMan.createSubMenuItem "AWS Deadline" theDeadlineCloudMenu
	theMainMenu.addItem theSubMenu -1
	menuMan.updateMenuBar() 
)--end script