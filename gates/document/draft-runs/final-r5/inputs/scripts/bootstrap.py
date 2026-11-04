#!/usr/bin/env python3
"""Install the pinned local Maven tool after verifying official SHA-512 bytes."""
from pathlib import Path
import hashlib
import os
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.9.11'
SHA512 = 'bcfe4fe305c962ace56ac7b5fc7a08b87d5abd8b7e89027ab251069faebee516b0ded8961445d6d91ec1985dfe30f8153268843c89aa392733d1a3ec956c9978'
CHECKSTYLE_SHA256 = 'afcba25e869016442972ec4513a8c06c812edf68f511c88ef497de00c3383917'

def checkstyle():
    """Obtain verified Checkstyle bytes so every default build runs Java negative fixtures."""
    destination = Path(os.environ.get('ALLOW_CHECKSTYLE_JAR',
        ROOT / '.tools/checkstyle-10.21.2-all.jar'))
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        url = 'https://github.com/checkstyle/checkstyle/releases/download/checkstyle-10.21.2/checkstyle-10.21.2-all.jar'
        destination.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    if hashlib.sha256(destination.read_bytes()).hexdigest() != CHECKSTYLE_SHA256:
        raise RuntimeError('Checkstyle integrity mismatch; refusing fixture execution')
    return destination.resolve()

def maven():
    """Return the pinned executable, downloading only the official checked archive."""
    tools = ROOT / '.tools'
    tools.mkdir(exist_ok=True)
    name = f'apache-maven-{VERSION}-bin.tar.gz'
    archive = tools / name
    if not archive.exists():
        url = f'https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/{VERSION}/{name}'
        archive.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    if hashlib.sha512(archive.read_bytes()).hexdigest() != SHA512:
        raise RuntimeError('Maven archive integrity mismatch; refusing extraction')
    executable = tools / f'apache-maven-{VERSION}/bin/mvn'
    if not executable.exists():
        with tarfile.open(archive) as bundle:
            for member in bundle.getmembers():
                if tools.resolve() not in (tools / member.name).resolve().parents:
                    raise RuntimeError('Unsafe Maven archive path')
                if member.issym() or member.islnk():
                    raise RuntimeError('Unexpected Maven archive link')
            bundle.extractall(tools)
    return executable

if __name__ == '__main__':
    print(maven())
