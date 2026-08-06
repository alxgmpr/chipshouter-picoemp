#!/usr/bin/env python3
"""Turn a captured glitch-target log into a fault count.

Usage:  uv run tools/analyze_glitch_log.py <logfile> [expected]

A fault is any block whose ACC differs from EXPECTED, in either direction --
a glitch can skip an iteration or repeat one. A truncated final line is
counted as malformed rather than as a fault: the target gets reset on purpose
during these runs, so real logs routinely end mid-line, and treating that as
a corrupted result would manufacture faults out of the capture ending.

Plan: docs/superpowers/plans/2026-08-05-picoemp-injection-tips.md
"""

import re
import sys

LINE = re.compile(r'^SEQ (\d+) ACC (\d+)$')
HEADER = re.compile(r'^GLITCH TARGET BLOCK_N (\d+) EXPECTED (\d+)$')


def analyze(text, expected):
    blocks = 0
    faults = []
    malformed = 0
    last_seq = None
    for line in text.splitlines():
        line = line.strip()
        if not line or HEADER.match(line):
            continue
        m = LINE.match(line)
        if not m:
            malformed += 1
            continue
        seq, acc = int(m.group(1)), int(m.group(2))
        blocks += 1
        last_seq = seq
        if acc != expected:
            faults.append((seq, acc))
    return {
        'blocks': blocks,
        'faults': faults,
        'fault_rate': (len(faults) / blocks) if blocks else 0.0,
        'last_seq': last_seq,
        'malformed': malformed,
    }


def main(argv):
    if not 2 <= len(argv) <= 3:
        print(__doc__.strip())
        return 2
    text = open(argv[1]).read()
    if len(argv) == 3:
        expected = int(argv[2])
    else:
        m = HEADER.search(text)
        if not m:
            print('No header line in log; pass expected explicitly.')
            return 2
        expected = int(m.group(2))
    a = analyze(text, expected)
    print('blocks     %d' % a['blocks'])
    print('faults     %d' % len(a['faults']))
    print('fault rate %.4f' % a['fault_rate'])
    print('last seq   %s' % a['last_seq'])
    print('malformed  %d' % a['malformed'])
    for seq, acc in a['faults']:
        print('  SEQ %d ACC %d (delta %+d)' % (seq, acc, acc - expected))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
