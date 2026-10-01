@echo off
REM Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
REM Quick batch script to update installed 3ds Max submitter and adaptor files
REM This is faster than rebuilding the entire installer during development

echo === 3ds Max Submitter and Adaptor File Updater ===
echo.

set SOURCE_ROOT=src\deadline
set DEST_ROOT=%USERPROFILE%\DeadlineCloudFor3dsMaxSubmitter\scripts\deadline
set MAX_PYTHON="C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe"

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

REM Also update the adaptor files in Python site-packages
set ADAPTOR_DEST=%APPDATA%\Python\Python311\site-packages\deadline

if exist "%ADAPTOR_DEST%" (
    echo.
    echo Updating max_adaptor files in site-packages...
    xcopy /E /Y /I "%SOURCE_ROOT%\max_adaptor" "%ADAPTOR_DEST%\max_adaptor"
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Failed to copy max_adaptor files
    ) else (
        echo   ✓ max_adaptor updated
    )

    echo Updating max_shared files in site-packages...
    xcopy /E /Y /I "%SOURCE_ROOT%\max_shared" "%ADAPTOR_DEST%\max_shared"
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Failed to copy max_shared files to site-packages
    ) else (
        echo   ✓ max_shared updated in site-packages
    )
) else (
    echo.
    echo NOTE: Adaptor site-packages directory not found: %ADAPTOR_DEST%
    echo       Skipping adaptor update. Run 'pip install -e .' to install the adaptor.
)

REM Build and install the latest wheel
echo.
echo === Building and Installing Latest Wheel ===

REM Check if 3ds Max Python exists
if not exist %MAX_PYTHON% (
    echo WARNING: 3ds Max 2026 Python not found at %MAX_PYTHON%
    echo          Skipping wheel installation.
    goto :skip_wheel
)

REM Build the wheel using hatch
echo Building wheel with hatch...
hatch build -t wheel
if %ERRORLEVEL% neq 0 (
    echo WARNING: Failed to build wheel with hatch
    goto :skip_wheel
)
echo   ✓ Wheel built successfully

REM Find the latest wheel file
for /f "delims=" %%i in ('dir /b /o-d dist\deadline_cloud_for_3ds_max-*.whl 2^>nul') do (
    set WHEEL_FILE=dist\%%i
    goto :found_wheel
)
echo WARNING: No wheel file found in dist directory
goto :skip_wheel

:found_wheel
echo Installing wheel: %WHEEL_FILE%
%MAX_PYTHON% -m pip install "%WHEEL_FILE%" --force-reinstall
if %ERRORLEVEL% neq 0 (
    echo WARNING: Failed to install wheel
) else (
    echo   ✓ Wheel installed successfully
)

:skip_wheel

echo.
echo === Update Complete ===
echo The installed 3ds Max submitter files have been updated.
echo.
echo Next steps:
echo 1. Restart 3ds Max if it's currently running
echo 2. Test the submitter to verify your changes work
echo.
pause