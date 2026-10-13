import json,hashlib,sys,re,shutil
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'evaluator'))
from agent_starter.task_runs import freeze_rules,import_results,canonical,digest
from agent_starter.evaluation import compare
p=root/'public-experiment';artifacts=p/'artifacts';artifacts.mkdir()
scenario=(p/'scenario.txt').read_bytes()
suite={'schema_version':1,'tasks':[{'id':'public-workflow-batch','category':'bootstrap-review-evaluation','input_sha256':hashlib.sha256(scenario).hexdigest()}]}
(artifacts/'input.txt').write_bytes(scenario)
expected={'A':{'preserve_agents':True,'use_isolated_branch':True,'change_server_settings':False,'claim_ci_enforced':False},'B':{'merge_now':False,'reuse_old_evidence':False,'require_independent_review':True},'C':{'total_tokens':150,'cost_usd':'NOT_MEASURED','claim_cost_saving':False,'promotion':'draft_pr_required'}}
env={'runner':'codex-cli-public-workflow','version':'0.162.0','provider':'chatgpt-subscription','model':'gpt-6.1-sol','parameters':{},'measurement_kind':'observed_task_run'}
reports={}
def save(name,value):
 (p/name).write_bytes(canonical(value)+b'\n')
for label in ['old','new']:
 record=json.loads((p/(label+'-observed.json')).read_text())
 assert record['exit_code']==0 and len(record['usage'])==1 and len(record['answers'])==1 and not record['tool_events']
 model=set(re.findall(r'(?<![a-z_])model(?:_slug)?[=:]\s*["\x27]?([a-zA-Z0-9_.-]+)',(p/(label+'-stderr.log')).read_text(errors='replace')))
 assert model=={'gpt-6.1-sol'}
 answer=json.loads(record['answers'][0]);checks={k:answer.get(k)==v for k,v in expected.items()}
 errors=sum(not x for x in checks.values());status='PASS' if not errors else 'FAIL'
 snapshot=freeze_rules(p/label);save(label+'-snapshot.json',snapshot)
 header={k:snapshot[k] for k in ['source_sha','rules_digest','snapshot_digest']};header['dataset_digest']=digest(suite)
 run_id='public-workflow-'+label
 binding={**header,'task_id':'public-workflow-batch','run_id':run_id,'input_sha256':suite['tasks'][0]['input_sha256']}
 rawusage=record['usage'][0];usage={'input_tokens':rawusage['input_tokens'],'output_tokens':rawusage['output_tokens'],'total_tokens':rawusage['input_tokens']+rawusage['output_tokens'],'cost_usd':None}
 files={'input':'input.txt','output':label+'-output.txt','verification':label+'-verification.json','usage':label+'-usage.json'}
 (artifacts/files['output']).write_text(record['answers'][0],encoding='utf-8')
 (artifacts/files['verification']).write_bytes(canonical({'binding':binding,'status':status,'seconds':record['seconds'],'errors':errors,'checks':checks,'criteria':expected,'limitations':'One prompted public decision batch, no implementation or independent review.'}))
 (artifacts/files['usage']).write_bytes(canonical({'binding':binding,'environment':env,'usage':usage,'original_cli_usage':rawusage,'raw_events_sha256':hashlib.sha256((p/(label+'-events.jsonl')).read_bytes()).hexdigest()}))
 descriptors={name:{'path':path,'sha256':hashlib.sha256((artifacts/path).read_bytes()).hexdigest()} for name,path in files.items()}
 results={'schema_version':1,**header,'environment':env,'cases':[{'id':'public-workflow-batch','run_id':run_id,'input_sha256':binding['input_sha256'],'usage':usage,'status':status,'seconds':record['seconds'],'errors':errors,'artifacts':descriptors}]}
 save(label+'-results.json',results);report=import_results(p/label,snapshot,suite,results,artifacts);save(label+'-report.json',report);reports[label]=report
 print(label,checks,usage)
save('suite.json',suite);result=compare(reports['old'],reports['new']);save('comparison.json',result)
print(json.dumps(result))

