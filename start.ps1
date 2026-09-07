<#
start.ps1
Creates a venv (if missing), installs requirements, and starts the app with waitress.
Run this from the project root or double-click in Explorer (may require adjusting ExecutionPolicy).
#>

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

Write-Output "Starting Grant Research Agent..."

if (-not (Test-Path ".venv")) {
    Write-Output "Creating virtual environment .venv..."
    python -m venv .venv
}

Write-Output "Activating virtual environment..."
. .\.venv\Scripts\Activate.ps1

Write-Output "Installing requirements (if needed)..."
python -m pip install -r requirements.txt

Write-Output "Launching app (background)..."
# Start the server in a background process using the venv's python
Start-Process -FilePath "python" -ArgumentList "-m", "waitress", "--listen=0.0.0.0:8080", "app:app" -WindowStyle Hidden

Write-Output "Grant Research Agent started on port 8080. Visit http://localhost:8080/"
