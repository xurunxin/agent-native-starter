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
    args = parser.parse_args()
    if args.command == 'run':
        report = run_suite(args.project, args.suite)
        with Path(args.output).open('x', encoding='utf-8') as output:
            json.dump(report, output, indent=2, ensure_ascii=False)
            output.write('\n')
        print(json.dumps(summarize(report), indent=2))
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
