-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

-- Get 3ds Max version
global maxVersion_ = maxVersion()
global majorVersion = maxVersion_[1]

-- Python script to add the submitter's own directories to sys.path.
-- Prepend (insert at 0) rather than append so the bundled 'deadline' package always wins
-- over any leaked older 'deadline' that may be present in a user or system Python install.
-- Use os.path.normpath / os.path.join so the entries are stored in canonical native form
-- (matching what run_ui.py's defense-in-depth bootstrap uses), keeping the exact-string
-- dedup below correct on Windows regardless of how the MAX_SUBMITTER env var was written
-- by the installer.
--
-- IMPORTANT: read the raw env value and truthy-check it BEFORE calling os.path.normpath.
-- os.path.normpath("") returns "." (truthy), which would otherwise cause "." and
-- "./deadline/max_submitter" to be prepended to sys.path if MAX_SUBMITTER were unset —
-- exactly the CWD-on-sys.path footgun this whole change is trying to eliminate.
python.Execute "import sys, os"
python.Execute "_dc_max_submitter_raw = os.environ.get('MAX_SUBMITTER', '')"
python.Execute "_dc_max_submitter_path = os.path.normpath(_dc_max_submitter_raw) if _dc_max_submitter_raw else ''"
python.Execute "_dc_sys_path_entries = tuple((_dc_max_submitter_path, os.path.join(_dc_max_submitter_path, 'deadline', 'max_submitter'))) if _dc_max_submitter_path else ()"
python.Execute "sys.path[:] = [p for p in sys.path if p not in _dc_sys_path_entries]"
python.Execute "sys.path[0:0] = list(_dc_sys_path_entries)"
python.Execute "del _dc_max_submitter_raw, _dc_max_submitter_path, _dc_sys_path_entries"

-- Check if this is 3ds Max 2024 or earlier (version 26000 and below)
if majorVersion <= 26000 then
(
    -- Compatibility: 3ds Max 2024
    local DEBUG = false
    
    local theMainMenu = menuMan.getMainMenuBar()
    local theDeadlineCloudMenu = menuMan.findMenu "AWS Deadline"
    
    -- Remove existing menu if it exists
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
        case aDef[1] of
        (
            default:
            (
                try
                (
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
        )
    )
    
    -- Assign AWS Deadline menu to the main menu
    theSubMenu = menuMan.createSubMenuItem "AWS Deadline" theDeadlineCloudMenu
    theMainMenu.addItem theSubMenu -1
    menuMan.updateMenuBar() 
)
else
(
    -- Compatibility: 3ds Max 2025+
    function createDeadlineCloudMenu =
    (
        local menuMgr = callbacks.notificationParam()
        local mainMenuBar = menuMgr.mainMenuBar
        
        local deadlineCloudMenuGUID = "F8FFB827-741C-4A81-8C89-BBF856DCF56D"
        local deadlineCloudMenu = mainMenuBar.CreateSubMenu deadlineCloudMenuGUID "AWS Deadline"
        
        local submitActionGUID = "6AC5FDFE-2AF7-4069-8493-D8A1462F4E7F"
        local macroScriptActionTableID = 647394
        
        deadlineCloudMenu.CreateAction submitActionGUID macroScriptActionTableID "SubmitToDeadlineCloud`DeadlineCloud" title:"Submit to Deadline Cloud"
        
        local DEBUG = false
        if DEBUG do
        (
            local testJobBundleGUID = "A2B3C4D5-E6F7-8901-2345-6789ABCDEF01"
            deadlineCloudMenu.CreateAction testJobBundleGUID macroScriptActionTableID "TestJobBundleOutput`DeadlineCloud" title:"Run Job Bundle Tests"
        )
        
    )

    -- Remove any existing callback with the same ID to avoid duplicates
    callbacks.removeScripts id:#deadlineCloudMenu

    -- Register the callback to create menus when 3ds Max loads menus
    callbacks.addScript #cuiRegisterMenus createDeadlineCloudMenu id:#deadlineCloudMenu
)