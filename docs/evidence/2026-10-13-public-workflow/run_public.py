import json,subprocess,sys,time,os
from pathlib import Path
root=Path(sys.argv[1]);label=sys.argv[2];public=root/'public-experiment';p=public/label
env=os.environ.copy();env.pop('OPENAI_API_KEY',None)
status=subprocess.run(['codex.cmd','login','status'],capture_output=True,env=env,text=True)
if status.returncode or 'Logged in using ChatGPT' not in status.stdout+status.stderr:
 print('NOT_RUN: existing ChatGPT login not confirmed');sys.exit(2)
prompt=(public/(label+'-prompt.txt')).read_bytes()
start=time.perf_counter()
try:
 r=subprocess.run(['codex.cmd','exec','--ignore-user-config','--ephemeral','--sandbox','read-only','--json','--color','never','-'],input=prompt,cwd=p,env=env,capture_output=True,timeout=180)
except subprocess.TimeoutExpired as e:
 (public/(label+'-events.jsonl')).write_bytes(e.stdout or b'')
 print('NOT_RUN: bounded run timed out; no retry');sys.exit(3)
seconds=time.perf_counter()-start
(public/(label+'-events.jsonl')).write_bytes(r.stdout)
# No raw stderr publication; config/account messages remain local.
(public/(label+'-stderr.log')).write_bytes(r.stderr)
events=[]
for line in r.stdout.splitlines():
 try: events.append(json.loads(line))
 except (ValueError,UnicodeDecodeError):pass
usage=[e.get('usage') for e in events if e.get('type')=='turn.completed']
answers=[e['item']['text'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
record={'exit_code':r.returncode,'seconds':round(seconds,3),'auth_method':'existing_chatgpt_login','cli_version':'0.162.0','usage':usage,'answers':answers,'tool_events':[e.get('item',{}).get('type') for e in events if e.get('type')=='item.started']}
(public/(label+'-observed.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True)
sys.exit(r.returncode)

