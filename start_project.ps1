<#
.SYNOPSIS
    Launcher for the HCL Predictive Maintenance Software Prototype.
.DESCRIPTION
    Checks virtual environment, database, and models, then opens separate
    PowerShell terminal windows for each service in the required sequence.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " HCL Predictive Maintenance -- Multi-Process Service Launcher" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Verify working directory
Set-Location -Path $ProjectRoot
Write-Host "[1/6] Workspace directory: $ProjectRoot" -ForegroundColor Green

# 2. Check virtual environment
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment Python not found at: $PythonExe" -ForegroundColor Red
    Write-Host "Please create the venv with: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}
Write-Host "[2/6] Virtualenv Python detected: $PythonExe" -ForegroundColor Green

# 3. Check database and model artifacts
$DbPath = Join-Path $ProjectRoot "data\machine_data.db"
if (-not (Test-Path $DbPath)) {
    Write-Host "[WARN] SQLite database not found at $DbPath. Creating parent directory." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path (Join-Path $ProjectRoot "data") -Force | Out-Null
} else {
    Write-Host "[3/6] SQLite database found: $DbPath" -ForegroundColor Green
}

$ModelPath = Join-Path $ProjectRoot "ml\models\condition_classifier.joblib"
if (-not (Test-Path $ModelPath)) {
    Write-Host "[WARN] Model artifacts missing. Running training pipeline..." -ForegroundColor Yellow
    & $PythonExe (Join-Path $ProjectRoot "ml\train_model.py")
} else {
    Write-Host "[4/6] Serialized ML models verified in ml/models/" -ForegroundColor Green
}

# 4. Check if services are already running on ports 8000 or 8501
$Port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
$Port8501 = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue

# 5. Launch Service Terminals

# Terminal 1: SQLite Storage Worker
Write-Host ""
Write-Host "Launching Terminal 1: SQLite Ingestor (layer3_storage.py)..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; Write-Host 'Starting SQLite Storage Ingestor...' -ForegroundColor Green; & '$PythonExe' layer3_storage.py"

Start-Sleep -Seconds 2

# Terminal 2: AI REST Service & Monitor
if ($Port8000) {
    Write-Host "Port 8000 already has a listener (PID $($Port8000.OwningProcess)). Skipping duplicate ml_service launch." -ForegroundColor Yellow
} else {
    Write-Host "Launching Terminal 2: AI Evaluation Microservice (ml_service.py)..." -ForegroundColor Cyan
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; Write-Host 'Starting AI Service on port 8000...' -ForegroundColor Green; & '$PythonExe' ml_service.py"
    Start-Sleep -Seconds 2
}

# Terminal 3: Telemetry Publisher
Write-Host "Launching Terminal 3: Synthetic Telemetry Publisher (publisher.py)..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; Write-Host 'Starting Telemetry Publisher...' -ForegroundColor Green; & '$PythonExe' publisher.py"

Start-Sleep -Seconds 2

# Terminal 4: Streamlit AI Dashboard
if ($Port8501) {
    Write-Host "Port 8501 already has a listener (PID $($Port8501.OwningProcess)). Skipping duplicate Streamlit launch." -ForegroundColor Yellow
} else {
    Write-Host "Launching Terminal 4: Streamlit AI Dashboard (layer5_ai_dashboard.py)..." -ForegroundColor Cyan
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; Write-Host 'Starting Streamlit Portal...' -ForegroundColor Green; & '$PythonExe' -m streamlit run layer5_ai_dashboard.py --server.port 8501"
}

# Optional Terminal 5: Node-RED
$NodeRedCmd = Get-Command "node-red.cmd" -ErrorAction SilentlyContinue
if ($null -eq $NodeRedCmd) {
    $NodeRedCmd = Get-Command "node-red" -ErrorAction SilentlyContinue
}

if ($NodeRedCmd) {
    $Port1880 = Get-NetTCPConnection -LocalPort 1880 -State Listen -ErrorAction SilentlyContinue
    if ($Port1880) {
        Write-Host "Port 1880 already has a listener. Node-RED is already active." -ForegroundColor Yellow
    } else {
        Write-Host "Launching Terminal 5: Node-RED Runtime..." -ForegroundColor Cyan
        Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Node-RED on port 1880...' -ForegroundColor Green; cmd.exe /c node-red.cmd"
    }
} else {
    Write-Host "[INFO] Node-RED command not found in current PATH. Skipping Node-RED auto-launch." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " All processes dispatched into dedicated terminal windows!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Active Local URLs:" -ForegroundColor White
Write-Host " - AI Service:       http://localhost:8000" -ForegroundColor Cyan
Write-Host " - AI Dashboard:     http://localhost:8501" -ForegroundColor Cyan
if ($NodeRedCmd) {
    Write-Host " - Node-RED Editor:  http://localhost:1880" -ForegroundColor Cyan
    Write-Host " - Node-RED Dash:    http://localhost:1880/dashboard/predictive-maintenance" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "To safely stop any service, click into its respective terminal window and press Ctrl+C." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
