#!/usr/bin/env pwsh
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

$ErrorActionPreference = "Stop"

if (-not (Test-Path "wheels")) {
    New-Item -ItemType Directory -Path "wheels" | Out-Null
}
Remove-Item "wheels\*.whl" -Force -ErrorAction SilentlyContinue

$repos = @("../openjd-adaptor-runtime-for-python", "../deadline-cloud", "../deadline-cloud-for-3ds-max")

foreach ($dir in $repos) {
    Write-Host "Building $dir..."
    Push-Location $dir
    try {
        hatch build
        Move-Item "dist\*.whl" "../deadline-cloud-for-3ds-max/wheels/" -Force
    } finally {
        Pop-Location
    }
}
