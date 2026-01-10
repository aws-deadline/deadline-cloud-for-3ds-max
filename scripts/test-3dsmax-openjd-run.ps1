# 3ds Max Adaptor Testing Script
# Tests the deadline-cloud-for-3ds-max adaptor directly without worker agent setup

param(
    [string]$JobBundleDir,
    [string]$WheelPath = "",
    [string]$MaxVersion = "2026",
    [int]$Step = 0,
    [string]$PathMappingFile = "",
    [switch]$SkipInstall,
    [switch]$ShowOutput,
    [switch]$Help
)

# Show help if requested
if ($Help) {
    Write-Host "=== 3ds Max Adaptor Testing Script Help ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "DESCRIPTION:" -ForegroundColor Yellow
    Write-Host "  Tests the deadline-cloud-for-3ds-max adaptor directly without worker agent setup"
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  Run this script from the repository root directory:" -ForegroundColor Yellow
    Write-Host "  .\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir <path>" -ForegroundColor Cyan
    Write-Host "  Example: .\scripts\test-3dsmax-openjd-run.ps1 -JobBundleDir test_bundle" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "PARAMETERS:" -ForegroundColor Yellow
    Write-Host "  -JobBundleDir    (Required) Path to the job bundle directory" -ForegroundColor Cyan
    Write-Host "  -WheelPath       Path to the wheel file to install" -ForegroundColor Cyan
    Write-Host "  -MaxVersion      3ds Max version (default: 2026)" -ForegroundColor Cyan
    Write-Host "  -Step            Step number to run (default: 0)" -ForegroundColor Cyan
    Write-Host "  -PathMappingFile Path to JSON file with path mapping rules (optional)" -ForegroundColor Cyan
    Write-Host "  -SkipInstall     Skip wheel installation (optional)" -ForegroundColor Cyan
    Write-Host "  -ShowOutput      Show detailed output (optional)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "PREREQUISITES:" -ForegroundColor Yellow
    Write-Host "  Install PowerShell YAML module for proper parameter parsing:"
    Write-Host "  Install-Module powershell-yaml -Force" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}

# Validate required parameters
if ([string]::IsNullOrEmpty($JobBundleDir)) {
    Write-Error "JobBundleDir parameter is required. Use -Help for usage information."
    Write-Host "Example: .\test-3dsmax-openjd.ps1 -JobBundleDir test_bundle" -ForegroundColor Yellow
    exit 1
}

# Auto-detect wheel file if not provided
if ([string]::IsNullOrEmpty($WheelPath)) {
    $wheelFiles = Get-ChildItem "dist\deadline_cloud_for_3ds_max-*.whl" | Sort-Object LastWriteTime -Descending
    if ($wheelFiles) {
        $WheelPath = $wheelFiles[0].FullName
        Write-Host "Auto-detected wheel file: $WheelPath" -ForegroundColor Gray
    } else {
        Write-Error "No wheel files found in dist directory. Please build the wheel first with 'hatch build' or specify -WheelPath"
        exit 1
    }
}

# Configuration
$MaxPythonPath = "C:\Program Files\Autodesk\3ds Max $MaxVersion\Python\python.exe"
$LogDir = "C:\Users\$env:USERNAME\AppData\Local\Autodesk\3dsMax\$MaxVersion - 64bit\ENU\Network"

Write-Host "=== 3ds Max Adaptor Testing Script ===" -ForegroundColor Green
Write-Host "Wheel: $WheelPath" -ForegroundColor Cyan
Write-Host "Max Version: $MaxVersion" -ForegroundColor Cyan
Write-Host "Job Bundle: $JobBundleDir" -ForegroundColor Cyan
Write-Host "Step: $Step" -ForegroundColor Cyan

