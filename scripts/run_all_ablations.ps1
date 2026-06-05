<#
.SYNOPSIS
  Phase 3 ablation driver — interleaves seeds across configs, resumes from
  partial runs, tees a persistent log, and pings on completion.

.DESCRIPTION
  Iterates seed-major (1, 2, 3, ...) across configs (B2, V1, V2-Full).
  Surfaces per-config bugs early instead of after burning 2/3 of the budget.

  Resumability: if results/<config>/<region>/seed_<N>_*/run_data.json already
  exists, that cell is skipped. Crashes / kills / power outages are recoverable
  by simply re-running the script.

  Logging: all stdout + stderr is teed to scripts/logs/ablation_<timestamp>.log
  for forensic inspection after multi-day runs.

.PARAMETER Pilot
  Run a single seed per config with --max-turns 5 (one full evaluator cycle is
  9 turns; 5 is enough to surface harness bugs without burning real cost).
  Use this BEFORE committing to the full multi-seed budget.

.PARAMETER Configs
  Configurations to run. Default: B2, V1, V2-Full (the H2 comparison subset
  per EVALUATION_PROTOCOL.md). Override for partial reruns.

.PARAMETER Seeds
  Number of seeds per config. Default: 7 (matches T1 in EVALUATION_PROTOCOL.md §5).

.PARAMETER Region
  TimesFM region. Default: us.

