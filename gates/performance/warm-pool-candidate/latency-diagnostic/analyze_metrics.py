"""Recompute descriptive ranks from retained raw rows and export the completed diagnostic."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def read(path):
    """Read a completed local evidence artifact without mutating it."""
    return json.loads(Path(path).read_text())


def ranks(values):
    """Compute exact unrounded nearest-rank statistics from raw integer durations."""
    ordered = sorted(values)
    assert ordered and all(type(value) is int and value > 0 for value in ordered)
    return {f'p{p}_ns': ordered[(p * len(ordered) + 99) // 100 - 1] for p in (50, 95, 99)} | {'max_ns': ordered[-1]}


def analyze(report_path, output):
    """Bind exports to terminal PASS and independently replay every published latency rank."""
    report = read(report_path)
    assert report['status'] == 'PASS' and report['terminal_input_recheck'] == 'PASS'
    assert report['production_selection'] == 'DISABLED' and report['promotion_authorized'] is False
    summary, samples = {}, []
    for name, pointer in report['variants'].items():
        run = Path(pointer['path']).parent
        manifest = read(run/'manifest.json')
        raw = read(Path(manifest['copied_root'])/'.gate/evidence/latency-java.json')
        result = report['results'][name]
        measured = [row['durationNs'] for row in raw['rows'] if row['phase'] == 'MEASURED']
        assert all(row['outcome'] == 'SUCCESS' and row['failure'] is None for row in raw['rows'])
        assert all(result['metrics']['latency'][key] == value for key, value in ranks(measured).items())
        for row in raw['rows']:
            samples.append({'variant': name, 'profile': raw['profile'], 'phase': row['phase'], 'index': row['index'],
                            'duration_ns': row['durationNs'], 'cycle_ns': row['cycleDurationNs'],
                            'ready_wait_ns': row['conditionDurationNs'],
                            'admission_phase': (row['admission'] or {}).get('phase', 'FRESH')})
        resources = report['scope_resources'][name]['metrics']
        metrics = result['metrics']
        cpu = metrics['cpu']['measured_usage_usec'] + metrics['cpu']['teardown_tail_usage_usec']
        summary[name] = {'profile': result['profile'], 'metrics': metrics,
                         'peak_mib': int(resources['memory.peak']) / 1048576,
                         'measurement_plus_teardown_cpu_seconds': cpu / 1e6}
    assert len(samples) == 860 and sum(row['phase'] == 'MEASURED' for row in samples) == 720
    output.mkdir(parents=True, exist_ok=False)
    with (output/'samples.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(samples[0]))
        writer.writeheader()
        writer.writerows(samples)
    data = {'status': 'RECOMPUTED_FROM_RAW_ROWS', 'report': str(report_path.resolve()),
            'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(), 'attempts': 860,
            'warmups': 140, 'measured': 720, 'errors': 0, 'variants': summary, 'pairs': report['pairs'],
            'scope': '500-node fresh-ID validation; instrumented component only; assumed CLEAN; no HTTP/SQL.'}
    (output/'summary.json').write_text(json.dumps(data, indent=2) + '\n')
    chart(data, output)


def chart(data, output):
    """Plot separate pairwise latency and CPU costs without merging conditioned profiles."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    variants = data['variants']
    colors = ('#687789', '#176B79')
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), gridspec_kw={'width_ratios': [1.35, 1]})
    for offset, profile, color, label in ((-.18, 'fresh', colors[0], 'Fresh DEFAULT'),
                                         (.18, 'pool', colors[1], 'Pool: automatic refill')):
        latency = [variants[f'pair{i}-{profile}']['metrics']['latency']['p95_ns'] / 1e6 for i in (1, 2, 3)]
        cpu = [variants[f'pair{i}-{profile}']['measurement_plus_teardown_cpu_seconds'] for i in (1, 2, 3)]
        positions = [i + offset for i in range(3)]
        for axis, values in zip(axes, (latency, cpu)):
            bars = axis.bar(positions, values, width=.34, color=color, label=label)
            axis.bar_label(bars, fmt='%.1f', padding=4, fontsize=10)
    for axis in axes:
        axis.set_xticks(range(3), ['Pair 1\nFresh → pool', 'Pair 2\nPool → fresh', 'Pair 3\nFresh → pool'])
        axis.set_xlabel('Independent paired run')
        axis.spines[['top', 'right']].set_visible(False)
        axis.grid(axis='y', alpha=.17)
        axis.set_axisbelow(True)
        axis.set_ylim(0, axis.get_ylim()[1] * 1.14)
    axes[0].set_title('p95 completed-request latency')
    axes[0].set_ylabel('Latency (ms; nearest rank, n = 100 per run)')
    axes[1].set_title('Measurement + teardown CPU')
    axes[1].set_ylabel('CPU seconds per 100 measured requests')
    fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, fontsize=10,
               loc='upper left', bbox_to_anchor=(.075, .91), ncol=2)
    fig.suptitle('Warm JVM pool: 500-node validation', x=.075, ha='left', fontsize=17, fontweight='bold')
    ready = variants['ready-conditioned']['metrics']
    empty = variants['empty-pool']['metrics']
    foot = (f"Separate profiles: READY-conditioned p95 {ready['latency']['p95_ns']/1e6:.1f} ms; "
            f"with preparation wait {ready['all_attempt_terminal_duration']['p95_ns']/1e6:.1f} ms.\n"
            f"Empty-pool demand p95 {empty['latency']['p95_ns']/1e6:.1f} ms; full cycle "
            f"{empty['all_attempt_terminal_duration']['p95_ns']/1e6:.1f} ms (n = 20).\n"
            "Source: measurement-r1, 4 November 2026 · 4-vCPU quota / 6-GiB ceiling · 860 requests, zero errors.\n"
            "Synthetic CLEAN context; HTTP/SQL excluded. Different isolation policies; no production acceptance claim.")
    fig.text(.075, .025, foot, fontsize=9, color='#40464D', linespacing=1.5)
    fig.tight_layout(rect=(.02, .23, .99, .92))
    fig.savefig(output/'latency.png', dpi=170)
    fig.savefig(output/'latency.svg')
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    analyze(args.report, args.output)
