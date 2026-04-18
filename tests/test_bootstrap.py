"""E0 smoke test: package imports and exposes __version__."""

import pytest


@pytest.mark.unit
def test_package_imports() -> None:
    import experiment_core

    assert hasattr(experiment_core, "__version__")
    assert isinstance(experiment_core.__version__, str)
