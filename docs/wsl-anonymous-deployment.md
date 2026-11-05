# Anonymous workspaces on the selected Windows/WSL host

**Existing target:** subsequent operator inventory identified the private R1
installation at `/opt/allow`, active and enabled. Follow the
[separate public cutover procedure](staged-public-cutover.md) for that host.
Its new root/account/unit are `/opt/allow-public`, `allow-public` and
`allow-public.service`; all WSL tooling uses `-InstallationSlot PUBLIC_REPLACEMENT`.
The PRIMARY fresh-install examples below are retained for other empty hosts and
must not be applied over the known R1 installation.

This is a target transfer procedure, not evidence of installation. The intended
origin is `https://allow.alloy4.fun`, Windows 10 21H2 IoT Enterprise, and WSL2
Ubuntu 24.04. The operator's `wsl --list --verbose` output identifies the exact
distribution as `Ubuntu-24.04`, Running, version 2. Use that name explicitly and
run Windows commands under the account that owns this distribution. This reported
inventory does not establish the remaining native prerequisites. No remote access
or existing public site is changed here.

Keep IIS stopped and ingress restricted. The existing public endpoint's observed
matrix-path bypass must fail acceptance until the corrected package is deployed.
Do not put this archive, private configuration or runtime in an IIS web root.

Before installing anything, inspect the existing target from PowerShell:

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber
wsl.exe --status
wsl.exe --version
wsl.exe --distribution Ubuntu-24.04 --exec /bin/sh -c 'uname -m; uname -r; cat /etc/os-release; ps -p 1 -o comm=; test -f /sys/fs/cgroup/cgroup.controllers; command -v java; command -v bwrap; command -v prlimit; /usr/bin/python3 --version; getent passwd allow'
wsl.exe --distribution Ubuntu-24.04 --user root --exec systemctl show allow.service --property=LoadState,ActiveState,UnitFileState,FragmentPath
wsl.exe --distribution Ubuntu-24.04 --user root --exec stat -c '%U %G %a %F' /opt/allow
```

These are inventory commands, not an automated PASS verdict. Missing paths,
accounts or units mean installation preparation is incomplete. Review any existing
installation or active service before choosing a fresh directory; do not overwrite
its database or stop a service whose ownership has not been established. If
`wsl --version` is unavailable or PID 1 is not systemd, review Microsoft's
[systemd prerequisites](https://learn.microsoft.com/windows/wsl/systemd) before
changing WSL. Do not apply a global WSL shutdown as part of this inventory.

In a new service-owned `/opt/allow` Linux installation, render:

```bash
/usr/bin/python3 -I -B deploy/configure.py --origin https://allow.alloy4.fun \
  --transport wsl --access-mode ANONYMOUS --backend-port 18081 --tunnel-port 18081 \
  --install-root /opt/allow --account allow --output /opt/allow/generated-instance
```

Review the generated `wslconfig.proposal`; do not overwrite the Windows user's
existing `.wslconfig`. Its 5GB memory, four processors and zero swap apply to the
user's WSL2 VM, potentially affecting other distributions. Arrange any required
WSL restart explicitly with their owners. Review per-distribution systemd setup
and install the generated service as administrator. The service uses MemoryHigh
3G, MemoryMax 4G, no swap, four CPUs and TasksMax512. Follow the ordinary verified
fresh initialization procedure; every SQL operation remains parser-routed.

For this fresh WSL supervisor flow, install the unit and run `systemctl daemon-reload`
without enabling or starting the service. The generic SSH guide's
`systemctl enable --now allow.service` belongs to its separate startup flow:
the WSL supervisor deliberately refuses an already-active service. An existing
enabled service requires a deliberate migration of startup ownership first.

After the `allow` account, protected installation, fresh initialization and resource
limited unit exist, run the post-installation preflight from the Windows staging
copy of the archive:

```powershell
.\deploy\windows\Test-Wsl.ps1 -Distribution Ubuntu-24.04 -LinuxAccount allow
```

It checks the selected Linux environment and configured service limits without
modifying configuration. It does not certify effective WSL VM limits, network
isolation or restart behavior.

Review `Start-Wsl.ps1` before running it with the same explicit parameters. It
starts only `allow.service`, holds a supported-supervisor mutex, keeps an explicit
foreground WSL invocation alive and permits at most three bounded attempts. It
refuses a preexisting active/uncertain service. Its finalizer stops only the
service it started; uncertain cleanup is an error. It does not install a task,
terminate a distribution, invoke global WSL shutdown or contain credentials.
An administrator may later register an approved task under that owning account;
task registration, login/reboot behavior and noninteractive process termination
must be reviewed and tested on the actual target. Abrupt supervisor termination
may bypass finalizers; inspect service ownership and state before recovery.

Once preflight passes and the fresh service is inactive, start its foreground
owner from the same Windows staging directory:

```powershell
.\deploy\windows\Start-Wsl.ps1 -Distribution Ubuntu-24.04 -LinuxAccount allow
```

Prove that Windows `127.0.0.1:18081` reaches the intended Linux loopback backend
using WSL2 NAT localhost forwarding. Do not assume mirrored networking. Verify
there is no externally reachable backend or SQL port. No wildcard binding or
public portproxy fallback is authorized. If mapping fails, stop acceptance and
review a separately configured SSH fallback.

Stage IIS with the rendered configuration and existing stopped-site tools.
Require actual TLS/SNI, exact Host/Origin, alias and duplicate-header rejection,
two independent anonymous sessions, expiry, restart cleanup, resource counters,
reboot/outage recovery and external browser acceptance before public exposure.
No capability, launch URL, private key or credentials belong in reports.

Microsoft references: [WSL configuration](https://learn.microsoft.com/windows/wsl/wsl-config),
[WSL commands](https://learn.microsoft.com/windows/wsl/basic-commands),
[systemd](https://learn.microsoft.com/windows/wsl/systemd), and
[WSL networking](https://learn.microsoft.com/windows/wsl/networking).

## Public transport and capability handling

The ANONYMOUS launcher never writes a private `launch.url`. Visitors explicitly
create separate temporary workspaces through the public bootstrap flow. A random
unused private constructor token remains process-local environment input only;
it is not printed, returned, injected by IIS or persisted as a launch link.
PRIVATE mode retains the existing private launch-link behavior.

The public launcher also bounds Tomcat to 16 request threads (two spare),
64 connections and a 16-connection accept backlog. Connection and keep-alive
idle timeouts are five seconds, keep-alive requests are capped at 20, and request
headers at 16KB. These transport occupancy bounds complement the application's
eight-request global admission and two-request per-workspace admission; they do
not promise availability or an end-to-end request deadline. Verify IIS timeouts,
slow-client handling, resource counters and realistic throughput on the target.

The dual-mode archive is a privately transferred deployment candidate. Its
manifest includes the anonymous lifecycle module, frozen contract/proofs/review
records, WSL tooling and this guide. It does not establish native Windows/WSL/IIS
acceptance or authorize public artifact redistribution. Do not include Windows
login details, RDP credentials or certificates in the archive or evidence.


For the approved staged anonymous route, the partial unauthenticated probe is:

```bash
/usr/bin/python3 -I -B deploy/probe_public.py --origin https://allow.alloy4.fun --access-mode ANONYMOUS
```

This closed option expects 401 for absent/invalid/forwarded-identity capability
checks; PRIVATE remains the default and expects 403 for those same checks.
Other route, Host/Origin, TLS, body and security-header checks are unchanged.
This probe does not enroll visitors or establish isolation/expiry/native target
acceptance. Keep its results separate from the full target acceptance record.
