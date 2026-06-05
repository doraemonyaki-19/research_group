<#
.SYNOPSIS
  Frees disk space by removing model weights from all but the best checkpoint.
  Preserves args.json, history.json, and final_val_metric.json in every run dir.

.DESCRIPTION
  For each checkpoint directory under artifacts/:
    - Reads final_val_metric.json to get best_val_metric
    - Keeps model.safetensors only in the single best run (lowest val_loss)
    - Deletes model.safetensors from all other completed runs
    - Never touches args.json, history.json, final_val_metric.json
    - Skips in-progress runs (no final_val_metric.json)

.PARAMETER ArtifactsDir
  Root artifacts directory. Default: research_group/artifacts

.PARAMETER DryRun
  Print what would be deleted without actually deleting.
#>
param(
    [string]$ArtifactsDir = "$PSScriptRoot\..\artifacts",
    [switch]$DryRun
)

$ArtifactsDir = Resolve-Path $ArtifactsDir

# Collect all completed runs (have final_val_metric.json and model.safetensors)
$runs = Get-ChildItem $ArtifactsDir -Recurse -Filter "final_val_metric.json" | ForEach-Object {
    $runDir = $_.Directory
    $weights = Join-Path $runDir "best\model.safetensors"
    if (Test-Path $weights) {
        $metric = (Get-Content $_.FullName | ConvertFrom-Json).best_val_metric
        [PSCustomObject]@{
            RunDir    = $runDir.FullName
            Weights   = $weights
            ValLoss   = [double]$metric
            RelPath   = $runDir.FullName -replace [regex]::Escape($ArtifactsDir.Path + "\"), ""
        }
    }
} | Where-Object { $_ -ne $null } | Sort-Object ValLoss

if ($runs.Count -eq 0) {
    Write-Host "No completed checkpoints found."
    exit 0
}

$best = $runs[0]
Write-Host "Best checkpoint: $($best.RelPath) (val_loss=$($best.ValLoss))"
Write-Host ""

foreach ($run in $runs) {
    $sizeMB = [math]::Round((Get-Item $run.Weights).Length / 1MB, 0)
    if ($run.RunDir -eq $best.RunDir) {
        Write-Host "KEEP   $($run.RelPath) (val_loss=$($run.ValLoss), ${sizeMB}MB)"
    } else {
        if ($DryRun) {
            Write-Host "DELETE $($run.RelPath)\best\model.safetensors (val_loss=$($run.ValLoss), ${sizeMB}MB) [dry-run]"
        } else {
            Remove-Item $run.Weights -Force
            # Remove empty best/ dir
            $bestDir = Split-Path $run.Weights -Parent
            if (-not (Get-ChildItem $bestDir)) { Remove-Item $bestDir -Force }
            Write-Host "DELETED $($run.RelPath)\best\model.safetensors (val_loss=$($run.ValLoss), ${sizeMB}MB)"
        }
    }
}

$totalFreed = ($runs | Where-Object { $_.RunDir -ne $best.RunDir } | ForEach-Object {
    if (Test-Path $_.Weights) { (Get-Item $_.Weights).Length } else { 882MB }
} | Measure-Object -Sum).Sum / 1GB

if (-not $DryRun) {
    Write-Host "`nDone. Freed ~$([math]::Round($totalFreed, 1)) GB. Metadata preserved in all run dirs."
}
