"""Check or render the project LinkedIn skill and harness entry points."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rendered_files(root):
    source = root / '.agents/skills/linkedin-triage'
    outputs = {root / '.claude/skills/linkedin-triage' / name:
               (source / name).read_text(encoding='utf-8')
               for name in ('SKILL.md', 'references/commands.md')}
    body = ('Read .agents/skills/linkedin-triage/SKILL.md and its command reference.\n'
            'Resolve the repository and explicit observation/capture/note roots. Use preview\n'
            'unless scoped writes are authorized. Preserve separate source and write\n'
            'permissions, verified capture versus analyzed-note states, bounded\n'
            'selected retained checks, excerpt provenance and untrusted-content handling.\n'
            'Read docs/linkedin-source-scope.md before any live-source request.\n'
            'No permitted live acquisition or unsave route is established here.\n'
            'Legacy matches are unverified candidates, never analysis receipts.\n'
            'Do not bypass access walls, infer cloud permissions or edit receipts.\n'
            'Report incomplete/skipped/failed separately from verified analysis.\n')
    metadata = {'name': 'linkedin-triage', 'description': 'Read supplied LinkedIn observations and publish verified local notes.'}
    markdown = '---\n' + ''.join(f'{k}: {json.dumps(v)}\n' for k, v in metadata.items()) + '---\n\n' + body
    for directory in ('.agents/agents', '.claude/agents'):
        outputs[root / directory / 'linkedin-triage.md'] = markdown
    outputs[root / '.claude/commands/linkedin-triage.md'] = body
    outputs[root / '.codex/agents/linkedin-triage.toml'] = ''.join(
        f'{k} = {json.dumps(v)}\n' for k, v in metadata.items()) + "developer_instructions = '''\n" + body + "'''\n"
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    changed = []
    for path, content in rendered_files(ROOT).items():
        if path.exists() and path.read_text(encoding='utf-8') == content:
            continue
        changed.append(path.relative_to(ROOT).as_posix())
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
    print(json.dumps({'changed': changed, 'written': args.write}))
    return 0 if args.write or not changed else 1


if __name__ == '__main__':
    raise SystemExit(main())

