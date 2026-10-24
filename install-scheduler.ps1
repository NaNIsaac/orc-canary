param([switch]$Install, [string]$TaskName='ORC Canary Plan', [string]$At='03:00')
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'canary.py'
$python = (Get-Command python -ErrorAction Stop).Source
$workdir = $PSScriptRoot
$taskCommand = "`"$python`" `"$script`" plan"
Write-Host "Proposed weekly task: $TaskName; Sunday $At; command: $taskCommand"
if (-not $Install) { Write-Host 'Dry-run only. Use -Install after reviewing.'; return }
$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`" plan" -WorkingDirectory $workdir
$time = [datetime]::ParseExact($At,'HH:mm',[cultureinfo]::InvariantCulture)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $time
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'External ORC quality probe planning, no dispatch or changes' -Force | Out-Null
Write-Host "Installed $TaskName. Runs plan only; it never sends to ORC automatically."
