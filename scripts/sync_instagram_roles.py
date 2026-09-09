"""Render project-local harness roles from the canonical Instagram skill.

No runtime installation. Default checks tracked outputs; --write updates only
the named project files. Review the resulting Git diff before committing.
"""
import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def rendered_files(root):
    source = root / '.agents/skills/instagram-triage'
    outputs = {}
    for relative in ('SKILL.md', 'roles.json', 'references/commands.md',
                     'references/capture-role.md', 'references/analysis-role.md'):
        outputs[root / '.claude/skills/instagram-triage' / relative] = (
            source / relative).read_text(encoding='utf-8')
    roles = json.loads((source / 'roles.json').read_text(encoding='utf-8'))
    for role in roles:
        name = role['name']
        if name not in {'instagram-capture-subagent', 'ig-analyze-subagent'}:
            raise ValueError('unknown source role')
        relative = role['instructions']
        if relative not in {'references/capture-role.md', 'references/analysis-role.md'}:
            raise ValueError('unknown role instructions')
        body = (source / relative).read_text(encoding='utf-8').rstrip() + '\n'
        if "'''" in body:
            raise ValueError('role cannot contain TOML literal delimiter')
        metadata = {key: role[key] for key in ('name', 'description')}
        toml = ''.join(f'{key} = {json.dumps(value)}\n' for key, value in metadata.items())
        outputs[root / '.codex/agents' / (name + '.toml')] = (
            toml + "developer_instructions = '''\n" + body + "'''\n")
        markdown = '---\n' + ''.join(
            f'{key}: {json.dumps(value)}\n' for key, value in metadata.items()) + '---\n\n' + body
        for directory in ('.agents/agents', '.claude/agents'):
            outputs[root / directory / (name + '.md')] = markdown
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    outputs = rendered_files(ROOT)
    changed = []
    for path, content in outputs.items():
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
