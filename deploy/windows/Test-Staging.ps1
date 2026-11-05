<#
.SYNOPSIS
Run portable, isolated staging mocks without IIS or native Windows acceptance.
#>
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$tokens=$null; $errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Install-Site.ps1'),[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Installer syntax is invalid.' }
foreach ($name in @('Assert-HostName','Read-SafeXml','Assert-RenderedConfig','Assert-FreeResources','Assert-Certificate','New-StoppedSite','Set-SafeLogging')) {
    $function=$ast.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$true)
    if (-not $function) { throw "Missing function: $name" }
    Invoke-Expression $function.Extent.Text
}
$script:count=0
<# Record a successful mock assertion. #>
function Pass { $script:count++ }
<# Assert that a bounded script block fails. #>
function Expect-Failure([scriptblock]$Action) {
    $failed=$false
    try { & $Action } catch { $failed=$true }
    if (-not $failed) { throw 'Expected rejection did not occur.' }
    Pass
}
$directory=Join-Path ([IO.Path]::GetTempPath()) ('allow-staging-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $directory | Out-Null
try {
    $fixture=@'
<configuration><system.webServer><rewrite><rules><clear /><rule name="Require HTTPS" stopProcessing="true"><match url=".*" /><conditions><add input="{HTTPS}" pattern="^on$" negate="true" ignoreCase="false" /></conditions><action type="CustomResponse" statusCode="403" statusReason="Forbidden" statusDescription="Deployment routing rejected" /></rule><rule name="Require configured host" stopProcessing="true"><match url=".*" /><conditions><add input="{HTTP_HOST}" pattern="^test-host\.example$" negate="true" ignoreCase="false" /></conditions><action type="CustomResponse" statusCode="403" statusReason="Forbidden" statusDescription="Deployment routing rejected" /></rule><rule name="Allow through local SSH tunnel" stopProcessing="true"><match url="(.*)" /><action type="Rewrite" url="http://127.0.0.1:18081/{R:1}" appendQueryString="true" logRewrittenUrl="false" /></rule></rules></rewrite><caching enabled="false" enableKernelCache="false" /><httpErrors existingResponse="PassThrough" /><security><requestFiltering><requestLimits maxAllowedContentLength="3145728" /></requestFiltering></security></system.webServer></configuration>
'@
    [IO.File]::WriteAllText((Join-Path $directory 'web.config'),$fixture)
    Assert-HostName 'test-host.example'; Pass
    Assert-RenderedConfig $directory 'test-host.example'; Pass
    Expect-Failure { Assert-HostName 'BAD.example' }
    Expect-Failure { Assert-RenderedConfig $directory 'other.example' }
    [IO.File]::WriteAllText((Join-Path $directory 'extra.txt'),'extra')
    Expect-Failure { Assert-RenderedConfig $directory 'test-host.example' }
    [IO.File]::Delete((Join-Path $directory 'extra.txt'))
    function Get-ChildItem { param($Path,$ErrorAction) return @() }
    $manager=[pscustomobject]@{Sites=@{newsite=[pscustomobject]@{Bindings=@()}};ApplicationPools=@{}}
    Expect-Failure { Assert-FreeResources $manager 'newsite' 443 }
    function Get-Item { param($LiteralPath) [pscustomobject]@{HasPrivateKey=$true;NotBefore=[datetime]::UtcNow.AddDays(-1);NotAfter=[datetime]::UtcNow.AddDays(1)} }
    function Test-Certificate { param($Cert,$Policy,$DNSName,$ErrorAction) $false }
    Expect-Failure { Assert-Certificate ('A'*40) 'test-host.example' }
    $script:pool=[pscustomobject]@{ManagedRuntimeVersion='v4'}
    $script:binding=[pscustomobject]@{CertificateHash=$null;CertificateStoreName='';SslFlags=0}
    $script:site=[pscustomobject]@{ServerAutoStart=$true;Applications=@{'/'=[pscustomobject]@{ApplicationPoolName=''}};Bindings=@($script:binding);Name='newsite'}
    $pools=[pscustomobject]@{}; $pools | Add-Member ScriptMethod Add {param($name) return $script:pool}
    $sites=[pscustomobject]@{}; $sites | Add-Member ScriptMethod Add {param($name,$protocol,$address,$path) return $script:site}
    $manager=[pscustomobject]@{ApplicationPools=$pools;Sites=$sites;Committed=$false;FailCommit=$false}
    $manager | Add-Member ScriptMethod CommitChanges { if ($script:site.ServerAutoStart) { throw 'Auto-start site reached commit.' }; if ($this.FailCommit) { throw 'Simulated commit failure.' }; $this.Committed=$true }
    $certificate=[pscustomobject]@{}; $certificate | Add-Member ScriptMethod GetCertHash { return ,([byte[]](1,2,3)) }
    $script:cleared=$false
    $custom=[pscustomobject]@{}; $custom | Add-Member ScriptMethod Clear { $script:cleared=$true }
    $log=[pscustomobject]@{}; $log | Add-Member ScriptMethod GetCollection {param($name) if ($name -ne 'customFields') { throw 'Wrong collection.' }; return $custom }
    $element=@{name='newsite'}; $element | Add-Member ScriptMethod GetChildElement {param($name) if ($name -ne 'logFile') { throw 'Wrong child.' }; return $log }
    $section=[pscustomobject]@{}; $section | Add-Member ScriptMethod GetCollection { return ,@($element) }
    $config=[pscustomobject]@{}; $config | Add-Member ScriptMethod GetSection {param($name) if ($name -ne 'system.applicationHost/sites') { throw 'Wrong section.' }; return $section }
    $logManager=[pscustomobject]@{}; $logManager | Add-Member ScriptMethod GetApplicationHostConfiguration { return $config }
    $logSite=[pscustomobject]@{Name='newsite';LogFile=[pscustomobject]@{LogFormat='';LogExtFileFlags=''}}
    Set-SafeLogging $logManager $logSite
    if (-not $script:cleared -or $logSite.LogFile.LogFormat -cne 'W3C' -or $logSite.LogFile.LogExtFileFlags -match 'Query|UserName|Referer|Cookie') { throw 'Unsafe logging configuration.' }; Pass
    function Set-SafeLogging { param($Manager,$Site) if ($Site.ServerAutoStart) { throw 'Unexpected auto-start.' } }
    New-StoppedSite $manager 'newsite' 'test-host.example' 443 $directory $certificate
    if (-not $manager.Committed -or $script:site.ServerAutoStart -or $script:binding.SslFlags -ne 1 -or $script:pool.ManagedRuntimeVersion -cne '') { throw 'Stopped staging configuration failed.' }; Pass
    $manager.FailCommit=$true; $manager.Committed=$false
    Expect-Failure { New-StoppedSite $manager 'newsite' 'test-host.example' 443 $directory $certificate }
    if ($manager.Committed) { throw 'Simulated failure unexpectedly committed.' }; Pass
    [pscustomobject]@{status='PASS';assertions=$script:count;nativeWindowsAcceptance='OPEN'} | ConvertTo-Json -Compress
} finally {
    if ([IO.Directory]::Exists($directory)) { [IO.Directory]::Delete($directory,$true) }
}
