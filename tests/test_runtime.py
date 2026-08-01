import pytest

from aeon.core.runtime import AeonRuntime


@pytest.mark.asyncio
async def test_mock_cycle_is_deterministic(settings):
    first = AeonRuntime(settings=settings, runtime_dir=settings.aeon_runtime_dir / "first")
    second = AeonRuntime(settings=settings, runtime_dir=settings.aeon_runtime_dir / "second")
    a = await first.process("Evaluate whether memory affects this conclusion")
    b = await second.process("Evaluate whether memory affects this conclusion")
    assert a.response == b.response
    assert [c.salience for c in a.workspace] == [c.salience for c in b.workspace]


@pytest.mark.asyncio
async def test_identity_survives_restart(settings):
    first = AeonRuntime(settings=settings)
    identity = first.self_model.model.continuity_id
    await first.process("Remember continuity")
    second = AeonRuntime(settings=settings)
    assert second.self_model.model.continuity_id == identity
    assert second.storage.list_memories()


@pytest.mark.asyncio
async def test_cycle_logs_required_modules(runtime):
    result = await runtime.process("Test observable recurrent cognition")
    actors = {
        event.actor for event in runtime.storage.list_events() if event.cycle_id == result.cycle_id
    }
    assert {
        "manas",
        "attention",
        "workspace",
        "metacognition",
        "buddhi",
        "ahamkara",
        "sakshin",
    } <= actors
    assert result.iterations >= 1


def test_cloud_mode_requires_backend_credentials(settings):
    settings.aeon_runtime_mode = "cloud"
    settings.supabase_url = None
    settings.supabase_service_role_key = None
    with pytest.raises(ValueError, match="SUPABASE"):
        AeonRuntime(settings=settings)


@pytest.mark.parametrize(
    ("provider", "credential_field", "credential", "expected"),
    [
        ("anthropic", "anthropic_api_key", "test", "anthropic"),
        ("gemini", "google_api_key", "test", "gemini"),
    ],
)
def test_hosted_provider_selection(settings, provider, credential_field, credential, expected):
    settings.aeon_model_provider = provider
    setattr(settings, credential_field, credential)
    runtime = AeonRuntime(settings=settings)
    assert runtime.provider.provider_name == expected


def test_unknown_provider_rejected(settings):
    settings.aeon_model_provider = "imaginary"
    with pytest.raises(ValueError, match="Unknown"):
        AeonRuntime(settings=settings)
