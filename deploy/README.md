# Allow: dual-mode IIS + Linux deployment candidate

The archive supplies closed PRIVATE and ANONYMOUS profiles. PRIVATE remains the
default shared operator workspace. ANONYMOUS supplies separate temporary visitor
workspaces with bounded enrollment, expiry and scoped lifecycle cleanup. Native
Windows/WSL/IIS and intended public exposure acceptance remain **OPEN**.

The selected target already runs private R1 at `/opt/allow`. Use the
[separate public cutover procedure](docs/staged-public-cutover.md): it creates
`/opt/allow-public` under a distinct account and preserves the original private
store. Do not extract this archive over the existing installation. The
`PUBLIC_REPLACEMENT` selector binds the new account/root/unit and checks that
the old service is disabled and quiescent before provisioning or startup.
It never automatically stops the old service. The generic fresh PRIMARY
instructions below apply only to a different, genuinely empty installation.

Read [the IIS/Linux guide](docs/iis-deployment.md) for the existing private SSH
route and [the anonymous WSL guide](docs/wsl-anonymous-deployment.md) for the
selected `https://allow.alloy4.fun` Windows10 21H2 IoT Enterprise / WSL2 Ubuntu24.04
target. The operator confirmed the exact WSL distribution name `Ubuntu-24.04`,
reported Running with WSL version 2. The guide uses this explicit name throughout.
Native Windows backend execution is not supported.

The archive contains no workspace data, tokens, login credentials, keys or trained
models. Verify its SHA-256 sidecar through a trusted channel. Extract into a short
service-owned Linux directory such as `/opt/allow` with `umask 077` and mode0700.
Preserve normalized archive modes; installation paths must not be group/other
writable. Instance configuration must be mode0600. Keep the archive, Linux files
and private configuration outside the IIS web root.

Render the selected anonymous WSL candidate:

```bash
/usr/bin/python3 -I -B deploy/configure.py --origin https://allow.alloy4.fun \
  --transport wsl --access-mode ANONYMOUS --backend-port 18081 --tunnel-port 18081 \
  --output /opt/allow/generated-instance --install-root /opt/allow --account allow
install -m 600 generated-instance/linux/instance.json deploy/instance.json
/usr/bin/python3 -I -B deploy/linux/setup.py --config deploy/instance.json
```

The last command checks the manifest/prerequisites without creating a database.
Follow the guide before adding `--initialize` for a new isolated installation.
For PRIVATE over SSH, omit the access/transport flags and use the guide's separate
backend/tunnel settings. Legacy four-setting instance files remain PRIVATE/SSH.
ANONYMOUS never publishes a private launch link. Visitors explicitly start their
own temporary workspace; capabilities remain tab-local and are not URL tokens.

Retain `-I -B`. Setup/service reject local application bytecode, unlisted executable
inputs and unsafe ownership. Fresh initialization refuses old generated tools.
One persistent flock protects supported supervisors. Never delete locks or
ownership journals to force recovery. SQL, including lifecycle cleanup, remains
through SQLeanParser; uncertain cleanup retains quarantined capacity. Logical
expiry/deletion does not promise secure erasure of WAL, backups or storage media.

The WSL renderer emits a reviewable user-wide resource proposal; it does not
apply `.wslconfig`, shut down distributions or install a Windows task. Review the
explicit-distribution preflight and foreground supervisor with the target owner.
Confirm NAT localhost mapping and external port isolation before accepting it.
The WSL preflight requires an installed service and account. Start with the guide's
read-only inventory; for a fresh installation leave the service inactive until
`Start-Wsl.ps1` takes ownership. Do not combine that flow with the SSH guide's
`systemctl enable --now` startup command.

The IIS installer supports `-PreflightOnly` and stages the dedicated site with
auto-start disabled. It does not start IIS access or open ingress. Keep staging
stopped/restricted until native TLS/route, two-session isolation, expiry, resource,
restart and recovery checks pass. The observed old public endpoint bypass remains
a target release blocker until corrected deployment acceptance demonstrates denial.

Run `python -I -B deploy/probe_public.py --origin https://allow.alloy4.fun --access-mode ANONYMOUS` only
against an explicitly approved route. This is a partial eight-check unauthenticated
boundary probe: it supplies no real capability and does not test enrollment,
authenticated workspace behavior, isolation, expiry or complete public acceptance.

Fresh Tier-1 advisory validation remains the selected operator experiment;
durable/solver work stays DEFAULT and pooling stays disabled. Prior Tier-1
measurements missed the strict300-ms gate. Target performance remains unmeasured;
set `advisory_profile` to `DEFAULT` for the documented rollback.

This is a private-transfer deployment candidate. Native target acceptance,
commercial release and public artifact redistribution have separate unresolved
gates. Public hosting does not establish redistribution rights.
