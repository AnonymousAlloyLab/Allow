# Separate public installation for the existing R1 target

This procedure replaces the public route with a fresh anonymous installation. It
does not upgrade or migrate the existing private store. The operator reported the
original R1 manifest hash
`7e40d4d1b07f0543b1f2beb02be149e4c5fccd2f87365212863a5887294aa1d6`,
Java 17.0.20.1, `/opt/allow` owned by `allow:allow` mode0700, and an active, enabled
`allow.service`. The selected WSL2 distribution is `Ubuntu-24.04` on Windows10
21H2 IoT Enterprise. IIS site `Allow` uses `C:\inetpub\allow` and HTTPS binding
`*:443:allow.alloy4.fun`, SNI flag1, with a certificate in `My`. These are
operator-reported facts, not remote acceptance results.
The operator also reported the scheduled task `\Allow Private Tunnel` as Running.
Its name/state identify a likely route owner; inspect its action and recovery
settings privately before assuming it is the only tunnel process.

The closed `PUBLIC_REPLACEMENT` profile uses `/opt/allow-public`, account
`allow-public`, unit `allow-public.service`, ANONYMOUS mode and WSL loopback18081.
It keeps fresh database credentials, identities and generated dependencies under
the new root. No private model, corpus, runtime or credential is copied there.
The original installation stays at its original path. Do not overlay the archive
on `/opt/allow` or point either installation at the other's database.

The [contract](../spec/staged-public-cutover.json) received the required six
reviews; its 50 finite policy theorems passed two matching Lean4.34.1 builds before
implementation. This is not proof of native isolation, backups or race freedom.
The disposable two-store rehearsal preserved the stopped R1 runtime inventory
and all four fixture document readbacks. It reused dependencies and one workstation
UID; fresh target provisioning and distinct-account isolation remain untested.

## Maintenance boundary and preservation

Keep ingress restricted for the entire cutover and acceptance. The existing R1
public route failed the matrix-path boundary probe; it must not be the public
fallback. The deployment package does not automatically stop or disable anything.
An operator must own an exclusive maintenance window and exclude competing root
administrators, scheduled startups and manual backend launches.

Before mutation, identify and privately save the existing Allow IIS configuration,
effective ARR settings and any Windows tasks/tunnel supervisors that own this
route. Record their states without putting capabilities or credentials in reports.
Inspect the selected TLS certificate's hostname, expiry and private-key access.
Other sites on this Windows server are outside this cutover.

Once those checks are complete, stop only the identified Allow route and quiesce
its known supervisor/tunnel. The relevant operator commands are:

```powershell
Import-Module WebAdministration
Stop-Website -Name 'Allow'
Disable-ScheduledTask -TaskPath '\' -TaskName 'Allow Private Tunnel'
Stop-ScheduledTask -TaskPath '\' -TaskName 'Allow Private Tunnel'
wsl.exe --distribution Ubuntu-24.04 --user root --exec systemctl disable --now allow.service
wsl.exe --distribution Ubuntu-24.04 --user root --exec systemctl show allow.service --property=LoadState,ActiveState,SubState,MainPID,UnitFileState,Job,ControlGroup
```

Require loaded/inactive/dead, MainPID0, disabled, no pending job and an empty or
absent cgroup. Verify the old supervisor cannot restart it, no unmanaged old
backend/SQL processes remain, and Linux/Windows loopback18081 has no conflicting
listener. A unit status alone does not establish absence of unmanaged processes.
Do not terminate a whole WSL distribution or unrelated Windows task.

Capture a private post-stop content/identity/configuration inventory or a verified
cold backup. Normal shutdown can write state, so compare against this stopped
boundary. Check for external runtime, tablespace and WAL links before claiming
backup completeness; retain the original path and permissions. Do not use a live
tree copy, hardlinked backup, direct SQL client or delete ownership journals.
Every SQL operation, including any SQL backup, must use SQLeanParser. If quiescence
or backup scope is uncertain, leave ingress restricted and investigate.

## Fresh protected installation

Transfer the archive and its SHA256 through a trusted channel into private staging
outside all IIS roots. Check `Get-FileHash -Algorithm SHA256` against that trusted
value. The sidecar detects corruption; it is not a signature. Retain the original
archive and use a separate Windows extraction for the PowerShell tools.

Check that the `allow-public` account, `/opt/allow-public` and
`/etc/systemd/system/allow-public.service` are all absent. If any exists, inspect
and resume deliberately; do not overwrite or reuse it as a fresh installation.
As root inside `Ubuntu-24.04`, create the account and root only after that check:

```bash
useradd --system --no-create-home --home-dir /opt/allow-public --shell /usr/sbin/nologin allow-public
install -d -m 700 -o allow-public -g allow-public /opt/allow-public
```

Extract the verified archive into this empty root as `allow-public` with
`umask 077`. Use a Linux ZIP extractor that preserves the normalized Unix modes:
ordinary files no broader than0644, pinned parser no broader than0755 (owner
execute required) and directories0700. Stricter0600/0700 modes from the umask are
accepted; never restore group/other write bits. Keep all ancestors
root-owned or service-owned without group/other write access. Do not use recursive
ownership repair on `/opt/allow`. The private account must retain its original
UID and root0700; the public account must be distinct and denied each of read,
write and traversal on the old root, including ACL and supplementary-group effects.

