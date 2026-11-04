<#
.SYNOPSIS
Runs the dedicated SSH forward in the foreground; never opens a public local port.
.DESCRIPTION
Provision and verify the host-key file out of band. This script does not accept new
host keys, store credentials, install a task, or restart the Linux application.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9.-]*$')][string]$LinuxHost,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z_][a-z0-9_-]*$')][string]$SshUser,
    [Parameter(Mandatory=$true)][string]$IdentityFile,
    [Parameter(Mandatory=$true)][string]$KnownHostsFile,
    [ValidateRange(1024,65535)][int]$TunnelPort=18081,
    [ValidateRange(1024,65535)][int]$BackendPort=8080
)
$ErrorActionPreference = 'Stop'
$key = (Resolve-Path -LiteralPath $IdentityFile).Path
$hostsFile = (Resolve-Path -LiteralPath $KnownHostsFile).Path
if ($hostsFile -match '\s') { throw 'Use a known-hosts file path without whitespace, for example C:\AllowSecrets\known_hosts.' }
$hostsFile = $hostsFile.Replace('\', '/')
$ssh = (Get-Command ssh.exe -ErrorAction Stop).Source
$options = @('-F', 'none', '-N', '-T', '-L', "127.0.0.1:${TunnelPort}:127.0.0.1:${BackendPort}",
    '-i', $key, '-o', "UserKnownHostsFile=$hostsFile", '-o', 'StrictHostKeyChecking=yes',
    '-o', 'GlobalKnownHostsFile=none', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3', '-o', 'ConnectTimeout=10',
    '--', "${SshUser}@${LinuxHost}")
& $ssh @options
exit $LASTEXITCODE
