# Deploying Allow behind IIS

This package runs IIS on Windows as an HTTPS reverse proxy to an **Ubuntu 24.04
x86-64 Linux backend** over a loopback-bound SSH tunnel. Linux is required for
the existing Java worker sandbox and SQL ownership controls. Install one private
workspace per dedicated Linux service account. Every holder of its launch link
has access to that workspace; this is not a multi-tenant authentication system.

The package selects **fresh Tier-1 JVMs for document advisory validation**.
The recorded end-to-end p95 was 348.70 ms versus 399.67 ms for fresh DEFAULT on
the same workload. This is an explicit private experimental selection, not a
pass of the earlier strict <300-ms gate. Durable revalidation and solver jobs
retain DEFAULT; warm pooling stays disabled. Target-server latency is unmeasured.

## Package and prerequisites

The archive contains compiled Spring/React assets, Python application modules,
the pinned SQLeanParser executable/lock/notice, deployment tools and a SHA-256
manifest. It contains no workspace database, tokens, SSH keys, TLS certificates,
source datasets, trained checkpoints or copied virtual environment. Transfer it
privately and verify the archive checksum received over your trusted channel.

Use a short, canonical installation path such as `/opt/allow` and a dedicated
unprivileged account named `allow`. Target budget is **4 vCPU / 8 GiB**. Do not
run corpus ingestion or ML training alongside interactive validation.

Linux requires Java 17 at the standard Ubuntu layout, `/usr/bin/python3` 3.12,
Python venv support, Bubblewrap, util-linux/prlimit, build tools for PostgreSQL,
OpenSSH server, and systemd with CPU/memory/pids controllers. Namespace creation
must be permitted for the service account. The package retains the current
`/lib64` and `/etc/java-17-openjdk` sandbox layout. Install these host prerequisites
as administrator; do not disable sandboxing if a preflight fails:

```bash
sudo apt-get install openjdk-17-jdk python3.12-venv bubblewrap util-linux \
  build-essential libreadline-dev zlib1g-dev bison flex pkg-config openssh-server unzip
sudo useradd --system --create-home --home-dir /opt/allow --shell /usr/sbin/nologin allow
```

