"""Replay frozen evidence offline; never invoke a model or network."""
import json
from pathlib import Path
import subprocess
import sys

repository = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repository))
from agent_starter.task_runs import freeze_rules, import_results
from agent_starter.evaluation import compare

evidence = Path(__file__).resolve().parent
target = Path(sys.argv[1]).resolve()
target.mkdir(parents=True, exist_ok=False)
reports = {}
for label in ('old', 'new'):
    project = target / label
    subprocess.run(['git', 'clone', '--branch', 'main', str(evidence / (label + '-rules.bundle')),
                    str(project)], check=True, capture_output=True)
    def read(suffix):
        return json.loads((evidence / (label + suffix)).read_text(encoding='utf-8'))
    snapshot = read('-snapshot.json')
    assert freeze_rules(project) == snapshot
    report = import_results(project, snapshot,
                            json.loads((evidence / 'suite.json').read_text(encoding='utf-8')),
                            read('-results.json'), evidence / 'artifacts')
    assert report == read('-report.json')
    reports[label] = report
    print(label, 'freeze/import MATCH')
assert compare(reports['old'], reports['new']) == json.loads(
    (evidence / 'comparison.json').read_text(encoding='utf-8'))
print('comparison MATCH')
