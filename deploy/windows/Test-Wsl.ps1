<# .SYNOPSIS Read-only selected WSL distribution preflight; does not apply configuration. #>
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$Distribution,
 [ValidateSet('PRIMARY','PUBLIC_REPLACEMENT')][string]$InstallationSlot='PRIMARY',
 [ValidatePattern('^$|^[a-z_][a-z0-9_-]*$')][string]$LinuxAccount=''
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
$version=Get-CimInstance Win32_OperatingSystem
& $wsl --list --verbose
if ($LASTEXITCODE -ne 0) { throw 'Unable to inventory WSL distributions.' }
if ($InstallationSlot -eq 'PUBLIC_REPLACEMENT') {
 & $wsl --distribution $Distribution --user $LinuxAccount --exec /usr/bin/python3 -I -B /opt/allow-public/deploy/linux/check_public.py --config /opt/allow-public/deploy/instance.json
 if ($LASTEXITCODE -ne 0) { throw 'Public installation guard failed.' }
}
$check='set -eu; test "$(uname -m)" = x86_64; uname -r | grep -qi microsoft-standard-WSL2; test "$(ps -p 1 -o comm=)" = systemd; test -f /sys/fs/cgroup/cgroup.controllers; command -v java; command -v bwrap; command -v prlimit; /usr/bin/python3 -I -B -c "import sys; assert sys.version_info[:2] == (3,12)"; test -d /opt/allow; test ! -L /opt/allow; test "$(stat -c %a /opt/allow)" = 700; test "$(stat -c %u /opt/allow)" = "$(id -u)"; bwrap --unshare-user --unshare-pid --ro-bind / / --proc /proc --dev /dev /bin/true'
if ($InstallationSlot -eq 'PUBLIC_REPLACEMENT') { $check=$check.Replace('/opt/allow','/opt/allow-public') }
& $wsl --distribution $Distribution --user $LinuxAccount --exec /bin/sh -c $check
if ($LASTEXITCODE -ne 0) { throw 'Selected Linux prerequisites failed; do not weaken sandboxing.' }
$limits='set -eu; test "$(systemctl show allow.service -p MemoryHigh --value)" = 3221225472; test "$(systemctl show allow.service -p MemoryMax --value)" = 4294967296; test "$(systemctl show allow.service -p MemorySwapMax --value)" = 0; test "$(systemctl show allow.service -p TasksMax --value)" = 512; test "$(systemctl show allow.service -p CPUQuotaPerSecUSec --value)" = 4s'
if ($InstallationSlot -eq 'PUBLIC_REPLACEMENT') { $limits=$limits.Replace('allow.service','allow-public.service') }
& $wsl --distribution $Distribution --user root --exec /bin/sh -c $limits
if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect the explicit service resource configuration.' }
[pscustomobject]@{WindowsVersion=$version.Version; Distribution=$Distribution; InstallationSlot=$InstallationSlot; Unit=$unit; Status='PREREQUISITES_CHECKED'; NativeLoopback='OPEN'; WslEffectiveLimits='OPEN'; RebootRecovery='OPEN'} | ConvertTo-Json