Use a separate restricted SSH-forwarding account on Linux. Windows requires IIS,
URL Rewrite, ARR, OpenSSH Client and a TLS certificate for the chosen DNS name.
Microsoft documents [ARR and URL Rewrite reverse proxy configuration](https://learn.microsoft.com/en-us/iis/extensions/url-rewrite-module/reverse-proxy-with-url-rewrite-v2-and-application-request-routing).
Follow its module installation guidance; the package does not download or install
Windows modules or change global ARR settings automatically.

## Render instance configuration

Extract the package into `/opt/allow` as the dedicated `allow` account with
`umask 077`; the installation root must be owned by that account and mode0700.
All installation ancestors must belong to that account or trusted root and must
not be group/other writable. Root-owned sticky temporary ancestors are allowed
for isolated checks. The archive normalizes ordinary files to0644 and the pinned
parser to0755; preserve these modes when extracting. Never make installation or
runtime directories group writable. Keep only the rendered `web.config` in the IIS site root;
the Linux package and configuration never belong under a Windows web root.

Run as the service account from `/opt/allow`:

```bash
/usr/bin/python3 -I -B deploy/configure.py \
  --origin https://allow.example.com --output /opt/allow/generated-instance \
  --install-root /opt/allow --account allow \
  --tunnel-port 18081 --backend-port 8080
```

Choose an output location writable by the account; the renderer requires a new
directory. Replace `allow.example.com`
with your lowercase DNS name. Omit `:443`; other explicit HTTPS ports are
supported. A URL path prefix is not supported. Copy `linux/instance.json` to
`/opt/allow/deploy/instance.json` with `install -m 600`; it must be a service-owned
regular file, without hardlinks or symlinks.
Copy the generated `linux/allow.service` to `/etc/systemd/system/allow.service`
as administrator. The unit bounds PostgreSQL, SQLeanParser, Spring and workers
together to 400% CPU, 5-GiB high/6-GiB maximum memory, no swap and 512 tasks.

## Initialize and start Linux

As `allow`, first run this command without `--initialize` to verify the package
manifest and host prerequisites. Add `--initialize` to provision the new installation:

```bash
/usr/bin/python3 -I -B deploy/linux/setup.py --config deploy/instance.json --initialize
```

Setup needs network access for hash-pinned Python packages and PostgreSQL/
pgvector source archives. PostgreSQL is compiled at the installation root;
Python is provisioned into a new local environment. A fresh initialization
refuses any preexisting generated venv/PostgreSQL/download directories, even
when the runtime is empty. No existing workstation
database is copied. The pinned SQLeanParser executable is verified against its
lock; the target does not need `/home/augustus/SQLeanParser`. Every SQL statement,
including schema initialization, goes through the parser proxy. Setup does not
download model weights or import a corpus. Predicate retrieval needs separately
provisioned data/models before it has useful results.

The setup and service entrypoints require `/usr/bin/python3 -I -B`. They load
only verified application source, reject local application bytecode caches and
unlisted inputs, and disable application bytecode generation. Do not run these
entrypoints through a normal Python import or without the isolation flags.
Standard-library/distribution Python and the transferred manifest/entry scripts
are trusted bootstrap inputs; the checksum is not a signature. A malicious
same-UID operator or root remains outside this boundary.

Managed third-party dependencies are separately trusted from hash-pinned fresh
provisioning. Their bytecode is permitted within the venv. Ownership/mode checks
allow only the standard generated venv interpreter links to system Python and
its internal `lib64` link, plus generated PostgreSQL `libpq`/`libecpg`/`libpgtypes`
shared-library links that resolve inside the private PostgreSQL install. Shipped
application/configuration and private runtime paths reject symlinks. This does
not claim that application manifests prove dependency runtime semantics.

Initialization and service share one nonblocking flock retained through cleanup.
A competing supported supervisor performs no SQL/token/backend action. Leave
`.runtime/deployment.lock` in place; never unlink it to bypass contention.
The owner reaps its backend before SQL teardown; cleanup uncertainty fails the
service. Only that owner removes its launch link. Retained initialized stores
keep their existing state and credentials; they are never presented as fresh.

Do not use the initializer as an upgrade/migration mechanism for an existing
installation. Preserve its state and follow the existing SQL backup and recovery
procedures. Never remove a retained ownership journal to force startup.

Then, as administrator:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now allow.service
sudo systemctl status allow.service
```

The service creates `/opt/allow/.runtime/launch.url` with owner-only permissions.
Read that file privately as the operator; it contains the public HTTPS URL with
a bearer token in its fragment. The token is never embedded in IIS configuration
or application assets. Do not put it in a query string, public log or shared ticket.
The browser removes the fragment and keeps the token in memory. A backend restart
rotates the token; an SSH tunnel reconnect alone does not. Reopen the current
private link after restarting the backend or losing the in-memory session.

## Establish the Windows tunnel

Provision a dedicated SSH key and verify the Linux host-key fingerprint through
an independent channel before populating the Windows known-hosts file. Restrict
the Linux SSH account to local forwarding to `127.0.0.1:8080`, disable shell/PTY,
agent/X11 forwarding and other destinations using the host's OpenSSH controls.
Keep private keys readable only by the Windows account running the tunnel.

Run the supplied script on Windows under that account:

```powershell
.\Start-Tunnel.ps1 -LinuxHost linux-backend.example.com -SshUser allow-tunnel `
  -IdentityFile C:\AllowSecrets\id_ed25519 -KnownHostsFile C:\AllowSecrets\known_hosts `
  -TunnelPort 18081 -BackendPort 8080
```

It runs in the foreground, binds only Windows `127.0.0.1:18081`, uses strict host
verification, ignores ambient SSH configuration, and exits when forwarding fails.
Use a known-hosts filename without whitespace. The installed OpenSSH client must
support `-F none`; verify this before provisioning unattended operation. For unattended operation, register
it with your approved Windows service/task supervisor under the same account,
with restart-on-failure and no interactive password prompts. The package does
not silently install a privileged task. When the tunnel is unavailable, IIS
must return a gateway failure; there is no alternate backend or SQL route.

## Configure IIS

Use a dedicated IIS instance/site if global ARR settings conflict with other
applications. As administrator, explicitly review and set:

```powershell
Import-Module WebAdministration
Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy' -Name enabled -Value $true
Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy' -Name preserveHostHeader -Value $false
Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy' -Name reverseRewriteHostInResponseHeaders -Value $false
```

Copy the rendered `iis/web.config` into a new dedicated directory such as
`C:\inetpub\allow`. Grant the new application-pool identity read access to that
directory. The proxy must send Host `127.0.0.1:18081` and preserve the browser's
Origin and Authorization unchanged. It must never inject a shared token.

Install the certificate in LocalMachine/My, then run from elevated **Windows
PowerShell 5.1** in an exclusive IIS administration window:

```powershell
.\Install-Site.ps1 -SiteName Allow -HostName allow.example.com `
  -PhysicalPath C:\inetpub\allow -CertificateThumbprint YOUR_40_HEX_THUMBPRINT `
  -PreflightOnly
```

Preflight requires the root to contain only the exact rendered `web.config`,
matching canonical hostname and a fixed loopback tunnel destination. It rejects
existing site/app-pool names and **any existing IIS or HTTP.sys binding on the
selected port**, so use a dedicated instance/port. It verifies modules and ARR,
certificate dates/private-key presence, and the Windows SSL certificate policy
for the hostname, trust chain and revocation. Revocation lookup may use the
network; an unavailable check fails closed. Do not bypass this failure with an
untrusted certificate. Microsoft describes the checks and their limits in
[Test-Certificate](https://learn.microsoft.com/en-us/powershell/module/pki/test-certificate?view=windowsserver2025-ps).
The command does not mutate IIS configuration.

Repeat without `-PreflightOnly` to stage the site. The first configuration commit
sets `serverAutoStart=false`, the dedicated app pool, SNI and certificate. The
script never starts the site. It selects site-specific W3C logging fields that
exclude query strings, usernames, cookies, Authorization and referrer, and clears
custom fields. Verify effective logging and any global tracing/monitoring on the
real target; source settings alone do not prove that secrets are absent from logs.
The configured log fields follow Microsoft's
[site logging documentation](https://learn.microsoft.com/en-us/iis/configuration/system.applicationhost/sites/site/logfile/).

There is no cross-system transaction guarantee for IIS and HTTP.sys. A failed
commit reports uncertain state and retains artifacts for inspection. Keep ingress
restricted, compare the new site/pool/binding with the supplied names, physical
path, port and certificate, and remove only resources known to belong to the
failed invocation. Do not delete global TLS registrations or existing sites to
force a retry. A clean retry still refuses collisions.

Use `-HttpsPort` for an explicit nondefault port matching the rendered origin.
Review local firewall rules and DNS; no external port may reach the Spring
listener or Windows tunnel. Do not add a competing HTTP site or a redirect that
echoes untrusted Host values.

## Controlled public deployment

The public hostname, Windows/Linux connection details and audience must be
resolved before installing on a target. **Public URL with privately distributed
operator links** preserves the existing shared-workspace access model. Anonymous
visitors or registered users with isolated workspaces require a new access design;
never publish the launch link to simulate public access. Internet hosting does
not itself approve commercial release or public redistribution of this archive.

Keep the IIS site stopped and ingress restricted to your acceptance client while
provisioning Linux, the restricted tunnel account/key, a supervised Windows
tunnel and TLS. Review the Windows account/key/known-host ACLs, web-root ACLs,
firewall and recovery policy. No task/service supervisor, DNS or firewall change
is installed automatically. Check the actual certificate chain and renewal
procedure, including the Windows trust store and external clients.

After preflight and staged configuration inspection, intentionally start the
site for acceptance from the permitted client:

```powershell
Start-Website -Name Allow
```

From an external acceptance client with Python 3, run the nonsecret probe against
the actual hostname (use `python` on Windows or `/usr/bin/python3` on Linux):

```bash
python -I -B deploy/probe_public.py --origin https://allow.example.com --timeout 8
```

The probe runs eight sequential GET checks. It uses normal certificate and
hostname validation, ignores ambient HTTP proxies, follows no redirects and
accepts no launch link or real token. Each request has a total subprocess
deadline including DNS, plus a 64-KiB body cap. Output contains only check IDs,
statuses, timings and fixed error categories; failure returns exit code 1.
Do not interpret these diagnostic timings as validation latency. Probe PASS
establishes the listed unauthenticated checks only. In particular, rejected
aliases without a bearer do not establish authenticated URI normalization.

Complete the authenticated and operational checks below while ingress remains
restricted. Test IIS-generated denial/gateway headers separately; the probe
requires backend security headers on root and canonical backend denials, not
on all edge errors. If a check fails, stop the new site and preserve diagnostics.
After audience acceptance and successful native checks, intentionally permit
the chosen public ingress, retest from an external client, and enable automatic
site startup if that is the agreed operating policy:

```powershell
Set-ItemProperty 'IIS:\Sites\Allow' -Name serverAutoStart -Value $true
```

Demonstrate restart/reboot recovery with the selected tunnel supervisor. Treat
unattended recovery, target latency and Windows acceptance as open until actual
results are recorded. The [staging contract](../spec/public-iis-staging.json),
six-seat council and 37-theorem Lean model precede these tooling changes; the
model does not prove Windows behavior or implementation correspondence.

## Target acceptance and rollback

Windows/IIS execution has not been tested on this Linux build host. Before use,
check the real target route: the private launch link loads the editor; document
creation, advisory validation, commit/history and bounded solver jobs work;
retrieval correctly reports the empty/unprovisioned corpus. Confirm no token
appears in IIS access logs and that responses retain no-store and CSP headers.

Negative checks must reject missing/wrong bearer, hostile and duplicate Host/
Origin/Authorization, wrong public hostname, HTTP and forwarded-header spoofing.
Confirm only the loopback tunnel listener exists, a wrong SSH host key fails,
tunnel loss returns a gateway error, and backend restart invalidates the old
token while retained documents survive. Check systemd resource counters and
measure end-to-end validation on the actual server under realistic load.

To return advisory validation to DEFAULT, stop the service, set
`"advisory_profile": "DEFAULT"` in the private instance JSON, restart, and use
the newly generated launch link. This does not change durable or solver profiles.
Stop IIS access and the tunnel before maintenance. `systemctl stop allow.service`
terminates the backend and its owned PostgreSQL/parser processes; do not kill
unrelated services or delete workspace files.

The [deployment contract](../spec/iis-deployment.json) and its finite Lean policy
proof precede these changes. They do not prove Windows behavior, implementation
refinement, target security or performance. Prior strict latency failures and
open runtime/accessibility/rights gates remain recorded. This is a private
operator transfer package; commercial release and public redistribution remain
**NO_GO** until their separate requirements are resolved.
