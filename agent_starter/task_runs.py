"""Frozen rule bundles and evidence-checked instrumented task result import."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from .evaluation import summarize, validate_run
from .recovery import safe_path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def is_sha(value, length=64):
    return isinstance(value, str) and bool(re.fullmatch('[0-9a-f]{' + str(length) + '}', value))


def git(project, *args):
    result = subprocess.run(['git', '-C', str(project), *args], capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError('Git evidence read failed')
    return result.stdout


def freeze_rules(project, revision=None):
    project = Path(project).resolve()
    if Path(git(project, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != project:
        raise ValueError('Use the repository root')
    if git(project, 'status', '--porcelain').strip():
        raise ValueError('Freeze only a clean committed source')
    revision = revision or git(project, 'rev-parse', 'HEAD').decode().strip()
    if not (is_sha(revision, 40) or is_sha(revision)):
        raise ValueError('A full fixed source SHA is required')
    if git(project, 'rev-parse', revision + '^{commit}').decode().strip() != revision:
        raise ValueError('Source commit mismatch')
    names = git(project, 'ls-tree', '-rz', '--name-only', revision).decode('utf-8').split('\0')
    def collect(selected):
        return [{'path': name, 'sha256': hashlib.sha256(git(project, 'show', revision + ':' + name)).hexdigest()}
                for name in sorted(selected)]
    rules = collect(name for name in names if name in ('AGENTS.md', 'agent-project.yaml') or name.startswith('skills/'))
    if not any(f['path'] == 'AGENTS.md' for f in rules):
        raise ValueError('AGENTS.md is required in the frozen rule bundle')
    implementation = collect(name for name in names if name.startswith('agent_starter/') and name.endswith('.py'))
    snapshot = {'schema_version': 1, 'source_sha': revision, 'source_dirty': False,
                'rules_files': rules, 'rules_digest': digest(rules),
                'implementation_digest': digest(implementation)}
    return {**snapshot, 'snapshot_digest': digest(snapshot)}


def environment(value):
    required = {'runner', 'version', 'provider', 'model', 'parameters', 'measurement_kind'}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError('Explicit runner/model/environment identity required')
    if value['measurement_kind'] not in ('synthetic_fixture', 'observed_task_run'):
        raise ValueError('Declare fixture versus actual task observations')
    for name in ('runner', 'version', 'provider', 'model'):
        if not isinstance(value[name], str) or not re.fullmatch(r'[A-Za-z0-9_./:-]{1,128}', value[name]):
            raise ValueError('Invalid environment identity')
    params = value['parameters']
    if not isinstance(params, dict) or set(params) - {'temperature', 'top_p', 'seed', 'max_output_tokens'}:
        raise ValueError('Only nonsecret generation parameters are accepted')
    for metric in params.values():
        if type(metric) not in (int, float) or not math.isfinite(metric) or metric < 0:
            raise ValueError('Invalid generation parameter')
    return value


def artifact(root, descriptor):
    if not isinstance(descriptor, dict) or set(descriptor) != {'path', 'sha256'} or not is_sha(descriptor['sha256']):
        raise ValueError('Artifact path and SHA256 required')
    path = safe_path(root, descriptor['path'])
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError('Artifact absent or exceeds 1 MiB budget')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != descriptor['sha256']:
        raise ValueError('Artifact digest mismatch')
    return data


def usage(value):
    fields = {'input_tokens', 'output_tokens', 'total_tokens', 'cost_usd'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('Explicit usage fields, including null unknowns, required')
    for key in fields - {'cost_usd'}:
        if value[key] is not None and (type(value[key]) is not int or value[key] < 0):
            raise ValueError('Token counts must be nonnegative integers or null')
    cost = value['cost_usd']
    if cost is not None and (type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0):
        raise ValueError('Cost must be measured nonnegative USD or null')
    if all(value[k] is not None for k in ('input_tokens', 'output_tokens', 'total_tokens')):
        if value['input_tokens'] + value['output_tokens'] != value['total_tokens']:
            raise ValueError('Token total mismatch')
    return value


def import_results(project, snapshot, suite, results, artifacts_root):
    if snapshot != freeze_rules(project, snapshot.get('source_sha')):
        raise ValueError('Frozen rule/source evidence mismatch')
    root = Path(artifacts_root)
    if root.is_symlink() or root.is_junction() or not root.is_dir():
        raise ValueError('Trusted artifact directory required')
    root = root.resolve()
    tasks = suite.get('tasks')
    if suite.get('schema_version') != 1 or not isinstance(tasks, list) or not tasks:
        raise ValueError('Versioned task suite required')
    expected = {}
    for task in tasks:
        if set(task) != {'id', 'category', 'input_sha256'} or not isinstance(task['id'], str) or not task['id'] or task['id'] in expected or not isinstance(task['category'], str) or not task['category'] or not is_sha(task['input_sha256']):
            raise ValueError('Unique classified tasks with frozen input digests required')
        expected[task['id']] = task
    dataset = digest(suite)
    env = environment(results.get('environment'))
    header = {key: snapshot[key] for key in ('source_sha', 'rules_digest', 'snapshot_digest')}
    header['dataset_digest'] = dataset
    if results.get('schema_version') != 1 or any(results.get(k) != v for k, v in header.items()):
        raise ValueError('Result source/rules/dataset does not match the frozen run')
    runs = results.get('cases')
    if not isinstance(runs, list) or len(runs) != len(expected):
        raise ValueError('Complete task coverage required')
    cases, seen, run_ids = [], set(), set()
    for run in runs:
        task_id, run_id = run.get('id'), run.get('run_id')
        if task_id not in expected or task_id in seen or not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', run_id) or run_id in run_ids:
            raise ValueError('Unique task/run identity required')
        seen.add(task_id)
        run_ids.add(run_id)
        task = expected[task_id]
        binding = {**header, 'task_id': task_id, 'run_id': run_id, 'input_sha256': task['input_sha256']}
        if run.get('input_sha256') != task['input_sha256']:
            raise ValueError('Input scenario identity changed')
        metrics = usage(run.get('usage'))
        state, seconds, errors = run.get('status'), run.get('seconds'), run.get('errors')
        descriptors = run.get('artifacts')
        if state == 'NOT_RUN':
            if seconds is not None or errors is not None or any(v is not None for v in metrics.values()) or descriptors != {} or not run.get('reason'):
                raise ValueError('NOT_RUN cannot carry measured metrics or verification claims')
            verified = {}
        else:
            if state not in ('PASS', 'FAIL') or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0 or type(errors) is not int or errors < 0 or (state == 'PASS' and errors != 0) or (state == 'FAIL' and errors == 0):
                raise ValueError('Invalid outcome/duration/error metrics')
            if not isinstance(descriptors, dict) or set(descriptors) != {'input', 'output', 'verification', 'usage'}:
                raise ValueError('Input/output/verification/usage evidence required')
            raw = {name: artifact(root, item) for name, item in descriptors.items()}
            if hashlib.sha256(raw['input']).hexdigest() != task['input_sha256']:
                raise ValueError('Actual input bytes do not match the scenario')
            verification = json.loads(raw['verification'])
            receipt = json.loads(raw['usage'])
            if verification.get('binding') != binding or any(verification.get(k) != v for k, v in
                    {'status': state, 'seconds': seconds, 'errors': errors}.items()):
                raise ValueError('Outcome verification is not bound to this run')
            if receipt.get('binding') != binding or receipt.get('environment') != env or receipt.get('usage') != metrics:
                raise ValueError('Usage receipt/runner identity mismatch')
            verified = {name: dict(item) for name, item in descriptors.items()}
        cases.append({'id': task_id, 'category': task['category'], 'run_id': run_id, 'status': state,
                      'seconds': seconds, 'errors': errors, 'tokens': metrics['total_tokens'],
                      'cost_usd': metrics['cost_usd'], 'usage': dict(metrics),
                      'input_sha256': task['input_sha256'], 'artifacts': verified})
    report = {'source_sha': snapshot['source_sha'], 'source_dirty': False, 'rules_digest': snapshot['rules_digest'],
              'snapshot_digest': snapshot['snapshot_digest'], 'implementation_digest': snapshot['implementation_digest'],
              'dataset_digest': dataset, 'environment': env, 'evidence_kind': 'instrumented_task_import',
              'results_digest': digest(results), 'cases': cases}
    report['report_digest'] = digest(report)
    validate_run(report)
    return report


def write_report(project, path, report):
    path = Path(path).resolve()
    if path.is_relative_to(Path(project).resolve()):
        raise ValueError('Write evidence outside the source repository')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    freeze = commands.add_parser('freeze')
    freeze.add_argument('project')
    freeze.add_argument('--revision')
    freeze.add_argument('--output', required=True)
    ingest = commands.add_parser('import')
    ingest.add_argument('project')
    for name in ('snapshot', 'suite', 'results', 'artifacts', 'output'):
        ingest.add_argument('--' + name, required=True)
    args = parser.parse_args()
    def read(name):
        return json.loads(Path(getattr(args, name)).read_text(encoding='utf-8'))
    if args.command == 'freeze':
        report = freeze_rules(args.project, args.revision)
        write_report(args.project, args.output, report)
        print(json.dumps({k: report[k] for k in ('source_sha', 'rules_digest', 'snapshot_digest')}))
    else:
        report = import_results(args.project, read('snapshot'), read('suite'), read('results'), args.artifacts)
        write_report(args.project, args.output, report)
        print(json.dumps({'measurement_kind': report['environment']['measurement_kind'],
                          'summary': summarize(report)}, indent=2))


if __name__ == '__main__':
    main()
