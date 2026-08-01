from pathlib import Path

import pytest

from aeon.config import Settings
from aeon.core.runtime import AeonRuntime


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        aeon_runtime_dir=tmp_path / "runtime",
        aeon_model_provider="mock",
        aeon_mock_seed=19,
        aeon_max_cycles=3,
        aeon_workspace_capacity=3,
        aeon_observer_signing_key="test-key",
    )


@pytest.fixture
def runtime(settings: Settings) -> AeonRuntime:
    return AeonRuntime(settings=settings)
