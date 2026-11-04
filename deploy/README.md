# Allow: private IIS + Linux deployment package

Read [the deployment guide](docs/iis-deployment.md) before installation.
IIS provides HTTPS on Windows; a strict SSH tunnel reaches the existing Linux
loopback backend. Native Windows backend execution is not supported.

The archive contains no workspace data, tokens, keys or trained models. Verify
the archive SHA-256 sidecar obtained over a trusted channel, extract into a short
private Linux directory such as `/opt/allow`, and preserve executable modes.
Do not put the archive or extracted Linux files in an IIS web root.

Generate nonsecret instance files:

```bash
/usr/bin/python3 deploy/configure.py --origin https://allow.example.com \
  --output /opt/allow/generated-instance --install-root /opt/allow
cp generated-instance/linux/instance.json deploy/instance.json
/usr/bin/python3 deploy/linux/setup.py --config deploy/instance.json
```

The last command verifies the manifest and host prerequisites without creating
a database. Add `--initialize` only for the explicit fresh-workspace setup in
the guide. Install the rendered systemd unit, then configure the SSH tunnel and
the dedicated IIS site using the included PowerShell scripts.

Advisory validation selects fresh Tier-1 JVMs as an operator opt-in experiment;
durable/solver paths retain DEFAULT and warm pooling remains disabled. Tier-1
was faster in the prior paired HTTP measurement, but missed the 300-ms target.
Set `advisory_profile` to `DEFAULT` in the instance configuration to roll back.

Windows/IIS execution and actual production-host acceptance remain open. This
is an operator-private transfer artifact, not commercial-release approval.
