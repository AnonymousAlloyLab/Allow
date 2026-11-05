<#
.SYNOPSIS
Preflight or stage a new stopped, dedicated HTTPS IIS site.
.DESCRIPTION
Requires an exclusive administrative configuration window. It never starts the
site or changes global ARR settings. Before staging, an operator must verify restrictive
NTFS write ACLs on the web root and every ancestor, and confirm every ancestor is
free of reparse points. Native Windows acceptance is still required.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z][A-Za-z0-9_-]*$')][string]$SiteName,
    [Parameter(Mandatory=$true)][string]$HostName,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{40}$')][string]$CertificateThumbprint,
    [Parameter(Mandatory=$true)][string]$PhysicalPath,
    [ValidateRange(1,65535)][int]$HttpsPort=443,
    [switch]$PreflightOnly
)
$ErrorActionPreference = 'Stop'

<# Require the same canonical DNS grammar used by the Linux renderer. #>
function Assert-HostName([string]$Name) {
    if ($Name.Length -gt 253 -or $Name -cnotmatch '^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$') { throw 'Invalid canonical DNS host.' }
    $labels = $Name.Split('.')
    foreach ($label in $labels) { if ($label.Length -gt 63) { throw 'DNS label too long.' } }
    if (($labels | Where-Object { $_ -cnotmatch '^[0-9]+$' }).Count -eq 0) { throw 'IP literal host is not allowed.' }
}

<# Load XML without DTDs or external entities. #>
function Read-SafeXml([string]$Path) {
    $settings = [System.Xml.XmlReaderSettings]::new()
    $settings.DtdProcessing = [System.Xml.DtdProcessing]::Prohibit
    $settings.XmlResolver = $null
    $reader = [System.Xml.XmlReader]::Create($Path, $settings)
    try { $xml = [System.Xml.XmlDocument]::new(); $xml.XmlResolver = $null; $xml.Load($reader); return $xml }
    finally { $reader.Dispose() }
}

