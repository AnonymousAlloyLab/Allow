$ErrorActionPreference='Stop'
$global:wslCalls=@()
$global:wslActive=$false
$global:wslFailKeepalive=$false
function Get-Command { param($Name,$ErrorAction) [pscustomobject]@{Source='Invoke-FakeWsl'} }
function Invoke-FakeWsl {
 $global:wslCalls+=,@($args)
 $global:LASTEXITCODE=0
 if ($global:wslFailKeepalive -and $args -contains '/opt/allow/deploy/linux/wsl_keepalive.py') { $global:LASTEXITCODE=1 }
 if ($args -contains '--property=ActiveState') {
  if ($global:wslActive) { 'active' } else { 'inactive' }
 }
}
& ./deploy/windows/Start-Wsl.ps1 -Distribution 'Ubuntu Explicit' -MaximumAttempts 1
if ($global:wslCalls.Count -ne 4) { throw 'Expected state/start/keepalive/stop.' }
foreach($call in $global:wslCalls) {
 if ($call[0] -ne '--distribution' -or $call[1] -ne 'Ubuntu Explicit') { throw 'Distribution argument boundary lost.' }
 if ($call -contains '--shutdown' -or $call -contains '--terminate') { throw 'Global teardown forbidden.' }
}
$global:wslCalls=@();$global:wslActive=$true;$rejected=$false
try { & ./deploy/windows/Start-Wsl.ps1 -Distribution 'Ubuntu Explicit' -MaximumAttempts 1 } catch { $rejected=$true }
if (-not $rejected -or $global:wslCalls.Count -ne 1) { throw 'Preexisting active service mutated.' }
$global:wslCalls=@();$global:wslActive=$false;$global:wslFailKeepalive=$true;$rejected=$false
try { & ./deploy/windows/Start-Wsl.ps1 -Distribution 'Ubuntu Explicit' -MaximumAttempts 1 } catch { $rejected=$true }
if (-not $rejected -or $global:wslCalls.Count -ne 4) { throw 'Restart budget or owned cleanup failed.' }
[pscustomobject]@{status='PASS';checks=@('argument-boundaries','owned-start-keepalive-stop','preexisting-owner-rejected','bounded-restart-and-cleanup');nativeWindows='OPEN'} | ConvertTo-Json
