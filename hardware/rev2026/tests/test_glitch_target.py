"""Host-side checks on the glitch target and its log analyser.

The load-bearing test is that EXPECTED actually equals what compute_block()
returns. If that constant were wrong, every block would report a fault, the
baseline control would be nonzero, and the whole experiment would be
measuring a typo. glitch_target.py imports nothing from `machine` precisely
so this can run on CPython.

Plan: docs/superpowers/plans/2026-08-05-picoemp-injection-tips.md
Spec: docs/superpowers/specs/2026-08-05-picoemp-injection-tips-design.md
"""

import importlib.util
import sys

import conftest

REPO = conftest.ROOT.parents[1]
TARGET = REPO / 'firmware' / 'micropython' / 'glitch_target.py'


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load():
    return _load_module(TARGET, 'glitch_target')


def test_expected_matches_the_computation():
    """The constant the target compares against is the value it computes."""
    gt = _load()
    assert gt.compute_block() == gt.EXPECTED


def test_block_is_large_enough_to_be_hit():
    """The vulnerable window must be wide enough for an untriggered pulse.

    A block of a few hundred iterations would complete in microseconds and a
    hand-pressed pulse would essentially never land inside it. See spec
    section 4 -- skipping the trigger is only justified by a wide window.
    """
    gt = _load()
    assert gt.BLOCK_N >= 10000, \
        f'BLOCK_N = {gt.BLOCK_N} is too small for untriggered pulsing'


def test_line_format_is_parseable():
    """format_line emits exactly what the analyser expects."""
    gt = _load()
    assert gt.format_line(7, 12345) == 'SEQ 7 ACC 12345'


def test_target_uses_no_gpio():
    """The target must not touch hardware -- it has to run on CPython too."""
    source = TARGET.read_text()
    assert 'import machine' not in source
    assert 'from machine' not in source


ANALYZER = conftest.ROOT / 'tools' / 'analyze_glitch_log.py'


def _load_analyzer():
    return _load_module(ANALYZER, 'analyze_glitch_log')


CLEAN_LOG = """GLITCH TARGET BLOCK_N 100000 EXPECTED 100000
SEQ 0 ACC 100000
SEQ 1 ACC 100000
SEQ 2 ACC 100000
"""

FAULTED_LOG = """GLITCH TARGET BLOCK_N 100000 EXPECTED 100000
SEQ 0 ACC 100000
SEQ 1 ACC 99999
SEQ 2 ACC 100000
SEQ 3 ACC 100002
"""


def test_clean_log_reports_no_faults():
    a = _load_analyzer().analyze(CLEAN_LOG, 100000)
    assert a['blocks'] == 3
    assert a['faults'] == []
    assert a['fault_rate'] == 0.0
    assert a['last_seq'] == 2


def test_faulted_log_reports_both_directions():
    """Both a low and a high ACC are faults -- a glitch can skip or repeat."""
    a = _load_analyzer().analyze(FAULTED_LOG, 100000)
    assert a['blocks'] == 4
    assert a['faults'] == [(1, 99999), (3, 100002)]
    assert a['fault_rate'] == 0.5


def test_truncated_final_line_is_counted_not_crashed():
    """A capture cut off mid-line must not look like a fault.

    The target is reset by design during these runs, so the last line of a
    real log is very often a partial one. Counting that as a corrupted
    result would manufacture faults out of the capture ending.
    """
    a = _load_analyzer().analyze(CLEAN_LOG + 'SEQ 3 AC', 100000)
    assert a['blocks'] == 3
    assert a['faults'] == []
    assert a['malformed'] == 1


def test_empty_log_is_not_a_division_by_zero():
    a = _load_analyzer().analyze('', 100000)
    assert a['blocks'] == 0
    assert a['fault_rate'] == 0.0
    assert a['last_seq'] is None
