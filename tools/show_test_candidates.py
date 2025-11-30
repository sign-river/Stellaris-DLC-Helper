#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Show the test URL candidates for each configured source.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import DLC_SOURCES


def build_candidates_for_source(source):
    # Return a single explicit test URL if configured; otherwise return a single fixed default per source
    candidates = []
    if source.get('test_url'):
        candidates.append(source.get('test_url'))
        return candidates
    base = source.get('url', '').rstrip('/')
    fmt = source.get('format', 'standard')
    name = source.get('name')
    if name == 'r2':
        candidates.append(f"{base}/test/test2.bin")
    elif name == 'domestic_cloud':
        candidates.append(f"{base}/test/test.bin")
    elif fmt in ['github_release', 'gitee_release']:
        # Use a single release-style default with tag 'test' for release-based sources
        if '/releases/download/' in base:
            parts = base.split('/releases/download/')
            prefix = parts[0] + '/releases/download/'
            candidates.append(f"{prefix}test/test.bin")
        else:
            candidates.append(f"{base}/test/test.bin")
    else:
        candidates.append(f"{base}/test/test.bin")
    # dedupe
    res = []
    seen = set()
    for u in candidates:
        if u and u not in seen:
            seen.add(u)
            res.append(u)
    return res


def main():
    print('测试 URL 候选：')
    for s in DLC_SOURCES:
        if s.get('enabled'):
            name = s.get('name')
            print(f"\n源: {name}\n base: {s.get('url')}")
            cands = build_candidates_for_source(s)
            for c in cands:
                print(' - ' + c)

if __name__ == '__main__':
    main()
