import pytest
from is_wire.rpc import ServiceProvider


def test_service_provider_invalid_channel_type():
    with pytest.raises(TypeError, match="channel"):
        ServiceProvider("not a channel")


def test_service_provider_invalid_channel_none():
    with pytest.raises(TypeError, match="channel"):
        ServiceProvider(None)
