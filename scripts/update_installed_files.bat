@echo off
REM Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
REM Quick batch script to update installed 3ds Max submitter files
REM This is faster than rebuilding the entire installer during development

echo === 3ds Max Submitter File Updater ===
echo.

set SOURCE_ROOT=src\deadline
set DEST_ROOT=%USERPROFILE%\DeadlineCloudFor3dsMaxSubmitter\scripts\deadline

REM Check if source exists
if not exist "%SOURCE_ROOT%" (
    echo ERROR: Source directory not found: %SOURCE_ROOT%
    echo Make sure you're running this from the deadline-cloud-for-3ds-max root directory
    pause
    exit /b 1
)

REM Check if destination exists
if not exist "%DEST_ROOT%" (
    echo ERROR: Destination directory not found: %DEST_ROOT%
    echo Make sure the 3ds Max submitter is installed
    pause
    exit /b 1
)

echo Updating max_submitter files...
xcopy /E /Y /I "%SOURCE_ROOT%\max_submitter" "%DEST_ROOT%\max_submitter"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to copy max_submitter files
    pause
    exit /b 1
)
echo   ✓ max_submitter updated

echo Updating max_shared files...
xcopy /E /Y /I "%SOURCE_ROOT%\max_shared" "%DEST_ROOT%\max_shared"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to copy max_shared files
    pause
    exit /b 1
)
echo   ✓ max_shared updated

echo.
echo === Update Complete ===
echo The installed 3ds Max submitter files have been updated.
echo.
echo Next steps:
echo 1. Restart 3ds Max if it's currently running
echo 2. Test the submitter to verify your changes work
echo.
pause