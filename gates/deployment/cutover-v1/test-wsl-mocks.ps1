<# Portable orchestration fixtures; no Windows/WSL service is contacted. #>
$ErrorActionPreference='Stop'
$global:wslCalls=@();$global:mutexNames=@();$global:wslActive=$false
$global:guardCount=0;$global:guardFailAt=0;$global:keepaliveFail=$false;$global:stopFail=$false
function Get-Command { param($Name,$ErrorAction) [pscustomobject]@{Source='Invoke-FakeWsl'} }
function Get-CimInstance { param($ClassName) [pscustomobject]@{Version='10.0.fixture'} }
function Start-Sleep { param($Seconds) }
function New-Object {
 param($TypeName,[Parameter(ValueFromRemainingArguments=$true)]$ConstructorArgs)
 if ($TypeName -ne 'System.Threading.Mutex') { throw 'Unexpected mocked constructor.' }
 $global:mutexNames+=,$ConstructorArgs[1]
 [System.Threading.Mutex]::new($false,[string]$ConstructorArgs[1])
}
function Invoke-FakeWsl {
 $global:wslCalls+=,@($args);$global:LASTEXITCODE=0
 if ($args -contains '/opt/allow-public/deploy/linux/check_public.py') {
  $global:guardCount++
  if ($global:guardFailAt -eq $global:guardCount) { $global:LASTEXITCODE=1 }
 }
 if ($global:keepaliveFail -and (($args -contains '/opt/allow-public/deploy/linux/wsl_keepalive.py') -or ($args -contains '/opt/allow/deploy/linux/wsl_keepalive.py'))) { $global:LASTEXITCODE=1 }
 if ($global:stopFail -and $args -contains 'systemctl' -and $args -contains 'stop') { $global:LASTEXITCODE=1 }
 if ($args -contains '--property=ActiveState') {
  if ($global:wslActive) { 'active' } else { 'inactive' }
 }
}
function Reset-Fixture {
 $global:wslCalls=@();$global:wslActive=$false;$global:guardCount=0
 $global:guardFailAt=0;$global:keepaliveFail=$false;$global:stopFail=$false
}
function Assert-PublicCalls {
 foreach($call in $global:wslCalls) {
  if ($call[0] -ne '--distribution' -or $call[1] -ne 'Ubuntu Explicit') { throw 'Lost exact distro argument.' }
  if ($call -contains 'allow.service' -or $call -contains '--shutdown' -or $call -contains '--terminate') { throw 'Legacy/global lifecycle mutation.' }
  if ($call -contains 'systemctl' -and $call -notcontains 'allow-public.service') { throw 'Wrong selected unit.' }
 }
}
Reset-Fixture
& ./deploy/windows/Start-Wsl.ps1 -Distribution 'Ubuntu Explicit' -MaximumAttempts 1
if ($global:wslCalls.Count -ne 4) { throw 'PRIMARY default sequence changed.' }
$primaryMutex=$global:mutexNames[-1]
Reset-Fixture
& ./deploy/windows/Start-Wsl.ps1 -Distribution 'Ubuntu Explicit' -InstallationSlot PUBLIC_REPLACEMENT -MaximumAttempts 1
Assert-PublicCalls
if ($global:wslCalls.Count -ne 5) { throw 'Expected public state/guard/start/observer/stop.' }
if ($global:mutexNames[-1] -ne $primaryMutex) { throw 'Slots do not share a distribution mutex.' }
if ($global:wslCalls[1] -notcontains '/opt/allow-public/deploy/linux/check_public.py' -or $global:wslCalls[1] -notcontains 'allow-public') { throw 'Missing guard before start.' }
if ($global:wslCalls[2] -notcontains 'start' -or $global:wslCalls[3] -notcontains 'PUBLIC_REPLACEMENT') { throw 'Wrong replacement dispatch.' }
Reset-Fixture;$global:guardFailAt=1;$rejected=$false
try { & ./deploy/windows/Start-Wsl.ps1 -Distribution 'Ubuntu Explicit' -InstallationSlot PUBLIC_REPLACEMENT } catch { $rejected=$true }
if (-not $rejected -or $global:wslCalls.Count -ne 2) { throw 'Guard denial entered start/stop transaction.' }
Assert-PublicCalls
Reset-Fixture;$global:wslActive=$true;$rejected=$false
try { & ./deploy/windows/Start-Wsl.ps1 -Distribution 'Ubuntu Explicit' -InstallationSlot PUBLIC_REPLACEMENT } catch { $rejected=$true }
if (-not $rejected -or $global:wslCalls.Count -ne 1) { throw 'Preexisting ownership mutated.' }
Reset-Fixture;$global:keepaliveFail=$true;$global:guardFailAt=2;$rejected=$false
try { & ./deploy/windows/Start-Wsl.ps1 -Distribution 'Ubuntu Explicit' -InstallationSlot PUBLIC_REPLACEMENT -MaximumAttempts 2 } catch { $rejected=$true }
Assert-PublicCalls
if (-not $rejected -or $global:wslCalls.Count -ne 6 -or $global:guardCount -ne 2) { throw 'Retry guard or selected cleanup missing.' }
if ($global:wslCalls[-1] -notcontains 'stop') { throw 'Owned replacement was not stopped.' }
Reset-Fixture;$global:stopFail=$true;$rejected=$false
try { & ./deploy/windows/Start-Wsl.ps1 -Distribution 'Ubuntu Explicit' -InstallationSlot PUBLIC_REPLACEMENT -MaximumAttempts 1 } catch { $rejected=$true }
Assert-PublicCalls
if (-not $rejected -or $global:wslCalls.Count -ne 5) { throw 'Owned stop failure was hidden.' }
$mutexName=$global:mutexNames[-1]
if ($mutexName -notmatch '^Global\\AllowWsl-[A-F0-9]{64}$') { throw 'Expected an actual named mutex.' }
$child='$m=[System.Threading.Mutex]::new($false,"' + $mutexName + '");try{$ok=$m.WaitOne(1000);if(-not $ok){exit 1};$m.ReleaseMutex()}finally{$m.Dispose()}'
$encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($child))
& ([Environment]::ProcessPath) -NoProfile -EncodedCommand $encoded
if ($LASTEXITCODE -ne 0) { throw 'Failed stop leaked the supported supervisor mutex.' }
foreach($script in @('./deploy/windows/Start-Wsl.ps1','./deploy/windows/Test-Wsl.ps1')) {
 Reset-Fixture;$rejected=$false
 try { & $script -Distribution 'Ubuntu Explicit' -InstallationSlot PUBLIC_REPLACEMENT -LinuxAccount allow } catch { $rejected=$true }
 if (-not $rejected -or $global:wslCalls.Count) { throw 'Mixed account reached WSL.' }
}
foreach($script in @('./deploy/windows/Start-Wsl.ps1','./deploy/windows/Test-Wsl.ps1')) {
 Reset-Fixture;$rejected=$false
 try { & $script -Distribution 'Ubuntu Explicit' -InstallationSlot UNKNOWN } catch { $rejected=$true }
 if (-not $rejected -or $global:wslCalls.Count) { throw 'Unknown selector reached WSL.' }
}
Reset-Fixture
$preflight=& ./deploy/windows/Test-Wsl.ps1 -Distribution 'Ubuntu Explicit' -InstallationSlot PUBLIC_REPLACEMENT | ConvertFrom-Json
if ($preflight.InstallationSlot -ne 'PUBLIC_REPLACEMENT' -or $preflight.NativeLoopback -ne 'OPEN') { throw 'Native acceptance overstated.' }
$selected=$global:wslCalls | Where-Object { $_ -contains '--distribution' }
foreach($call in $selected) {
 if ($call -contains 'allow') { throw 'Replacement preflight used legacy account.' }
 if (($call -join ' ') -match 'systemctl show allow\.service') { throw 'Replacement limits inspected legacy unit.' }
}
if ($global:guardCount -ne 1) { throw 'Preflight omitted public guard.' }
[pscustomobject]@{status='PASS';checks=@('primary-default','replacement-fixed-tuple','shared-distribution-mutex','guard-before-start','guard-denial-no-manager-effects','retry-rechecks-guard','owned-public-only-cleanup','failed-stop-propagates-and-cross-process-mutex-released','preexisting-owner-refused','mixed-account-refused-before-wsl','unknown-selector-before-wsl','selected-preflight-native-open');nativeWindows='OPEN'} | ConvertTo-Json