<# Check the entire rendered configuration, not only selected rewrite rules. #>
function Assert-RenderedConfig([string]$Directory, [string]$Authority) {
    $entries = @(Get-ChildItem -LiteralPath $Directory -Force)
    if ($entries.Count -ne 1 -or $entries[0].Name -cne 'web.config' -or $entries[0].PSIsContainer -or ($entries[0].Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Web root must contain only a regular web.config.' }
    $xml = Read-SafeXml $entries[0].FullName
    $rules = @($xml.configuration.'system.webServer'.rewrite.rules.rule)
    if ($rules.Count -ne 3) { throw 'Unexpected rewrite rules.' }
    $rewrite = [string]$rules[2].action.url
    if ($rewrite -cnotmatch '^http://127\.0\.0\.1:([1-9][0-9]{0,4})/\{R:1\}$' -or [int]$Matches[1] -lt 1024 -or [int]$Matches[1] -gt 65535) { throw 'Invalid tunnel rewrite.' }
    $port = [int]$Matches[1]; $pattern = '^' + $Authority.Replace('.', '\.') + '$'
    $expected = @"
<configuration><system.webServer><rewrite><rules><clear /><rule name="Require HTTPS" stopProcessing="true"><match url=".*" /><conditions><add input="{HTTPS}" pattern="^on$" negate="true" ignoreCase="false" /></conditions><action type="CustomResponse" statusCode="403" statusReason="Forbidden" statusDescription="Deployment routing rejected" /></rule><rule name="Require configured host" stopProcessing="true"><match url=".*" /><conditions><add input="{HTTP_HOST}" pattern="$pattern" negate="true" ignoreCase="false" /></conditions><action type="CustomResponse" statusCode="403" statusReason="Forbidden" statusDescription="Deployment routing rejected" /></rule><rule name="Allow through local SSH tunnel" stopProcessing="true"><match url="(.*)" /><action type="Rewrite" url="http://127.0.0.1:$port/{R:1}" appendQueryString="true" logRewrittenUrl="false" /></rule></rules></rewrite><caching enabled="false" enableKernelCache="false" /><httpErrors existingResponse="PassThrough" /><security><requestFiltering><requestLimits maxAllowedContentLength="3145728" /></requestFiltering></security></system.webServer></configuration>
"@
    $reference = [System.Xml.XmlDocument]::new(); $reference.XmlResolver = $null; $reference.LoadXml($expected)
    if ($xml.DocumentElement.OuterXml -cne $reference.DocumentElement.OuterXml) { throw 'web.config differs from the closed rendered configuration.' }
}

<# Check certificate validity, chain, revocation and hostname before staging. #>
function Assert-Certificate([string]$Thumbprint, [string]$DnsName) {
    $certificate = Get-Item -LiteralPath "Cert:\LocalMachine\My\$Thumbprint"
    $now = [DateTime]::UtcNow
    if (-not $certificate.HasPrivateKey -or $certificate.NotBefore.ToUniversalTime() -gt $now -or $certificate.NotAfter.ToUniversalTime() -le $now) { throw 'Certificate must be current and have a private key.' }
    if (-not (Test-Certificate -Cert $certificate -Policy SSL -DNSName "dns=$DnsName" -ErrorAction Stop)) { throw 'Certificate DNS, chain or revocation validation failed.' }
    return $certificate
}

<# Reject collisions with existing sites and HTTP.sys SSL registrations. #>
function Assert-FreeResources($Manager, [string]$Name, [int]$Port) {
    if ($null -ne $Manager.Sites[$Name] -or $null -ne $Manager.ApplicationPools[$Name]) { throw 'Site or app pool already exists.' }
    foreach ($site in $Manager.Sites) { foreach ($binding in $site.Bindings) {
        if ($binding.Protocol -in @('http','https') -and $binding.BindingInformation -match '^.*:([0-9]+):[^:]*$' -and [int]$Matches[1] -eq $Port) { throw 'IIS port binding already exists.' }
    } }
    foreach ($entry in @(Get-ChildItem 'IIS:\SslBindings' -ErrorAction Stop)) {
        if ($null -eq $entry.Port -or [int]$entry.Port -lt 1) { throw 'Cannot inspect HTTP.sys SSL registration.' }
        if ([int]$entry.Port -eq $Port) { throw 'HTTP.sys SSL port registration already exists.' }
    }
}

<# Verify that administrator access and exact global proxy prerequisites are present. #>
function Assert-Environment {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run in an elevated administrator session.' }
    Import-Module WebAdministration -ErrorAction Stop
    if (-not (Get-WebGlobalModule -Name 'RewriteModule' -ErrorAction Stop)) { throw 'URL Rewrite module is required.' }
    if (-not (Get-WebGlobalModule -Name 'ApplicationRequestRouting' -ErrorAction Stop)) { throw 'ARR module is required.' }
    $proxy = Get-WebConfiguration -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy'
    if (-not $proxy.enabled -or $proxy.preserveHostHeader -or $proxy.reverseRewriteHostInResponseHeaders) { throw 'ARR must enable proxy and disable both host-preserving settings.' }
}

<# Configure explicit site-specific W3C fields and clear inherited custom fields. #>
function Set-SafeLogging($Manager, $Site) {
    $Site.LogFile.LogFormat = 'W3C'
    $Site.LogFile.LogExtFileFlags = 'Date, Time, ClientIP, Method, UriStem, HttpStatus, Win32Status, TimeTaken'
    $section = $Manager.GetApplicationHostConfiguration().GetSection('system.applicationHost/sites')
    foreach ($element in $section.GetCollection()) {
        if ([string]$element['name'] -ceq $Site.Name) { $element.GetChildElement('logFile').GetCollection('customFields').Clear(); return }
    }
    throw 'Could not find site-specific logging configuration.'
}

<# Create both objects in one commit, with auto-start disabled before commit. #>
function New-StoppedSite($Manager, [string]$Name, [string]$DnsName, [int]$Port, [string]$Directory, $Certificate) {
    $pool = $Manager.ApplicationPools.Add($Name); $pool.ManagedRuntimeVersion = ''
    $site = $Manager.Sites.Add($Name, 'https', "*:${Port}:${DnsName}", $Directory)
    $site.ServerAutoStart = $false; $site.Applications['/'].ApplicationPoolName = $Name
    $binding = $site.Bindings[0]; $binding.CertificateHash = $Certificate.GetCertHash(); $binding.CertificateStoreName = 'My'; $binding.SslFlags = 1
    Set-SafeLogging $Manager $site
    $Manager.CommitChanges()
}

Assert-HostName $HostName
Assert-Environment
$directory = (Resolve-Path -LiteralPath $PhysicalPath).ProviderPath
if (-not (Test-Path -LiteralPath $directory -PathType Container) -or ((Get-Item -LiteralPath $directory -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Physical path must be a non-symlink directory.' }
$authority = if ($HttpsPort -eq 443) { $HostName } else { "${HostName}:${HttpsPort}" }
Assert-RenderedConfig $directory $authority
$certificate = Assert-Certificate $CertificateThumbprint $HostName
Add-Type -AssemblyName 'Microsoft.Web.Administration'
$manager = [Microsoft.Web.Administration.ServerManager]::new()
try {
    Assert-FreeResources $manager $SiteName $HttpsPort
    if ($PreflightOnly) { Write-Output 'Preflight passed; no IIS changes made.'; return }
    try { New-StoppedSite $manager $SiteName $HostName $HttpsPort $directory $certificate }
    catch { throw "Staging failed; state may be uncertain. Do not start the site. Inspect IIS site '$SiteName', its pool and HTTP.sys SSL registrations; remove only resources confirmed to belong to this invocation. $($_.Exception.Message)" }
    Write-Output 'Dedicated site staged with auto-start disabled. Keep stopped and ingress restricted pending native acceptance.'
} finally { $manager.Dispose() }
