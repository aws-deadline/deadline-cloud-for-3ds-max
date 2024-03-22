-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

macroScript RunJobBundleTests category:"DeadlineCloud" buttontext:"Run Job Bundle Tests" tooltip:"Run Job Bundle Tests"
(
	local DEBUG = true
	
	-- runs the main ui window of the Deadline Cloud Max Submitter
	if DEBUG do
	(
		-- local repo path during development phase
		-- TODO: parameterize this path
		python.ExecuteFile @"src\deadline\max_submitter\job_bundle_output_test_runner.py"
	)
	
	if not DEBUG do
	(
		-- looks in 3ds Max scripts directory
		python.ExecuteFile "job_bundle_output_test_runner.py"
	)
)--end script