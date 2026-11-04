#!/usr/bin/env python3
"""Record exact local runtime artifacts and embedded notices without claiming clearance."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def sha(data):
    """Compute an integrity digest of already acquired dependency bytes."""
    return hashlib.sha256(data).hexdigest()

def jar_inventory(path):
    """Inventory every embedded Maven identity and notice; fat JARs retain separate identities."""
    contents = path.read_bytes()
    properties = []
    notices = []
    with zipfile.ZipFile(path) as jar:
        for name in sorted(jar.namelist()):
            if name.endswith('/pom.properties'):
                fields = {}
                for line in jar.read(name).decode('utf-8', errors='replace').splitlines():
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        fields[key] = value
                properties.append(fields)
            basename = name.rsplit('/', 1)[-1].lower()
            if ('license' in basename or 'notice' in basename) and not name.endswith('/'):
                notices.append({'entry': name, 'sha256': sha(jar.read(name))})
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(contents), 'sha256': sha(contents),
            'embedded_maven_identities': properties, 'embedded_notices': notices}

def main():
    """Freeze reproducible dependency metadata and the commercial-license limitations."""
    jars = sorted((ROOT / 'backend/target/dependency').glob('*.jar'))
    jars.append(ROOT / 'backend/target/solver/alloy.jar')
    inventory = {'purpose': 'Local development dependency/SBOM evidence; not redistribution clearance',
        'java_baseline': 17, 'maven': '3.9.11', 'spring_boot': '3.5.16',
        'alloy': {'coordinate': 'org.alloytools:org.alloytools.alloy.dist:6.2.0',
                  'distribution': 'Maven Central artifact; not the differing GitHub release binary',
                  'sha256': '6037cbeee0e8423c1c468447ed10f5fcf2f2743a2ffc39cb1c81f2905c0fdb9d',
                  'sat4j_observed': '2.3.1',
                  'source': 'https://repo.maven.apache.org/maven2/org/alloytools/org.alloytools.alloy.dist/6.2.0/'},
        'runtime_jars': [jar_inventory(p) for p in jars],
        'frontend_lock_sha256': sha((ROOT / 'frontend/package-lock.json').read_bytes()),
        'frontend_declared': json.loads((ROOT / 'frontend/package.json').read_text()),
        'license_findings': [
            'Alloy distribution metadata and upstream tagged license notices disagree about MIT/Apache migration; preserve per-artifact provenance and resolve before redistribution.',
            'SAT4J is embedded in the distribution and has its own license choices and obligations; a root-project MIT label does not cover the whole runtime.',
            'No user corpus, JDK distribution or Maven repository is bundled into the source deliverable.',
            'Local development permission does not establish dataset embedding, training, sharing or resale rights.'],
        'commercial_release_cleared': False}
    expected = inventory['alloy']['sha256']
    assert inventory['runtime_jars'][-1]['sha256'] == expected, 'Pinned Alloy bytes differ'
    destination = ROOT / 'gates/g1/dependencies.json'
    destination.write_text(json.dumps(inventory, indent=2) + '\n')
    print(f'Recorded {len(jars)} runtime JARs and the exact frontend lock; commercial clearance remains open.')

if __name__ == '__main__':
    main()
