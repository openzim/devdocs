# pyright: strict, reportUnusedExpression=false

import pytest

from devdocs2zim import compute, entrypoint
from devdocs2zim.__about__ import __version__


def test_version():
    assert "dev" in __version__


def test_compute():
    assert compute(1, 2) == 3
    with pytest.raises(TypeError):
        compute(1.0, 2)  # pyright: ignore [reportArgumentType]
    assert entrypoint() is None
