#!/usr/bin/env python3
"""Render a new IIS/Linux instance without installing services or changing IIS."""
import sys
if not sys.flags.isolated or not sys.flags.dont_write_bytecode:
    raise SystemExit('Invoke with /usr/bin/python3 -I -B')

import argparse
import os
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def origin(value):
    """Require one canonical ASCII DNS HTTPS origin without path or implicit authority."""
    pattern = r'https://([a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+)(?::([1-9][0-9]{0,4}))?'
    match = re.fullmatch(pattern, value, flags=re.ASCII)
    if not match or len(match[1]) > 253 or any(len(label) > 63 for label in match[1].split('.')):
        raise ValueError('Use a canonical lowercase HTTPS DNS origin, without a path')
    if all(label.isdigit() for label in match[1].split('.')):
        raise ValueError('IP literal origins are not supported')
    if match[2] and (int(match[2]) == 443 or int(match[2]) > 65535):
        raise ValueError('Omit default port 443; explicit ports must be within 1..65535')
    return value


def port(value):
    """Accept an unprivileged, non-ambiguous local TCP port."""
    result = int(value)
    if not 1024 <= result <= 65535:
        raise ValueError('Local ports must be between 1024 and 65535')
    return result


def install_root(value):
    """Keep generated systemd arguments simple and private socket paths short."""
    if not re.fullmatch(r'/[a-zA-Z0-9_/-]+', value) or len(value) > 40:
        raise ValueError('Use a short absolute installation path, for example /opt/allow')
    if '//' in value or value.endswith('/') or '..' in Path(value).parts:
        raise ValueError('Installation path must be canonical')
    return value


def reject(rules, name, variable, expected):
    """Emit a deterministic rejection rule ahead of all proxy routing."""
    rule = ET.SubElement(rules, 'rule', name=name, stopProcessing='true')
    ET.SubElement(rule, 'match', url='.*')
    conditions = ET.SubElement(rule, 'conditions')
    ET.SubElement(conditions, 'add', input=variable, pattern=expected, negate='true', ignoreCase='false')
    ET.SubElement(rule, 'action', type='CustomResponse', statusCode='403', statusReason='Forbidden',
                  statusDescription='Deployment routing rejected')


def web_config(public_origin, tunnel_port):
    """Generate an IIS site that forwards unchanged credentials and Origin through ARR."""
    root = ET.Element('configuration')
    server = ET.SubElement(root, 'system.webServer')
    rules = ET.SubElement(ET.SubElement(server, 'rewrite'), 'rules')
    ET.SubElement(rules, 'clear')
    reject(rules, 'Require HTTPS', '{HTTPS}', '^on$')
    reject(rules, 'Require configured host', '{HTTP_HOST}', '^' + public_origin[8:].replace('.', r'\.') + '$')
    rule = ET.SubElement(rules, 'rule', name='Allow through local SSH tunnel', stopProcessing='true')
    ET.SubElement(rule, 'match', url='(.*)')
    ET.SubElement(rule, 'action', type='Rewrite', url=f'http://127.0.0.1:{tunnel_port}/{{R:1}}',
                  appendQueryString='true', logRewrittenUrl='false')
    ET.SubElement(server, 'caching', enabled='false', enableKernelCache='false')
    ET.SubElement(server, 'httpErrors', existingResponse='PassThrough')
    filtering = ET.SubElement(ET.SubElement(server, 'security'), 'requestFiltering')
    ET.SubElement(filtering, 'requestLimits', maxAllowedContentLength='3145728')
    ET.indent(root)
    return ET.tostring(root, encoding='unicode', xml_declaration=True) + '\n'


def service_unit(root, account, transport="ssh", installation_slot="PRIMARY"):
    """Keep PostgreSQL, SQLeanParser, Spring and their children in one bounded unit."""
    return f'''[Unit]
Description={"Allow anonymous replacement behind IIS" if installation_slot == "PUBLIC_REPLACEMENT" else "Allow private workspace behind IIS"}
After=network.target

[Service]
Type=simple
User={account}
Group={account}
WorkingDirectory={root}
UMask=0077
ExecStart=/usr/bin/python3 -I -B {root}/deploy/linux/service.py --config {root}/deploy/instance.json
KillMode=control-group
TimeoutStopSec=60
Restart=on-failure
RestartSec=5
CPUQuota=400%
MemoryHigh={"3G" if transport == "wsl" else "5G"}
MemoryMax={"4G" if transport == "wsl" else "6G"}
MemorySwapMax=0
TasksMax=512

[Install]
WantedBy=multi-user.target
'''


