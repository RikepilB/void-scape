"""Resolve one retained RSS resource without fetching or granting read consent."""
from __future__ import annotations

import argparse
import json
import re

from rss_capture_helper import article, verify


def select(root, key, resource='article', enclosure=None):
    """Bind a resource choice to verified, explicitly unredacted feed evidence."""
    if not isinstance(key, str) or not re.fullmatch(r'rss:[a-f0-9]{64}', key):
        raise ValueError('invalid RSS capture key')
    record = verify(root, key[4:])
    entry = record['entry']
    if resource == 'article':
        if enclosure is not None:
            raise ValueError('article selection cannot include an enclosure index')
        url, redacted = entry.get('link'), entry.get('link_redacted')
        reader, tier = 'article', None
    elif resource == 'enclosure':
        items = entry.get('enclosures')
        if (not isinstance(items, list) or type(enclosure) is not int or
                not 1 <= enclosure <= len(items)):
            raise ValueError('select an existing one-based enclosure index')
        item = items[enclosure - 1]
        if not isinstance(item, dict):
            raise ValueError('invalid enclosure metadata')
        url, redacted = item.get('url'), item.get('url_redacted')
        mime = item.get('type')
        if not isinstance(mime, str):
            raise ValueError('enclosure media type required')
        mime = mime.split(';', 1)[0].strip().lower()
        if not re.fullmatch(r'(audio|video)/[a-z0-9!#$&^_.+-]+', mime):
            raise ValueError('unsupported enclosure media type; do not guess a reader')
        reader, tier = 'video', 'audio' if mime.startswith('audio/') else 'both'
    else:
        raise ValueError('unsupported RSS resource kind')
    if redacted is not False:
        raise ValueError('original resource URL unavailable or provenance unknown')
    safe, changed = article._evidence_url(url)
    if changed:
        raise ValueError('resource URL does not match retained unredacted provenance')
    return {'key': key, 'resource': resource, 'enclosure': enclosure,
            'url': safe, 'reader': reader, 'tier': tier,
            'changes': False, 'source_action_authorized': False,
            'content_trust': 'untrusted', 'read_authorized': False,
            'network_validation': 'required_at_read'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root')
    parser.add_argument('key')
    parser.add_argument('--resource', choices=['article', 'enclosure'], default='article')
    parser.add_argument('--enclosure', type=int)
    try:
        data = select(**vars(parser.parse_args(argv)))
        print(json.dumps({'ok': True, 'data': data, 'error': None}))
        return 0
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({'ok': False, 'data': None, 'error': {
            'code': 'rss_resource_unavailable',
            'message': 'Resource selection failed; preserve capture and review its provenance'}}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
