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

Extract the package into `/opt/allow`, set ownership to `allow`, and use restrictive
directory permissions. Keep only the rendered `web.config` in the IIS site root;
the Linux package and configuration never belong under a Windows web root.

Run as the service account from `/opt/allow`:

```bash
/usr/bin/python3 deploy/configure.py \
  --origin https://allow.example.com --output /opt/allow/generated-instance \
  --install-root /opt/allow --account allow \
  --tunnel-port 18081 --backend-port 8080
```

Choose an output location writable by the account; the renderer requires a new
directory. Replace `allow.example.com`
with your lowercase DNS name. Omit `:443`; other explicit HTTPS ports are
supported. A URL path prefix is not supported. Copy `linux/instance.json` to
`/opt/allow/deploy/instance.json`, and keep it private to the service account.
Copy the generated `linux/allow.service` to `/etc/systemd/system/allow.service`
as administrator. The unit bounds PostgreSQL, SQLeanParser, Spring and workers
together to 400% CPU, 5-GiB high/6-GiB maximum memory, no swap and 512 tasks.

## Initialize and start Linux

As `allow`, first run this command without `--initialize` to verify the package
manifest and host prerequisites. Add `--initialize` to provision the new installation:

```bash
/usr/bin/python3 deploy/linux/setup.py --config deploy/instance.json --initialize
```

Setup needs network access for hash-pinned Python packages and PostgreSQL/
pgvector source archives. PostgreSQL is compiled at the installation root;
Python is provisioned into a new local environment. No existing workstation
database is copied. The pinned SQLeanParser executable is verified against its
lock; the target does not need `/home/augustus/SQLeanParser`. Every SQL statement,
including schema initialization, goes through the parser proxy. Setup does not
download model weights or import a corpus. Predicate retrieval needs separately
provisioned data/models before it has useful results.

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

Install the certificate in LocalMachine/My, then run:

```powershell
.\Install-Site.ps1 -SiteName Allow -HostName allow.example.com `
  -PhysicalPath C:\inetpub\allow -CertificateThumbprint YOUR_40_HEX_THUMBPRINT
```

The script refuses to overwrite a site, app pool or TLS binding and refuses
incompatible ARR settings. It creates an HTTPS-only site. Use `-HttpsPort` for
an explicit nondefault port matching the generated origin. Review local firewall
rules and DNS; no external port may reach the Spring listener or Windows tunnel.
Do not add a competing HTTP site or a redirect that echoes untrusted Host values.

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
