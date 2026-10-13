import argparse
import json
import shlex
import sys

from .bootstrap import initialize, doctor, upgrade
from .provider import Provider


def main():
    parser = argparse.ArgumentParser(description='Agent-native starter tooling')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'doctor', 'upgrade'):
        command = commands.add_parser(name)
        command.add_argument('target')
        if name == 'init':
            command.add_argument('--dry-run', action='store_true', help='Report without writing target files')
            command.add_argument('--profile', choices=['lean', 'full'], default=None,
                                 help='Default: lean; full installs optional components')
            command.add_argument('--platform', choices=['auto', 'github', 'gitea', 'none'],
                                 default=None, help='Default: infer when unambiguous')
        elif name == 'doctor':
            command.add_argument('--verify', action='append', default=[],
                                 help='Explicit trusted command; no shell expansion')
            command.add_argument('--provider', choices=['github', 'gitea'])
            command.add_argument('--api-url')
            command.add_argument('--repository')
        elif name == 'upgrade':
            command.add_argument('--branch', default='agent-starter/upgrade')
    args = parser.parse_args()
    try:
        if args.command == 'init':
            result = initialize(args.target, dry_run=args.dry_run,
                                profile=args.profile, platform=args.platform)
        elif args.command == 'upgrade':
            result = upgrade(args.target, branch=args.branch)
        else:
            if args.provider and not (args.api_url and args.repository):
                parser.error('--provider requires --api-url and --repository')
            provider = Provider(args.provider, args.api_url, args.repository) if args.provider else None
            result = doctor(args.target, verify=[shlex.split(c) for c in args.verify], provider=provider)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get('ok', True) else 1
    except (ValueError, OSError) as error:
        print(json.dumps({'error': type(error).__name__}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
