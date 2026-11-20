# Run once from PowerShell as your regular Windows user, after a manual test.
[CmdletBinding()]
param(
    [ValidateSet('youtube', 'facebook', 'both')][string]$Target = 'youtube',
    [ValidatePattern('^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')][string]$At = '18:00',
    [switch]$Voice
)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Install the project .venv first (see README).' }
$targets = if ($Target -eq 'both') { 'youtube facebook' } else { $Target }
if ($targets.Contains('youtube') -and !(Test-Path (Join-Path $PSScriptRoot 'secrets\youtube.token.json'))) {
    throw 'Run publish.py authorize-youtube first.'
}
if ($targets.Contains('facebook') -and (!([Environment]::GetEnvironmentVariable('FB_PAGE_ID','User')) -or !([Environment]::GetEnvironmentVariable('FB_PAGE_TOKEN','User')))) {
    throw 'Set FB_PAGE_ID and FB_PAGE_TOKEN in user environment variables first.'
}
$arguments = "studio.py --publish $targets"
if ($Voice) { $arguments += ' --voice' }
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($At,'HH:mm',[cultureinfo]::InvariantCulture))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName 'ARARA Studio' -Action $action -Trigger $trigger -Settings $settings -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -Force