# Function to check prerequisites
function Test-Prerequisites {
    Write-Host "`n--- Checking Prerequisites ---" -ForegroundColor Yellow
    
    # Check if 3ds Max Python exists
    if (-not (Test-Path $MaxPythonPath)) {
        Write-Error "3ds Max Python not found at: $MaxPythonPath"
        Write-Host "Please ensure 3ds Max $MaxVersion is installed" -ForegroundColor Red
        return $false
    }
    Write-Host "3ds Max Python found" -ForegroundColor Green
    
    # Check if wheel file exists
    if (-not (Test-Path $WheelPath)) {
        Write-Error "Wheel file not found at: $WheelPath"
        return $false
    }
    Write-Host "Wheel file found" -ForegroundColor Green
    
    # Check if job bundle exists
    if (-not (Test-Path $JobBundleDir)) {
        Write-Error "Job bundle directory not found: $JobBundleDir"
        return $false
    }
    Write-Host "Job bundle directory found" -ForegroundColor Green
    
    # Check if openjd-cli is installed
    Write-Host "Checking openjd-cli installation..." -ForegroundColor Gray
    try {
        $openjdCheck = & $MaxPythonPath -c "import openjd.cli; print('openjd-cli available')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "openjd-cli is installed" -ForegroundColor Green
        } else {
            Write-Host "openjd-cli not found, installing..." -ForegroundColor Yellow
            & $MaxPythonPath -m pip install openjd-cli
            if ($LASTEXITCODE -eq 0) {
                Write-Host "openjd-cli installed successfully" -ForegroundColor Green
            } else {
                Write-Error "Failed to install openjd-cli"
                return $false
            }
        }
    } catch {
        Write-Host "Installing openjd-cli..." -ForegroundColor Yellow
        & $MaxPythonPath -m pip install openjd-cli
        if ($LASTEXITCODE -eq 0) {
            Write-Host "openjd-cli installed successfully" -ForegroundColor Green
        } else {
            Write-Error "Failed to install openjd-cli"
            return $false
        }
    }
    
    return $true
}

