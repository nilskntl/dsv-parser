"""Shared fixtures.

The DSV files under ``tests/fixtures`` are synthetic. Real files carry names,
addresses, birth dates and bank details of actual people, and none of that
belongs in a repository — see the ``/data/`` entry in ``.gitignore`` for where to
drop real files when reproducing a bug locally.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures() -> Path:
    """The directory holding the synthetic DSV fixtures."""
    return FIXTURES


@pytest.fixture
def definition_bytes() -> bytes:
    """A Format 7 Wettkampfdefinitionsliste."""
    return (FIXTURES / "definition.dsv7").read_bytes()


@pytest.fixture
def results_bytes() -> bytes:
    """A Format 8 Wettkampfergebnisliste."""
    return (FIXTURES / "results.dsv8").read_bytes()


@pytest.fixture
def entries_bytes() -> bytes:
    """A Format 7 Vereinsmeldeliste."""
    return (FIXTURES / "entries.dsv7").read_bytes()


@pytest.fixture
def broken_bytes() -> bytes:
    """A file with one problem of every kind the reader must survive."""
    return (FIXTURES / "broken.dsv7").read_bytes()