def validate_slot(slot, access, transport, root, account, backend, tunnel):
    """Bind the replacement selector to one closed, independently owned installation."""
    if slot not in ('PRIMARY', 'PUBLIC_REPLACEMENT'):
        raise ValueError('Unknown installation slot')
    if slot == 'PRIMARY' and (root == '/opt/allow-public' or account == 'allow-public'):
        raise ValueError('Reserved public root/account requires PUBLIC_REPLACEMENT')
    if slot == 'PUBLIC_REPLACEMENT' and (access, transport, root, account, backend, tunnel) != (
            'ANONYMOUS', 'wsl', '/opt/allow-public', 'allow-public', 18081, 18081):
        raise ValueError('PUBLIC_REPLACEMENT requires its exact isolated installation tuple')


def render(args):
    """Write only a new configuration directory; never replace existing instance files."""
    public = origin(args.origin)
    transport = getattr(args, "transport", "ssh")
    access = getattr(args, "access_mode", "PRIVATE")
    if transport not in ("ssh", "wsl") or access not in ("PRIVATE", "ANONYMOUS"):
        raise ValueError("Unknown deployment profile")
    tunnel, backend = port(args.tunnel_port), port(args.backend_port)
    root = install_root(args.install_root)
    slot = getattr(args, "installation_slot", "PRIMARY")
    validate_slot(slot, access, transport, root, args.account, backend, tunnel)
    if transport == "wsl" and (tunnel != 18081 or backend != 18081):
        raise ValueError("WSL requires both loopback ports to be 18081")
    if not re.fullmatch(r'[a-z_][a-z0-9_-]{0,30}', args.account):
        raise ValueError('Use a dedicated simple Linux account name')
    destination = Path(args.output)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    (destination/'iis').mkdir(mode=0o700)
    (destination/'linux').mkdir(mode=0o700)
    config = {'public_origin': public, 'tunnel_port': tunnel, 'backend_port': backend,
              'advisory_profile': args.advisory_profile, 'access_mode': access, 'transport': transport,
              'installation_slot': slot, 'ai_mode': 'OFF'}
    fd = os.open(destination/'linux/instance.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(json.dumps(config, indent=2) + '\n')
    unit = 'allow-public.service' if slot == 'PUBLIC_REPLACEMENT' else 'allow.service'
    (destination/'linux'/unit).write_text(service_unit(root, args.account, transport, slot))
    (destination/'iis/web.config').write_text(web_config(public, tunnel))
    if transport == 'wsl':
        (destination/'wslconfig.proposal').write_text('[wsl2]\nmemory=5GB\nprocessors=4\nswap=0\nlocalhostForwarding=true\n')
    (destination/'instance-summary.json').write_text(json.dumps(config | {'install_root': root,
        'account': args.account, 'target_iis_acceptance': 'OPEN'}, indent=2) + '\n')


def main():
    """Parse nonsecret operator values and render reviewable deployment configuration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--installation-slot', choices=['PRIMARY', 'PUBLIC_REPLACEMENT'], default='PRIMARY')
    parser.add_argument('--access-mode', choices=['PRIVATE', 'ANONYMOUS'], default='PRIVATE')
    parser.add_argument('--transport', choices=['ssh', 'wsl'], default='ssh')
    parser.add_argument('--output', required=True)
    parser.add_argument('--install-root', default='/opt/allow')
    parser.add_argument('--account', default='allow')
    parser.add_argument('--backend-port', type=int, default=8080)
    parser.add_argument('--tunnel-port', type=int, default=18081)
    parser.add_argument('--advisory-profile', choices=['DEFAULT', 'DOCUMENT_ADVISORY_TIER1'],
                        default='DOCUMENT_ADVISORY_TIER1')
    render(parser.parse_args())


if __name__ == '__main__':
    main()
