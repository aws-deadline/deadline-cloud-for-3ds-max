-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

macroScript SubmitToDeadlineCloud category:"DeadlineCloud" buttontext:"Submit to Deadline Cloud" tooltip:"Submit to Deadline Cloud"
(
	-- change to true for development install
	local DEBUG = false
	
	-- runs the main ui window of the Deadline Cloud Max Submitter
	if DEBUG do
	(
		-- change to <reporoot>/src/deadline/max_submitter/run_ui.py
		-- TODO: parameterize the path here
		python.ExecuteFile @"src\deadline\max_submitter\run_ui.py"
	)
	
	if not DEBUG do
	(
		-- looks in 3ds Max scripts directory
		python.ExecuteFile "run_ui.py"
	)
)--end script