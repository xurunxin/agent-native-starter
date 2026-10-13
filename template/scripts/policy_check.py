#!/usr/bin/env python3
"""最小静态策略检查。仅校验仓库文件和风险配置，不代替服务端保护。"""
from pathlib import Path
import sys
r = Path(__file__).resolve().parents[1]
required = ['AGENTS.md','agent-project.yaml','docs/engineering.md','LESSONS.md',
            'docs/subsystems/README.md','.github/PULL_REQUEST_TEMPLATE.md']
missing = [x for x in required if not (r/x).is_file()]
config = (r/'agent-project.yaml').read_text(encoding='utf-8') if not missing else ''
errors = [f'缺少文件: {x}' for x in missing]
for fragment in ('auto_merge: false','auto_release: false','require_isolated_worktree: true','verify_head_sha: true'):
    if fragment not in config: errors.append(f'缺失或不安全配置: {fragment}')
if 'CHANGE_ME' in config: print('WARNING: 请填写项目配置里的 CHANGE_ME')
if errors:
    print('\n'.join(errors), file=sys.stderr); sys.exit(1)
print('PASS: 文件与基础保护配置检查通过；仍需配置平台分支保护、CI 和审批。')
