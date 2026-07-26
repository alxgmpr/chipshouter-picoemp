import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kicad_parse as kp

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCH = ROOT / 'picoemp-rev2026.kicad_sch'
PCB = ROOT / 'picoemp-rev2026.kicad_pcb'
PRO = ROOT / 'picoemp-rev2026.kicad_pro'


@pytest.fixture(scope='session')
def root():
    return ROOT


@pytest.fixture(scope='session')
def sch():
    return kp.parse_file(SCH)


@pytest.fixture(scope='session')
def syms(sch):
    return kp.symbols(sch)
