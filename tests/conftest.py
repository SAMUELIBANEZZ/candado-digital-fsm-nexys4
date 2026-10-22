import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from candado.params import SIM  # noqa: E402
from candado.scenarios import SCENARIOS  # noqa: E402
from candado.testing import run_core  # noqa: E402


@pytest.fixture(scope="session")
def traces():
    """Simula una sola vez cada escenario sobre candado_core."""
    return {name: run_core(build(SIM)) for name, build in SCENARIOS.items()}