# Function to setup environment variables
function Setup-Environment {
    Write-Host "`n--- Setting Up Environment ---" -ForegroundColor Yellow
    
    $maxPythonDir = Split-Path $MaxPythonPath -Parent
    $repoPath = Get-Location
    $maxSubmitterPath = "$repoPath\src\deadline\max_submitter"
    
    # Set PATH with 3ds Max Python and executable FIRST (highest priority)
    $maxExecutableDir = "C:\Program Files\Autodesk\3ds Max $MaxVersion"
    Write-Host "Setting up PATH with 3ds Max priority..." -ForegroundColor Gray
    $env:PATH = "$maxPythonDir;$maxExecutableDir;$env:PATH"
    Write-Host "Updated PATH to include:" -ForegroundColor Green
    Write-Host "  - 3ds Max Python: $maxPythonDir" -ForegroundColor Green
    Write-Host "  - 3ds Max Executable: $maxExecutableDir" -ForegroundColor Green
    
    # Set PYTHONPATH with 3ds Max Python FIRST
    $env:PYTHONPATH = "$maxPythonDir;$repoPath\src;$maxSubmitterPath"
    Write-Host "Set PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Green
    
    # Set ADSK_3DSMAX_SCRIPTS_ADDON_DIR
    $env:ADSK_3DSMAX_SCRIPTS_ADDON_DIR = $maxSubmitterPath
    Write-Host "Set ADSK_3DSMAX_SCRIPTS_ADDON_DIR: $maxSubmitterPath" -ForegroundColor Green
    
    # Verify Python priority - CRITICAL CHECK
    Write-Host "`n--- Verifying Python Priority ---" -ForegroundColor Yellow
    try {
        $pythonPath = (Get-Command python -ErrorAction Stop).Source
        $pythonVersion = & python --version 2>&1
        
        Write-Host "Expected 3ds Max Python: $MaxPythonPath" -ForegroundColor Cyan
        Write-Host "Actual Default Python:   $pythonPath" -ForegroundColor Cyan
        Write-Host "Version: $pythonVersion" -ForegroundColor Cyan
        
        # Check if the paths match (normalize for comparison)
        $expectedNorm = $MaxPythonPath.ToLower().Replace('\', '/')
        $actualNorm = $pythonPath.ToLower().Replace('\', '/')
        
        if ($actualNorm -eq $expectedNorm) {
            Write-Host "SUCCESS: 3ds Max Python is now the default Python" -ForegroundColor Green
        } else {
            Write-Host "CRITICAL ERROR: Wrong Python interpreter detected!" -ForegroundColor Red
            Write-Host "Expected: $MaxPythonPath" -ForegroundColor Red
            Write-Host "Got:      $pythonPath" -ForegroundColor Red
            Write-Host ""
            Write-Host "This will cause module import failures. Exiting..." -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "FAILED: Could not verify Python priority" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Note: Environment changes are temporary for this session only" -ForegroundColor Yellow
    return $true
}

# Function to install the adaptor
function Install-Adaptor {
    Write-Host "`n--- Installing Adaptor ---" -ForegroundColor Yellow
    
    Write-Host "Running: $MaxPythonPath -m pip install $WheelPath --force-reinstall" -ForegroundColor Cyan
    
    try {
        & $MaxPythonPath -m pip install $WheelPath --force-reinstall --no-deps
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Adaptor installed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Error "Failed to install adaptor (exit code: $LASTEXITCODE)"
            return $false
        }
    } catch {
        Write-Error "Exception during installation: $($_.Exception.Message)"
        return $false
    }
}

# Function to build test command from job bundle
function Build-TestCommand {
    Write-Host "`n--- Building Test Command ---" -ForegroundColor Yellow
    
    # Read parameter values
    $paramFile = Join-Path $JobBundleDir "parameter_values.yaml"
    if (-not (Test-Path $paramFile)) {
        Write-Error "Parameter values file not found: $paramFile"
        return $null
    }
    
    # Import PowerShell-Yaml module for proper YAML parsing
    try {
        Import-Module powershell-yaml -ErrorAction Stop
        Write-Host "Using PowerShell-Yaml module for parsing" -ForegroundColor Gray
    } catch {
        Write-Error "PowerShell-Yaml module is required for YAML parsing."
        Write-Host "Please install it with: Install-Module powershell-yaml -Force" -ForegroundColor Yellow
        return $null
    }
    
    # Parse YAML properly
    $paramContent = Get-Content $paramFile -Raw
    $yamlData = ConvertFrom-Yaml $paramContent
    
    # Extract values from parsed YAML
    $getValue = { param($name) 
        $param = $yamlData.parameterValues | Where-Object { $_.name -eq $name }
        if ($param) { 
            return $param.value 
        } else { 
            return "" 
        }
    }
    
    # Get frames for run data
    $frames = & $getValue "Frames"
    $frames = if ([string]::IsNullOrEmpty($frames)) { "0" } else { $frames }
    
    # Read template file to extract renderer, state_set, and output_file_name
    $templateFile = Join-Path $JobBundleDir "template.yaml"
    if (-not (Test-Path $templateFile)) {
        Write-Error "Template file not found: $templateFile"
        return $null
    }
    
    $templateContent = Get-Content $templateFile -Raw
    $templateData = ConvertFrom-Yaml $templateContent
    
    # Validate step number against available steps
    if (-not $templateData.steps -or $templateData.steps.Count -eq 0) {
        Write-Error "No steps found in template file"
        return $null
    }
    
    if ($Step -lt 0 -or $Step -ge $templateData.steps.Count) {
        Write-Error "Step number $Step is out of range. Available steps: 0 to $($templateData.steps.Count - 1)"
        Write-Host "Available steps:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $templateData.steps.Count; $i++) {
            Write-Host "  Step $i`: $($templateData.steps[$i].name)" -ForegroundColor Gray
        }
        return $null
    }
    
    # Get the selected step
    $selectedStep = $templateData.steps[$Step]
    Write-Host "Selected step: $($selectedStep.name)" -ForegroundColor Green
    
    # Extract camera from taskParameterDefinitions
    $defaultCamera = "Unknown"  # fallback
    if ($selectedStep.parameterSpace -and $selectedStep.parameterSpace.taskParameterDefinitions) {
        $cameraParam = $selectedStep.parameterSpace.taskParameterDefinitions | Where-Object { $_.name -eq "Camera" }
        if ($cameraParam -and $cameraParam.range -and $cameraParam.range.Count -gt 0) {
            $defaultCamera = $cameraParam.range[0]
            Write-Host "Found camera parameter: $defaultCamera" -ForegroundColor Green
        }
    }
    Write-Host "Using camera parameter: $defaultCamera" -ForegroundColor Green
    
    # Extract initData section from template
    $initDataSection = $templateData.steps[0].stepEnvironments[0].script.embeddedFiles | Where-Object { $_.name -eq "initData" }
    if (-not $initDataSection) {
        Write-Error "Could not extract initData section from template file: $templateFile"
        Write-Host "Template structure may be invalid or different than expected" -ForegroundColor Red
        return $null
    }
    
    # Get the raw initData template string and substitute parameter values
    $initDataTemplate = $initDataSection.data
    
    # Substitute all parameter placeholders with actual values
    foreach ($param in $yamlData.parameterValues) {
        $placeholder = "{{Param.$($param.name)}}"
        $initDataTemplate = $initDataTemplate -replace [regex]::Escape($placeholder), $param.value
    }
    
    Write-Host "Substituted initData template:" -ForegroundColor Gray
    Write-Host $initDataTemplate -ForegroundColor Gray
    
    # Parse the substituted YAML to get the final init data
    $initDataYaml = ConvertFrom-Yaml $initDataTemplate
    $initData = $initDataYaml | ConvertTo-Json -Compress
    
    # Build run data JSON (use correct parameter names from template)
    $runData = @{
        Frame = [string]$frames.Split(',')[0].Split('-')[0]  # Take first frame as string
        Camera = $defaultCamera
    } | ConvertTo-Json -Compress
    
    # Get template file path
    $templateFile = Join-Path $JobBundleDir "template.yaml"
    
    # Create temporary JSON files for parameters
    $tempDir = [System.IO.Path]::GetTempPath()
    $jobParamsFile = Join-Path $tempDir "3dsmax-job-params.json"
    $taskParamsFile = Join-Path $tempDir "3dsmax-task-params.json"
    
    # Create complete job parameters from parameter_values.yaml (including deadline: parameters)
    $allJobParams = @{}
    foreach ($param in $yamlData.parameterValues) {
        $allJobParams[$param.name] = $param.value
    }

    $allJobParamsJson = $allJobParams | ConvertTo-Json -Compress
    
    # Create filtered job parameters for OpenJD (without deadline: parameters)
    $filteredJobParams = @{}
    foreach ($param in $yamlData.parameterValues) {
        if (-not $param.name.StartsWith("deadline:")) {
            $filteredJobParams[$param.name] = $param.value
        }
    }
    $filteredJobParamsJson = $filteredJobParams | ConvertTo-Json -Compress
    
    # Write complete job parameters to main file
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($jobParamsFile, $allJobParamsJson, $utf8NoBom)
    
    # Write filtered parameters to runner file
    $runnerJobParamsFile = Join-Path $tempDir "3dsmax-job-params-runner.json"
    [System.IO.File]::WriteAllText($runnerJobParamsFile, $filteredJobParamsJson, $utf8NoBom)
    
    # Parse run data to get task parameters and write to JSON file
    $runDataObj = $runData | ConvertFrom-Json
    $taskParamsArray = @()
    $taskParams = @{}
    foreach ($property in $runDataObj.PSObject.Properties) {
        # Ensure all values are strings for OpenJD compatibility
        $taskParams[$property.Name] = [string]$property.Value
    }
    $taskParamsArray += $taskParams
    # Force array structure even with single item
    if ($taskParamsArray.Count -eq 1) {
        $taskParamsJson = "[$($taskParamsArray | ConvertTo-Json -Compress)]"
    } else {
        $taskParamsJson = $taskParamsArray | ConvertTo-Json -Compress
    }
    [System.IO.File]::WriteAllText($taskParamsFile, $taskParamsJson, $utf8NoBom)
    
    # Build openjd run command with JSON file references using 3ds Max Python
    $stepName = $selectedStep.name
    $testCommand = "`"$MaxPythonPath`" -m openjd run `"$templateFile`" --step `"$stepName`" --job-param `"file://$runnerJobParamsFile`" --tasks `"file://$taskParamsFile`""
    
    # Add path mapping rules if provided
    if (-not [string]::IsNullOrEmpty($PathMappingFile)) {
        if (Test-Path $PathMappingFile) {
            $pathMappingContent = Get-Content $PathMappingFile -Raw
            # Escape for command line - convert to single line and escape quotes
            $pathMappingJson = $pathMappingContent -replace "`r`n", "" -replace "`n", "" -replace '"', '\"'
            $testCommand += " --path-mapping-rules `"$pathMappingJson`""
            Write-Host "`nPath Mapping Rules File: $PathMappingFile" -ForegroundColor Yellow
            Write-Host $pathMappingContent -ForegroundColor Gray
        } else {
            Write-Error "Path mapping file not found: $PathMappingFile"
            return $null
        }
    }
    
    # Print parameter information to console
    Write-Host "`nComplete Job Parameters JSON ($jobParamsFile):" -ForegroundColor Yellow
    Write-Host $allJobParamsJson -ForegroundColor Gray
    
    Write-Host "`nFiltered Job Parameters for Runner JSON ($runnerJobParamsFile):" -ForegroundColor Yellow
    Write-Host $filteredJobParamsJson -ForegroundColor Gray
    
    Write-Host "`nTask Parameters JSON ($taskParamsFile):" -ForegroundColor Yellow
    Write-Host $taskParamsJson -ForegroundColor Gray
    
    Write-Host "Scene File: $sceneFile" -ForegroundColor Cyan
    Write-Host "Frame: $($runData | ConvertFrom-Json | Select-Object -ExpandProperty frame)" -ForegroundColor Cyan
    Write-Host "Output: $outputPath" -ForegroundColor Cyan
    Write-Host "`nTest Command:" -ForegroundColor Yellow
    Write-Host $testCommand -ForegroundColor White
    
    return $testCommand
}

# Function to run the test
function Run-Test {
    param([string]$TestCommand)
    
    Write-Host "`n--- Running Test ---" -ForegroundColor Yellow
    Write-Host "Command: $TestCommand" -ForegroundColor Cyan
    
    $startTime = Get-Date
    Write-Host "Started at: $startTime" -ForegroundColor Gray
    
    try {
        # Run the command and capture output
        $output = cmd /c $TestCommand 2>&1
        $endTime = Get-Date
        $duration = $endTime - $startTime
        
        Write-Host "`nTest completed in: $($duration.TotalSeconds) seconds" -ForegroundColor Gray
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Test completed successfully!" -ForegroundColor Green
            if ($ShowOutput) {
                Write-Host "`nOutput:" -ForegroundColor Gray
                $output | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
            }
        } else {
            Write-Host "Test failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
            Write-Host "`nOutput:" -ForegroundColor Gray
            $output | ForEach-Object { Write-Host $_ -ForegroundColor Red }
        }
        
        return $LASTEXITCODE -eq 0
    } catch {
        Write-Error "Exception during test execution: $($_.Exception.Message)"
        return $false
    }
}

# Function to check logs
function Check-Logs {
    Write-Host "`n--- Checking Logs ---" -ForegroundColor Yellow
    
    if (Test-Path $LogDir) {
        $logFiles = Get-ChildItem $LogDir -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 3
        if ($logFiles) {
            Write-Host "Recent log files in $LogDir" -ForegroundColor Cyan
            foreach ($log in $logFiles) {
                Write-Host "  $($log.Name) - $($log.LastWriteTime)" -ForegroundColor Gray
            }
            Write-Host "`nTo view latest log: Get-Content '$($logFiles[0].FullName)' -Tail 20" -ForegroundColor Yellow
        } else {
            Write-Host "No log files found in $LogDir" -ForegroundColor Gray
        }
    } else {
        Write-Host "Log directory not found: $LogDir" -ForegroundColor Gray
    }
}

# Main execution
try {
    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        exit 1
    }
    
    # Setup environment variables
    if (-not (Setup-Environment)) {
        Write-Host "`nEnvironment setup failed. Cannot continue with wrong Python interpreter." -ForegroundColor Red
        exit 1
    }
    
    # Install adaptor (unless skipped)
    if (-not $SkipInstall) {
        if (-not (Install-Adaptor)) {
            exit 1
        }
    } else {
        Write-Host "`n--- Skipping Installation ---" -ForegroundColor Yellow
    }
    
    # Build test command
    $testCommand = Build-TestCommand
    if (-not $testCommand) {
        exit 1
    }
    
    # Run test
    $success = Run-Test -TestCommand $testCommand
    
    # Check logs regardless of success/failure
    Check-Logs
    
    if ($success) {
        Write-Host "`nTest completed successfully!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "`nTest failed. Check the output above and logs for details." -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Error "Unexpected error: $($_.Exception.Message)"
    exit 1
}