.PARAMETER MaxTurns
  Per-run turn cap. Default: 27 (matches the protocol's V2 budget).

.EXAMPLE
  $env:ANTHROPIC_API_KEY = "sk-..."
  ./scripts/run_all_ablations.ps1 -Pilot
  # then, if pilot looks good:
  ./scripts/run_all_ablations.ps1
#>
param(
    [switch]$Pilot,
    [switch]$Force,
    [string[]]$Configs = @("B2", "V1", "V2-Full"),
    [int]$Seeds = 7,
    [string]$Region = "us",
    [int]$MaxTurns = 160,
    [int]$RunTimeoutSeconds = 0,
    [string]$ApiKey,
    # Default model used by all configs unless a per-config override is set.
    # The Python harness validates the name against the chosen provider.
    [string]$Model = "gemini-2.5-pro",
    # Per-config model overrides. V1 in particular benefits from a stronger
    # model: it has no supervisors to compensate for weak agentic behavior
    # (the May 2026 pilot showed Gemini Flash silently no-op'ing in V1).
    [string]$B2Model = "gemini-2.5-pro",
    [string]$V1Model = "gemini-2.5-pro",
    [string]$V2Model = "gemini-2.5-pro",
    # V2 supervisors get their own model — defaults to gemini-2.5-flash so
    # the per-supervisor-call cost is much lower than the researcher /
    # evaluator model. Set equal to -V2Model to disable the per-agent split.
    [string]$SupervisorModel = "gemini-2.5-flash",
    # Official seeds from EVALUATION_PROTOCOL.md §5
    [int[]]$OfficialSeeds = @(42, 137, 271, 314, 1729, 2718, 3141)
)

if ($Configs.Count -eq 1 -and $Configs[0] -match ",") {
    $Configs = $Configs[0] -split "," | ForEach-Object { $_.Trim() }
}

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# ---------- Pilot mode overrides ----------
if ($Pilot) {
    $Seeds = 1
    $Configs = @("B2", "V1", "V2-Full")
    $MaxTurns = 5
    if ($RunTimeoutSeconds -eq 0) { $RunTimeoutSeconds = 14400 }  # 4 hours
    Write-Host "[PILOT MODE] Seed 1 B2/V1/V2-Full, max_turns=5, run_timeout=${RunTimeoutSeconds}s" -ForegroundColor Magenta
}
if ($RunTimeoutSeconds -eq 0) { $RunTimeoutSeconds = 129600 }  # 36 hours default

# ---------- Logging ----------
$logDir = Join-Path $repoRoot "scripts/logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$pilotPrefix = if ($Pilot) { "pilot_" } else { "" }
$logFile = Join-Path $logDir ("ablation_" + $pilotPrefix + "$timestamp.log")
Write-Host "Log: $logFile" -ForegroundColor DarkGray

# ---------- Banner ----------
function Write-Banner {
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host " ResearchGroup Phase 3 Ablation Bench" -ForegroundColor Cyan
    Write-Host " Configs: $($Configs -join ', ')" -ForegroundColor Cyan
    Write-Host " Seeds:   $Seeds  ($($Configs.Count * $Seeds) total runs)" -ForegroundColor Cyan
    Write-Host " Region:  $Region   MaxTurns: $MaxTurns" -ForegroundColor Cyan
    Write-Host " Order:   seed-major (interleaved)" -ForegroundColor Cyan
    Write-Host " Pilot:   $Pilot" -ForegroundColor Cyan
    Write-Host "===============================================" -ForegroundColor Cyan
}
Write-Banner | Tee-Object -FilePath $logFile -Append

# ---------- API key resolution ----------
# The Python harness handles auth precedence: --api-key arg > ANTHROPIC_API_KEY
# env var > .env file in repo root. This pre-check just warns if none of those
# is visible from PowerShell — the Python script will produce a precise error
# if the key truly can't be resolved.
$envFilePath = Join-Path $repoRoot ".env"
$keyVisible = $ApiKey -or $env:ANTHROPIC_API_KEY -or (Test-Path $envFilePath)
if (-not $keyVisible) {
    Write-Host "Warning: no API key visible to this script." -ForegroundColor Yellow
    Write-Host "  Provide one via:" -ForegroundColor Yellow
    Write-Host "    -ApiKey sk-...                     (script parameter)" -ForegroundColor Yellow
    Write-Host "    `$env:ANTHROPIC_API_KEY = `"sk-...`"  (environment variable)" -ForegroundColor Yellow
    Write-Host "    .env file at $envFilePath           (auto-loaded by Python)" -ForegroundColor Yellow
    Write-Host "Continuing — Python will fail fast if the key truly can't be found." -ForegroundColor DarkGray
}

# ---------- Live-tailing helper ----------
# Reads any new bytes appended to $Path since $StartPos and tees them to
# $LogFile. Returns the new file position. Robust against the file being
# locked by python's stdout writer: opens with FileShare.ReadWrite.
function Drain-NewContent {
    param(
        [string]$Path,
        [long]$StartPos,
        [string]$LogFile
    )
    if (-not (Test-Path $Path)) { return $StartPos }
    $fs = $null
    $reader = $null
    try {
        $fs = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )
        $fileLen = $fs.Length
        if ($fileLen -le $StartPos) { return $StartPos }
        $fs.Position = $StartPos
        $reader = New-Object System.IO.StreamReader $fs
        $newContent = $reader.ReadToEnd()
        # Capture the new position BEFORE the reader's Dispose closes the
        # underlying FileStream — otherwise $fs.Position throws
        # ObjectDisposedException and the catch returns the old StartPos,
        # causing the next poll to re-read everything from byte 0.
        $newPos = $fileLen
        if ($newContent) {
            Add-Content -Path $LogFile -Value $newContent -NoNewline
            Write-Host -NoNewline $newContent
        }
        return $newPos
    } catch {
        return $StartPos
    } finally {
        if ($reader) { $reader.Dispose() }
        if ($fs)     { $fs.Dispose() }
    }
}

# ---------- Resumability helper ----------
function Test-CellComplete {
    param([string]$Config, [int]$Seed, [string]$Model)
    # The Python harness writes to results/<config>/<model>/<region>/seed_<N>_*/
    # where "/" in model names is replaced with "_".
    $modelSafe = $Model -replace "[/\\]", "_"
    $cellDir = Join-Path "results" (Join-Path $Config (Join-Path $modelSafe $Region))
    if (-not (Test-Path $cellDir)) { return $false }
    $seedDirs = Get-ChildItem -Path $cellDir -Directory -Filter "seed_${Seed}_*" -ErrorAction SilentlyContinue
    foreach ($d in $seedDirs) {
        if (Test-Path (Join-Path $d.FullName "run_data.json")) { return $true }
    }
    return $false
}

# ---------- Main loop: seed-major (interleaved) ----------
$totalRuns = $Configs.Count * $Seeds
$runIdx = 0
$failedRuns = @()
$startTime = Get-Date

for ($seedIdx = 0; $seedIdx -lt $Seeds; $seedIdx++) {
    $seed = if ($Pilot) {1} else { $OfficialSeeds[$seedIdx] }
    foreach ($config in $Configs) {
        $runIdx++
        $runHeader = "[run $runIdx/$totalRuns] config=$config seed=$seed"

        # Resolve effective model up front so resumability check and run use the same value.
        $effectiveModel = switch ($config) {
            "B2"          { if ($B2Model) { $B2Model } else { $Model } }
            "V1"          { if ($V1Model) { $V1Model } else { $Model } }
            "V2-Full"     { if ($V2Model) { $V2Model } else { $Model } }
            "V2-noSkills" { if ($V2Model) { $V2Model } else { $Model } }
            default       { $Model }
        }
        if (Test-CellComplete -Config $config -Seed $seed -Model $effectiveModel) {
            if ($Force) {
                # Delete stale run_data.json so the cell is re-run
                $modelSafe = $effectiveModel -replace "[/\\]", "_"
                $cellDir = Join-Path "results" (Join-Path $config (Join-Path $modelSafe $Region))
                $seedDirs = Get-ChildItem -Path $cellDir -Directory -Filter "seed_${seed}_*" -ErrorAction SilentlyContinue
                foreach ($d in $seedDirs) {
                    $rdp = Join-Path $d.FullName "run_data.json"
                    if (Test-Path $rdp) {
                        Remove-Item $rdp -Force
                        "  [FORCE] Removed $rdp" | Tee-Object -FilePath $logFile -Append
                    }
                }
            } else {
                "$runHeader  SKIP (run_data.json exists)" | Tee-Object -FilePath $logFile -Append
                continue
            }
        }

        "`n>>> $runHeader  starting at $(Get-Date -Format 'HH:mm:ss')" | Tee-Object -FilePath $logFile -Append

        # Per-config max_turns per EVALUATION_PROTOCOL.md §5:
        #   V1 = 54 (twice V2; equates per-turn budget), V2 family = 18,
        #   B1/B2 = 27. Pilot (-Pilot flag) overrides to max_turns=5 for
        #   all configs before we get here, so this only fires on full runs.
        $effectiveMaxTurns = if ($Pilot) { $MaxTurns } else {
            switch ($config) {
                "V1"          { 80 }
                "V2-Full"     { 40 }
                "V2-noSkills" { 40 }
                default       { $MaxTurns }  # B2, B0, B1 use the global default (27)
            }
        }
        $pythonWallCap = [int]($RunTimeoutSeconds * 0.95)
        if ($config -eq "B0") {
            $argsList = @(
                "benchmarks/b0_grid_search.py",
                "--region", $Region,
                "--num-trials", (if ($Pilot) { 5 } else { 18 }),
                "--seed", "$seed",
                "--out-dir", (Join-Path "results/B0" (Join-Path $Region "seed_${seed}_$timestamp"))
            )
        } else {
            $argsList = @(
                "benchmarks/run_ablation.py",
                "--config", $config,
                "--seeds", "1",
                "--start-seed", "$seed",
                "--region", $Region,
                "--max-turns", "$effectiveMaxTurns",
                "--max-wall-seconds", "$pythonWallCap",
                "--model", $effectiveModel,
                "--supervisor-model", $SupervisorModel,
                "--task-context", (Join-Path $repoRoot "research_group_timesfm_expt.md"),
                "--quiet",
                "--json-only"
            )
            if ($ApiKey) {
                $argsList += @("--api-key", $ApiKey)
            }
        }

        # Launch python via Start-Process so we get a process handle for the
        # whole tree. The previous Start-Job + Start-Sleep approach was unreliable:
        # PowerShell Jobs running inside background-task harnesses can be subject
        # to power throttling that extends Sleep indefinitely, and a fully
        # asleep watchdog Job that has accumulated <1s CPU after >5h is exactly
        # what we observed in pilot run 20260507_082453. Diagnostic notes:
        # artifacts/ablation_hang_diagnostic_may2026.md.
        $runStart = Get-Date
        $tempOut = [IO.Path]::GetTempFileName()
        $tempErr = [IO.Path]::GetTempFileName()
        $pyProc = Start-Process -FilePath python `
                                -ArgumentList $argsList `
                                -WorkingDirectory $repoRoot `
                                -RedirectStandardOutput $tempOut `
                                -RedirectStandardError $tempErr `
                                -PassThru -NoNewWindow

        # Poll every 5s: drain new temp-file content to the run log (live tailing
        # without a parallel Job), and check the wall-clock cap. This keeps the
        # whole watchdog logic in one runspace — no Start-Job, no Start-Sleep.
        $outPos = 0L
        $errPos = 0L
        $timedOut = $false
        while (-not $pyProc.HasExited) {
            $stillRunning = -not $pyProc.WaitForExit(5000)
            $outPos = Drain-NewContent -Path $tempOut -StartPos $outPos -LogFile $logFile
            $errPos = Drain-NewContent -Path $tempErr -StartPos $errPos -LogFile $logFile
            if ($stillRunning) {
                $elapsed = ((Get-Date) - $runStart).TotalSeconds
                if ($elapsed -gt $RunTimeoutSeconds) {
                    "TIMEOUT: $runHeader exceeded ${RunTimeoutSeconds}s — killing process tree" | Tee-Object -FilePath $logFile -Append
                    try { $pyProc.Kill($true) } catch { try { $pyProc.Kill() } catch {} }
                    $pyProc.WaitForExit() | Out-Null
                    $timedOut = $true
                    break
                }
            }
        }
        # Final drain after exit.
        $outPos = Drain-NewContent -Path $tempOut -StartPos $outPos -LogFile $logFile
        $errPos = Drain-NewContent -Path $tempErr -StartPos $errPos -LogFile $logFile

        if ($timedOut) {
            $exit = -1
        } else {
            # WaitForExit() with no timeout flushes any pending exit-state
            # population on the Process object — without this, ExitCode can
            # be $null immediately after the polling loop, and PowerShell's
            # `$null -ne 0` evaluates to true, falsely flagging a clean run
            # as ERROR.
            $pyProc.WaitForExit() | Out-Null
            $exit = $pyProc.ExitCode
            if ($null -eq $exit) { $exit = 0 }
        }
        Remove-Item $tempOut -ErrorAction SilentlyContinue
        Remove-Item $tempErr -ErrorAction SilentlyContinue

        if ($timedOut) {
            "TIMEOUT: $runHeader killed after ${RunTimeoutSeconds}s (outer watchdog)" | Tee-Object -FilePath $logFile -Append
            $failedRuns += "$runHeader (TIMEOUT)"
        } elseif ($exit -ne 0) {
            "ERROR: $runHeader exited $exit" | Tee-Object -FilePath $logFile -Append
            $failedRuns += $runHeader
        } else {
            "<<< $runHeader  done at $(Get-Date -Format 'HH:mm:ss')" | Tee-Object -FilePath $logFile -Append
        }
    }
}

# ---------- Summary ----------
$elapsed = (Get-Date) - $startTime
"" | Tee-Object -FilePath $logFile -Append
"===============================================" | Tee-Object -FilePath $logFile -Append
"Ablation bench complete." | Tee-Object -FilePath $logFile -Append
"Elapsed:   $($elapsed.ToString('d\.hh\:mm\:ss'))" | Tee-Object -FilePath $logFile -Append
"Total:     $totalRuns runs across $($Configs.Count) configs x $Seeds seeds" | Tee-Object -FilePath $logFile -Append
"Failed:    $($failedRuns.Count)" | Tee-Object -FilePath $logFile -Append
foreach ($f in $failedRuns) { "  - $f" | Tee-Object -FilePath $logFile -Append }
"Log:       $logFile" | Tee-Object -FilePath $logFile -Append
"===============================================" | Tee-Object -FilePath $logFile -Append

# ---------- Completion notification ----------
# Audible bell — works on most Windows terminals, harmless if not supported.
[console]::beep(1200, 300)
[console]::beep(800, 300)

# Try Windows toast if BurntToast is installed, otherwise fall back silently.
$toastModule = Get-Module -ListAvailable -Name BurntToast -ErrorAction SilentlyContinue
if ($toastModule) {
    try {
        Import-Module BurntToast -ErrorAction SilentlyContinue
        $msg = if ($failedRuns.Count -eq 0) {
            "Ablation complete: $totalRuns runs in $($elapsed.ToString('d\.hh\:mm'))"
        } else {
            "Ablation complete with $($failedRuns.Count) failures"
        }
        New-BurntToastNotification -Text "ResearchGroup Phase 3", $msg -ErrorAction SilentlyContinue
    } catch {
        # toast failure is non-fatal
    }
}

if ($failedRuns.Count -gt 0) { exit 1 }
