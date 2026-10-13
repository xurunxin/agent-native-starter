"""Repeatable task observations and PR-only lesson promotion decisions."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(root, paths):
    data = b''
    for path in sorted(paths):
        if path.is_file():
            data += path.relative_to(root).as_posix().encode() + b'\0' + path.read_bytes() + b'\0'
    return sha(data)


def run_suite(project, manifest):
    """Only run an operator-reviewed suite in a disposable credential-free environment."""
    project, manifest = Path(project).resolve(), Path(manifest).resolve()
    raw = manifest.read_bytes()
    suite = json.loads(raw)
    cases, seen = [], set()
    for case in suite['cases']:
        if case['id'] in seen:
            raise ValueError('Duplicate case ID')
        seen.add(case['id'])
        observation = {k: case[k] for k in ('id', 'category', 'source')}
        observation.update(status='NOT_RUN', seconds=None, tokens=None, cost_usd=None)
        start = time.perf_counter()
        if case['kind'] == 'unittest':
            if not re.fullmatch(r'test_[a-z_]+\.py', case['file']) or not re.fullmatch(r'test_[a-z_]+', case['test']):
                raise ValueError('Invalid trusted unittest entry')
            command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                       '-p', case['file'], '-k', case['test'], '-v']
            if not (project / 'tests' / case['file']).is_file():
                observation.update(status='FAIL', reason='implementation_missing', exit_code=None)
            else:
                result = subprocess.run(command, cwd=project, capture_output=True, timeout=60)
                output = result.stdout + result.stderr
                count = re.search(rb'Ran (\d+) tests?', output)
                observation.update(status='PASS' if result.returncode == 0 and count and int(count[1]) > 0 else 'FAIL',
                                   exit_code=result.returncode, output_sha256=sha(output), command=command)
        elif case['kind'] == 'license':
            license_path = project / 'LICENSE'
            passed = license_path.is_file() and 'MIT License' in license_path.read_text(encoding='utf-8')
            observation['status'] = 'PASS' if passed else 'FAIL'
        elif case['kind'] != 'manual':
            raise ValueError('Unknown case kind')
        if observation['status'] != 'NOT_RUN':
            observation['seconds'] = time.perf_counter() - start
        cases.append(observation)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(project), *args], text=True).strip()
    return {'dataset_digest': sha(raw),
            'environment': {'runner': 'stdlib-contracts-v1', 'python': platform.python_version(),
                            'os': platform.system()},
            'source_sha': git('rev-parse', 'HEAD'), 'source_dirty': bool(git('status', '--porcelain')),
            'rules_digest': file_digest(project, [project / 'AGENTS.md', *project.glob('skills/*/SKILL.md')]),
            'implementation_digest': file_digest(project, project.glob('agent_starter/*.py')),
            'cases': cases}


def validate_run(report):
    if report.get('evidence_kind') == 'instrumented_task_import':
        from .task_runs import digest
        if report.get('report_digest') != digest({k: v for k, v in report.items() if k != 'report_digest'}):
            raise ValueError('Imported metrics/evidence were modified after verification')
    if not isinstance(report.get('source_sha'), str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', report['source_sha']):
        raise ValueError('Source revision is required')
    # An uncommitted worktree cannot be verified by its recorded Git SHA.
    # A missing dirty-state field is UNKNOWN, not equivalent to clean.
    if report.get('source_dirty') is not False:
        raise ValueError('A comparable run requires a clean source revision')
    for field in ('dataset_digest', 'rules_digest', 'implementation_digest'):
        if not isinstance(report.get(field), str) or not re.fullmatch(r'[a-f0-9]{64}', report[field]):
            raise ValueError('Missing digest: ' + field)
    if not isinstance(report.get('environment'), dict) or not report['environment']:
        raise ValueError('Environment is required')
    cases = report.get('cases')
    if not isinstance(cases, list) or not cases:
        raise ValueError('Task observations required')
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get('id'), str) or not case['id'] or case['id'] in seen:
            raise ValueError('Unique case IDs required')
        seen.add(case['id'])
        if not case.get('category') or case.get('status') not in ('PASS', 'FAIL', 'NOT_RUN'):
            raise ValueError('Invalid category or outcome')
        for field in ('seconds', 'tokens', 'cost_usd'):
            value = case.get(field)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError('Invalid measured metric: ' + field)
        if case['status'] != 'NOT_RUN' and case.get('seconds') is None:
            raise ValueError('Measured cases require execution duration')
    return {c['id']: c for c in cases}


def summarize(report):
    measured = [c for c in report['cases'] if c['status'] != 'NOT_RUN']
    passed = sum(c['status'] == 'PASS' for c in measured)
    summary = {'measured': len(measured), 'success_rate': passed / len(measured) if measured else None,
               'error_rate': (len(measured) - passed) / len(measured) if measured else None,
               'not_run': [c['id'] for c in report['cases'] if c['status'] == 'NOT_RUN']}
    for field in ('seconds', 'tokens', 'cost_usd'):
        summary[field] = sum(c[field] for c in measured) if measured and all(
            c.get(field) is not None for c in measured) else 'NOT_MEASURED'
    summary['categories'] = {}
    for category in sorted({c['category'] for c in report['cases']}):
        subset = [c for c in measured if c['category'] == category]
        summary['categories'][category] = {'measured': len(subset), 'passed': sum(c['status'] == 'PASS' for c in subset)}
    return summary


def compare(baseline, candidate):
    a, b = validate_run(baseline), validate_run(candidate)
    if baseline['dataset_digest'] != candidate['dataset_digest'] or baseline['environment'] != candidate['environment']:
        raise ValueError('Same dataset and execution environment required')
    if set(a) != set(b) or any(a[k]['category'] != b[k]['category'] or
                             (a[k]['status'] == 'NOT_RUN') != (b[k]['status'] == 'NOT_RUN') for k in a):
        raise ValueError('Same scenarios, categories and measured coverage required')
    return {'baseline': summarize(baseline), 'candidate': summarize(candidate),
            'rules_changed': baseline['rules_digest'] != candidate['rules_digest'],
            'implementation_changed': baseline['implementation_digest'] != candidate['implementation_digest'],
            'dataset_digest': baseline['dataset_digest'],
            'measurement_kind': baseline['environment'].get('measurement_kind', 'offline_contract')}



def compare_replicates(pairs):
    """Summarize *observed* paired task runs; never claim a causal Skill effect.

    Reuses imported evidence and compare() rather than introducing another runner.
    One pair is useful for diagnosis but cannot satisfy repeated-task acceptance.
    """
    if not isinstance(pairs, list) or not pairs:
        raise ValueError('At least one baseline/candidate pair is required')
    identities, seen_runs = None, set()
    observations = {'baseline': [], 'candidate': []}
    comparisons = []
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError('Each trial needs baseline and candidate reports')
        baseline, candidate = pair
        result = compare(baseline, candidate)
        if any(r.get('evidence_kind') != 'instrumented_task_import' or
               r['environment'].get('measurement_kind') != 'observed_task_run'
               for r in (baseline, candidate)):
            raise ValueError('Synthetic/offline results cannot establish actual task effects')
        if not result['rules_changed'] or result['implementation_changed']:
            raise ValueError('Changed code or unchanged rules confound the instruction comparison')
        current = (
            baseline['source_sha'], candidate['source_sha'],
            baseline['rules_digest'], candidate['rules_digest'],
            baseline['implementation_digest'], baseline['dataset_digest'],
            json.dumps(baseline['environment'], sort_keys=True),
        )
        if identities is not None and current != identities:
            raise ValueError('All trials must use the same frozen task, rules and environment')
        identities = current
        for name, report in (('baseline', baseline), ('candidate', candidate)):
            for case in report['cases']:
                run_id = case.get('run_id')
                if not isinstance(run_id, str) or not run_id or run_id in seen_runs:
                    raise ValueError('Distinct run IDs are required for every actual attempt')
                seen_runs.add(run_id)
                observations[name].append(case)
        comparisons.append(result)

    def aggregate(cases):
        measured = [c for c in cases if c['status'] != 'NOT_RUN']
        values = {'input_tokens': [], 'output_tokens': [], 'cached_input_tokens': [],
                  'total_tokens': [], 'cost_usd': [], 'seconds': []}
        for case in measured:
            usage = case.get('usage') or {}
            for name in values:
                values[name].append(case.get('seconds') if name == 'seconds' else usage.get(name))
        return {'attempted': len(cases), 'measured': len(measured),
                'passed': sum(c['status'] == 'PASS' for c in measured),
                'failed': sum(c['status'] == 'FAIL' for c in measured),
                'not_run': len(cases) - len(measured),
                'usage': {name: (sum(data) if measured and all(v is not None for v in data)
                                 else 'NOT_MEASURED') for name, data in values.items()}}

    totals = {name: aggregate(cases) for name, cases in observations.items()}
    complete = (len(pairs) >= 2 and all(v['not_run'] == 0 and v['measured'] > 0
                                       for v in totals.values()))
    return {'measurement_kind': 'observed_task_run',
            'paired_trials': len(pairs), 'status': 'RECORDED' if complete else 'INCOMPLETE',
            'baseline': totals['baseline'], 'candidate': totals['candidate'],
            'source_identity': {'baseline_sha': identities[0], 'candidate_sha': identities[1],
                                'dataset_digest': identities[5]},
            'causal_effect': 'NOT_ESTABLISHED',
            'limits': [
                'Allocation order, randomness, cache and human intervention not authenticated',
                'Repeated observations alone do not establish a statistically generalizable effect',
                'Quality requires an independently reviewed fixed task oracle',
            ]}



def validate_lesson(lesson):
    required = ('root_cause', 'evidence', 'reproduction', 'scope', 'prevention', 'checks', 'observed', 'review_after')
    return [field for field in required if not lesson.get(field)]


def promotion(lesson, comparison, *, security_boundary=False):
    """Decision only: never edits Skills, AGENTS.md or grants permissions."""
    if validate_lesson(lesson) or not comparison.get('candidate', {}).get('measured'):
        return 'insufficient_evidence'
    if security_boundary:
        return 'human_review_required'
    return 'draft_pr_required'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run')
    run.add_argument('--project', required=True)
    run.add_argument('--suite', required=True)
    run.add_argument('--output', required=True)
    comparison = commands.add_parser('compare')
    comparison.add_argument('baseline')
    comparison.add_argument('candidate')
    comparison.add_argument('--output')
    repeats = commands.add_parser('replicates')
    repeats.add_argument('--pair', nargs=2, action='append', required=True,
                          metavar=('BASELINE_REPORT', 'CANDIDATE_REPORT'))
    repeats.add_argument('--output')
    args = parser.parse_args()
    if args.command == 'run':
        report = run_suite(args.project, args.suite)
        with Path(args.output).open('x', encoding='utf-8') as output:
            json.dump(report, output, indent=2, ensure_ascii=False)
            output.write('\n')
        print(json.dumps(summarize(report), indent=2))
    else:
        if args.command == 'replicates':
            pairs = [[json.loads(Path(path).read_text(encoding='utf-8')) for path in pair]
                     for pair in args.pair]
            result = compare_replicates(pairs)
        else:
            result = compare(json.loads(Path(args.baseline).read_text(encoding='utf-8')),
                             json.loads(Path(args.candidate).read_text(encoding='utf-8')))
        if args.output:
            with Path(args.output).open('x', encoding='utf-8') as output:
                json.dump(result, output, indent=2)
                output.write('\n')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
