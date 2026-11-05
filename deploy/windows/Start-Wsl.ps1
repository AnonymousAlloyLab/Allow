<# .SYNOPSIS Foreground explicit selected-distribution supervisor; installs no task. #>
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$Distribution,
 [ValidateSet('PRIMARY','PUBLIC_REPLACEMENT')][string]$InstallationSlot='PRIMARY',
 [ValidatePattern('^$|^[a-z_][a-z0-9_-]*$')][string]$LinuxAccount='',
 [ValidateRange(1,10)][int]$MaximumAttempts=3
)
$ErrorActionPreference='Stop'
if ($InstallationSlot -eq 'PUBLIC_REPLACEMENT') {
 $account='allow-public'; $unit='allow-public.service'; $root='/opt/allow-public'
} else {
 $account='allow'; $unit='allow.service'; $root='/opt/allow'
}
if ($LinuxAccount -and $LinuxAccount -ne $account) { throw 'Account does not match the selected installation.' }
$LinuxAccount=$account
$wsl=(Get-Command wsl.exe -ErrorAction Stop).Source
$hash=[System.Security.Cryptography.SHA256]::Create()
$name=([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Distribution.ToUpperInvariant())))).Replace('-','')
$mutex=New-Object System.Threading.Mutex($false,"Global\AllowWsl-$name")
$locked=$false
$owned=$false
try {
 $locked=$mutex.WaitOne(0)
 if (-not $locked) { throw 'A supported supervisor already owns this distribution.' }
 $state=& $wsl --distribution $Distribution --user root --exec systemctl show $unit --property=ActiveState --value
 if ($LASTEXITCODE -ne 0 -or $state.Trim() -notin @('inactive','failed')) { throw 'Existing or uncertain service is not owned by this invocation.' }
 for ($attempt=1; $attempt -le $MaximumAttempts; $attempt++) {
  if ($InstallationSlot -eq 'PUBLIC_REPLACEMENT') {
   & $wsl --distribution $Distribution --user $LinuxAccount --exec /usr/bin/python3 -I -B /opt/allow-public/deploy/linux/check_public.py --config /opt/allow-public/deploy/instance.json
   if ($LASTEXITCODE -ne 0) { throw 'Public guard failed before the service start transaction.' }
  }
  & $wsl --distribution $Distribution --user root --exec systemctl start $unit
  if ($LASTEXITCODE -ne 0) { throw 'Selected service failed to start.' }
  $owned=$true
  & $wsl --distribution $Distribution --user $LinuxAccount --exec /usr/bin/python3 -I -B "$root/deploy/linux/wsl_keepalive.py" --installation-slot $InstallationSlot
  if ($LASTEXITCODE -eq 0) { break }
  if ($attempt -eq $MaximumAttempts) { throw 'Bounded supervisor restart budget exhausted.' }
  Start-Sleep -Seconds ([Math]::Min(30,5*$attempt))
 }
} finally {
 try {
  if ($owned) {
   & $wsl --distribution $Distribution --user root --exec systemctl stop $unit
   if ($LASTEXITCODE -ne 0) { Write-Error 'Owned service stop uncertain; inspect target before retry.' }
  }
 } finally {
  try { if ($locked) { $mutex.ReleaseMutex() } }
  finally {
   try { $mutex.Dispose() }
   finally { $hash.Dispose() }
  }
 }
}
