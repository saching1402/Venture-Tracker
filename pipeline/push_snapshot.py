#!/usr/bin/env python3
"""
Weekly refresh helper for the Venture GP Atlas API.

  python3 pipeline/push_snapshot.py export  out/tracker_prev.json
  python3 pipeline/push_snapshot.py import  site/tracker.json

Reads ATLAS_API (e.g. https://<backend>.up.railway.app/api/v1) and ATLAS_IMPORT_TOKEN from the environment.
Uses only the standard library.
"""
import json
import os
import sys
import urllib.error
import urllib.request


def call(method: str, path: str, body: bytes | None = None) -> dict:
    base = os.environ['ATLAS_API'].rstrip('/')
    req = urllib.request.Request(f'{base}{path}', data=body, method=method, headers={
        'X-Import-Token': os.environ['ATLAS_IMPORT_TOKEN'],
        'Content-Type': 'application/json',
        'User-Agent': 'venture-gp-atlas-refresh/1.0',
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f'{method} {path} failed: HTTP {e.code} {e.read()[:500].decode(errors="replace")}')


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in ('export', 'import'):
        sys.exit(__doc__)
    action, path = sys.argv[1], sys.argv[2]
    if action == 'export':
        data = call('GET', '/export/')
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)
        print(f'Exported {len(data["companies"])} companies, {len(data["firms"])} managers -> {path}')
    else:
        with open(path, 'rb') as fh:
            print(json.dumps(call('POST', '/import/?source=weekly-refresh', fh.read()), indent=1))


if __name__ == '__main__':
    main()
