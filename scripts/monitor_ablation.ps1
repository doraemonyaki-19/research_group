$targetProcess = "finetune_timesfm.py"
Write-Host "Monitoring for $targetProcess to finish. Will check every 30 minutes..."
while ($true) {
    $processes = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match $targetProcess }
    if (-not $processes) {
        Import-Module BurntToast -ErrorAction SilentlyContinue
        New-BurntToastNotification -Text "Ablation Run Finished!", "The TimesFM finetuning process has completed." -ErrorAction SilentlyContinue
        Write-Host "Process finished."
        break
    }
    Write-Host "Process is still running. Sleeping for 30 minutes..."
    Start-Sleep -Seconds 1800
}
