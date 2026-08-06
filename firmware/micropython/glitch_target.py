# PicoEMP glitch target -- a Pico that reports on its own corruption.
#
# Runs a deterministic block of work, checks the result, and prints one line
# per block. A line whose ACC differs from EXPECTED is a data fault. If the
# capture stops on its own, the target reset.
#
# Imports nothing from `machine` on purpose: the computation must be
# importable on CPython so tests/test_glitch_target.py can verify EXPECTED.
# A wrong EXPECTED would make every block report a fault and would poison
# the baseline control, so that check matters more than it looks.
#
# Run with:  mpremote connect <port> run glitch_target.py
#
# THIS BOARD WILL BE DELIBERATELY GLITCHED. Use a spare Pico. Flash
# corruption is a plausible outcome.

BLOCK_N = 100000
EXPECTED = BLOCK_N


def compute_block():
    """Count to BLOCK_N the slow way.

    Deliberately the simplest possible loop. A fault that skips, repeats or
    corrupts one iteration shows up directly in the total, with nothing else
    going on to confuse the attribution.
    """
    acc = 0
    for _ in range(BLOCK_N):
        acc += 1
    return acc


def format_line(seq, acc):
    return 'SEQ %d ACC %d' % (seq, acc)


def main():
    print('GLITCH TARGET BLOCK_N %d EXPECTED %d' % (BLOCK_N, EXPECTED))
    seq = 0
    while True:
        print(format_line(seq, compute_block()))
        seq += 1


if __name__ == '__main__':
    main()
