<#
.SYNOPSIS
Creates a new dedicated HTTPS-only IIS site from a rendered web.config.
.DESCRIPTION
Run as administrator after reviewing ARR settings. Refuses existing site, app pool
or TLS binding. Does not install modules, import certificates, change global ARR
settings, add tokens, or configure the SSH tunnel. Use a dedicated IIS instance
when global ARR requirements conflict with another application's requirements.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z][A-Za-z0-9_-]*$')][string]$SiteName,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9.-]+$')][string]$HostName,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{40}$')][string]$CertificateThumbprint,
    [Parameter(Mandatory=$true)][string]$PhysicalPath,
    [ValidateRange(1,65535)][int]$HttpsPort=443
)
$ErrorActionPreference = 'Stop'
Import-Module WebAdministration
$directory = (Resolve-Path -LiteralPath $PhysicalPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $directory 'web.config'))) { throw 'Rendered web.config is required.' }
if (Test-Path "IIS:\Sites\$SiteName") { throw 'Site already exists; no changes made.' }
if (Test-Path "IIS:\AppPools\$SiteName") { throw 'App pool already exists; no changes made.' }
$binding = "IIS:\SslBindings\0.0.0.0!${HttpsPort}!${HostName}"
if (Test-Path $binding) { throw 'TLS binding already exists; no changes made.' }
if (-not (Test-Path "Cert:\LocalMachine\My\$CertificateThumbprint")) { throw 'Install the TLS certificate first.' }
Get-WebGlobalModule -Name 'RewriteModule' -ErrorAction Stop | Out-Null
Get-WebGlobalModule -Name 'ApplicationRequestRouting' -ErrorAction Stop | Out-Null
$proxy = Get-WebConfiguration -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy'
if (-not $proxy.enabled -or $proxy.preserveHostHeader -or $proxy.reverseRewriteHostInResponseHeaders) {
    throw 'Review and configure ARR: enabled=true, preserveHostHeader=false, reverseRewriteHostInResponseHeaders=false.'
}
[xml]$config = Get-Content -Raw -LiteralPath (Join-Path $directory 'web.config')
$authority = if ($HttpsPort -eq 443) { $HostName } else { "${HostName}:${HttpsPort}" }
$hostRule = $config.configuration.'system.webServer'.rewrite.rules.rule | Where-Object { $_.name -eq 'Require configured host' }
if ($hostRule.conditions.add.pattern -ne ('^' + [regex]::Escape($authority) + '$')) { throw 'Rendered origin and HTTPS binding differ.' }
New-WebAppPool -Name $SiteName | Out-Null
Set-ItemProperty "IIS:\AppPools\$SiteName" -Name managedRuntimeVersion -Value ''
New-Website -Name $SiteName -PhysicalPath $directory -ApplicationPool $SiteName -Port $HttpsPort -HostHeader $HostName -Ssl -SslFlags 1 | Out-Null
New-Item -Path $binding -Thumbprint $CertificateThumbprint -SSLFlags 1 | Out-Null
Write-Output 'Dedicated HTTPS site created. Verify the SSH tunnel and target acceptance checks before use.'
