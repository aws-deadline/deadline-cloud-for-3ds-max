-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
-- Compatibility: 3ds Max 2025+

-- Function to create the AWS Deadline menu
function createDeadlineCloudMenu =
(
    -- Get the menu manager from the callback parameter
    local menuMgr = callbacks.notificationParam()
    local mainMenuBar = menuMgr.mainMenuBar
    
    -- No need to check for existing menu - the CreateSubMenu will handle it
    -- If a menu with the same GUID already exists, it will be replaced
    
    -- Create a new AWS Deadline menu with a unique GUID
    -- Using a fixed GUID ensures consistency across sessions
    local deadlineCloudMenuGUID = "F8FFB827-741C-4A81-8C89-BBF856DCF56D"
    local deadlineCloudMenu = mainMenuBar.CreateSubMenu deadlineCloudMenuGUID "AWS Deadline"
    
    -- Define menu items with their GUIDs
    local menuItems = #()
    
    -- Add the Submit to Deadline Cloud menu item
    local submitActionGUID = "6AC5FDFE-2AF7-4069-8493-D8A1462F4E7F"
    -- MacroScript action table ID is 647394
    local macroScriptActionTableID = 647394
    
    -- Create the Submit to Deadline Cloud action
    deadlineCloudMenu.CreateAction submitActionGUID macroScriptActionTableID "SubmitToDeadlineCloud`DeadlineCloud" title:"Submit to Deadline Cloud"
    
    -- Add the Test Job Bundle Output menu item if in DEBUG mode
    local DEBUG = false
    if DEBUG do
    (
        local testJobBundleGUID = "A2B3C4D5-E6F7-8901-2345-6789ABCDEF01"
        deadlineCloudMenu.CreateAction testJobBundleGUID macroScriptActionTableID "TestJobBundleOutput`DeadlineCloud" title:"Run Job Bundle Tests"
    )
    
    -- Python script to add repo path to max script locations
    python.Execute "import sys"
    python.Execute "import os"
    python.Execute "sys.path.append(os.path.expanduser(r'~\\DeadlineCloudSubmitter\\Submitters\\3dsMax\\scripts'))"
    
    if DEBUG do
    (
        -- change to <reporoot>/src/deadline/max_submitter
        -- TODO: Update to find local dev repo
        python.Execute "sys.path.append(r'C:\\Workspace\\deadline-cloud-for-3ds-max\\src\\deadline\\max_submitter')"
    )
)

-- Remove any existing callback with the same ID to avoid duplicates
callbacks.removeScripts id:#deadlineCloudMenu

-- Register the callback to create menus when 3ds Max loads menus
callbacks.addScript #cuiRegisterMenus createDeadlineCloudMenu id:#deadlineCloudMenu