#!/usr/bin/env python3
"""Exercise the assembled egraph workbench over real authenticated local HTTP."""
import json
from pathlib import Path
import re
from smoke_local import Client

ROOT = Path(__file__).resolve().parents[1]


def checked_islands(result):
    """Require honest checked extraction and its exact anonymous module/root binding."""
    canonical = result['canonical']
    graph = canonical['egraph']
    assert graph['profile'] == 'allow-egraph-v1'
    checked = [island for island in graph['islands'] if island['certificateStatus'] == 'CHECKED']
    assert checked, 'No checked egraph root'
    for island in checked:
        certificate = island['certificate']
        assert certificate['context']['module'] == canonical['payload']
        assert certificate['context']['rootPath'] == island['rootPath']
        assert certificate['rulesetDigest'] == graph['rulesetDigest']
        assert certificate['input'] == island['input'] and certificate['extracted'] == island['extracted']
        assert island['extractedCost'] <= island['inputCost']
        preview = island['preview']
        shown = sum(len(group['nodes']) for group in preview['classes'])
        assert len(preview['classes']) <= 24 and shown <= 48
        assert preview['truncated'] == (shown < island['stats']['nodes'])
        conclusion = certificate['steps'][certificate['conclusion']]
        assert conclusion['left'] == island['input'] and conclusion['right'] == island['extracted']
    return checked


def summary(result):
    """Retain only bounded numeric outcome evidence, excluding source and launch authority."""
    return {'solver_status': result['status'], 'islands': [
        {key: island[key] for key in ['rootPath', 'certificateStatus', 'stopReason', 'inputCost', 'extractedCost', 'stats']}
        for island in result['canonical']['egraph']['islands']]}


def main():
    """Check synthetic egraph integration without importing or exporting dataset sources."""
    client = Client()
    status, shell = client.request('/', authorized=False)
    assert status == 200 and '<div id="root">' in shell
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', shell)
    assert len(assets) >= 2
    for asset in assets:
        assert client.request(asset, authorized=False)[0] == 200
    for headers in [{}, {'Authorization': 'Bearer invalid'}, {'Origin': 'https://hostile.invalid'}, {'Host': 'hostile.invalid'}]:
        assert client.request('/api/config', headers=headers, authorized=bool(headers))[0] == 403
    source = 'sig Person {} pred model { some Person and (some Person or no Person) } run model for 3'
    first = client.terminal(client.submit(source))
    assert first['status'] == 'SAT' and first['witness'] is not None
    checked = checked_islands(first)
    assert any(item['extractedCost'] < item['inputCost'] for item in checked)
    assert any(item['preview'].get('edges') for item in checked)
    renamed = client.terminal(client.submit(source.replace('Person', 'PrivateBusinessName').replace('model', 'privatePredicate')))
    assert renamed['status'] == 'SAT'
    checked_islands(renamed)
    for key in ['payload', 'sha256', 'features', 'egraph']:
        assert first['canonical'][key] == renamed['canonical'][key], key
    assert 'PrivateBusinessName' not in json.dumps(renamed['canonical'])
    assert 'PrivateBusinessName' in json.dumps(renamed['witness'])
    relation = client.terminal(client.submit('sig Item {} pred model { some (Item & Item) } run model for 3'))
    assert relation['status'] == 'SAT'
    assert any(item['extractedCost'] < item['inputCost'] for item in checked_islands(relation))
    validation = client.terminal(client.submit(source, 'VALIDATE'))
    assert validation['status'] == 'VALIDATED' and validation['witness'] is None
    checked_islands(validation)
    unsupported = client.terminal(client.submit('one sig Unique {} run { some Unique } for 3'))
    assert unsupported['status'] == 'SAT'
    assert unsupported['canonical']['status'] == 'UNSUPPORTED_CANONICAL'
    assert unsupported['canonical']['egraph'] is None
    report = {'status': 'PASS', 'classification': 'TESTED_HTTP_INTEGRATION_NOT_FORMAL_REFINEMENT',
        'checks': ['Built React assets served', 'Missing/wrong bearer and hostile Host/Origin rejected',
            'Real SAT4J outcome coexists with cheaper checked Boolean extraction',
            'Relation idempotence lifts through SOME with a checked certificate',
            'Certificate endpoints/module/path/ruleset match authenticated result',
            'Alpha-renaming preserves exact structural bytes/features and complete egraph output',
            'Readable witness names remain separate from anonymous optimization data',
            'Validation computes egraphs without inventing SAT evidence',
            'Unsupported canonical syntax preserves solver result and has no raw egraph fallback'],
        'boolean_example': summary(first), 'relation_example': summary(relation),
        'browser_qa': 'NOT_RUN: extension inventory empty; Chrome creation returned Browser is not available',
        'dataset_sources_used': False, 'launch_capability_recorded': False}
    (ROOT / 'gates/egraph/http-smoke.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