The service account has no login shell. Run commands via explicit WSL execution,
for example `wsl.exe --distribution Ubuntu-24.04 --user allow-public --exec
/usr/bin/python3 -I -B ...`, rather than an interactive login. From the new Linux
root, as `allow-public`, render and install its configuration:

```bash
/usr/bin/python3 -I -B deploy/configure.py --origin https://allow.alloy4.fun \
  --installation-slot PUBLIC_REPLACEMENT --transport wsl --access-mode ANONYMOUS \
  --backend-port 18081 --tunnel-port 18081 --install-root /opt/allow-public \
  --account allow-public --output /opt/allow-public/generated-instance
install -m 600 generated-instance/linux/instance.json deploy/instance.json
/usr/bin/python3 -I -B deploy/linux/check_public.py --config deploy/instance.json
```

Do not run setup without `-I -B`. The guard is read-only and runs before runtime
lock creation, dependency provisioning or SQL. A guard failure is a stop condition;
do not edit it out or select PRIMARY. It checks the actual fixed paths/accounts
and old unit metadata, not global exclusion against concurrent administrators.

Install the reviewed generated `allow-public.service` as root only if its target
file is absent, then `systemctl daemon-reload`. Leave it disabled and inactive;
do not use `enable --now`. The unit contains no dependency that stops or starts
`allow.service`. Review the generated WSL resource proposal against any existing
`.wslconfig`; applying it or restarting WSL is a separate coordinated operation.
The proposal is four CPUs/5GB/zero swap; the service limits are CPU400%, memory
3GiB high/4GiB maximum, no swap and512 tasks.

Install missing prerequisites listed in the [Linux guide](iis-deployment.md).
Then run the verifier as `allow-public` and resolve any failures before adding
`--initialize` to initialize only this new root:

```bash
/usr/bin/python3 -I -B deploy/linux/setup.py --config deploy/instance.json
/usr/bin/python3 -I -B deploy/linux/setup.py --config deploy/instance.json --initialize
```

Provision from hash-pinned sources into fresh directories; do not copy the old
venv, PostgreSQL binaries, credentials or generated runtime. Setup compiles
PostgreSQL and provisions Python packages, requiring network access and temporary
build capacity. It initializes the empty schema through SQLeanParser and stops
its owned SQL processes before returning. Failed/uncertain setup retains evidence;
inspect it rather than deleting locks or presenting it as a fresh success.

## Restricted startup and acceptance

From the verified Windows staging copy, under the Windows account owning this
distribution, run:

```powershell
.\deploy\windows\Test-Wsl.ps1 -Distribution Ubuntu-24.04 -InstallationSlot PUBLIC_REPLACEMENT
.\deploy\windows\Start-Wsl.ps1 -Distribution Ubuntu-24.04 -InstallationSlot PUBLIC_REPLACEMENT
```

The second command holds the foreground supervisor. It checks the verified public
guard before every systemctl start transaction, and its finalizer stops only the
public unit it started. It uses the same distribution mutex as PRIMARY. Abrupt
process termination may bypass finalizers; inspect ownership and cleanup before
recovery. No Windows startup task is installed by these tools. Review and test
any later task's account, retry, shutdown and reboot behavior on this target.

Prove that Windows127.0.0.1:18081 reaches the intended Linux loopback backend via
WSL NAT forwarding. Verify backend and SQL are unreachable externally. Do not add
wildcard bindings or a public portproxy as a workaround.

Privately preserve the existing `C:\inetpub\allow\web.config` and stage the new
rendered IIS configuration while `Allow` is stopped. Review effective ARR host
preservation, proxy settings, request filtering and restricted logging before
restricted test access. The generic site installer refuses unsafe existing-site
replacement; do not delete or recreate the known site to bypass it. Do not put the
Linux package, instance configuration or runtime in the IIS root. Do not change
unrelated sites or their shared settings without separate impact review.

Restricted tests must cover actual TLS/SNI/certificate, exact Host/Origin and alias
denial, duplicate headers, two independent anonymous sessions, cross-session
denials, expiry/drain, restart cleanup, resource pressure, cold startup and
reboot/outage recovery. Use the partial unauthenticated probe in ANONYMOUS mode;
its PASS alone cannot establish full acceptance. The unchanged application's local
HTTP/browser tests remain useful evidence, not target tests. Keep old ingress
restricted until those native checks pass and exposure is deliberate.

## Restricted rollback

Stop the public foreground owner and verify the new unit and all its children/SQL
are stopped. Retain `/opt/allow-public` and its public writes for investigation;
do not silently discard visitor data. Keep ingress restricted. Restore only the
previously recorded private routing/startup configuration, then reopen the old
store through its original `/opt/allow` installation. Never attach old Java to the
public database, migrate backwards, or copy new credentials into the old root.
The old enabled state may be restored deliberately within that restricted flow.
Do not reopen R1 anonymously: its known public boundary defect remains unresolved.

The archive is a private-transfer candidate. Native acceptance, performance on the
4vCPU/8GiB host, licensing/redistribution and commercial release remain open.
