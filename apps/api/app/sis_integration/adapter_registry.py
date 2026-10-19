"""Registry and factory resolving SISAdapter instances by provider type or tenant configuration."""

from __future__ import annotations

from typing import Any, Callable
import httpx

from app.university_sync.client import UniversityContractClient

from .adapter_interface import SISAdapter
from .errors import SISIntegrationError
from .fake_university_adapter import FakeUniversityAdapter
from .generic_rest_adapter import GenericRestAdapter
from .models import UniversityIntegrationConfig


AdapterFactory = Callable[[UniversityIntegrationConfig, dict[str, Any]], SISAdapter]


class AdapterRegistry:
    """Registry maintaining available SISAdapter factories."""

    _factories: dict[str, AdapterFactory] = {}

    @classmethod
    def register(cls, provider_type: str, factory: AdapterFactory) -> None:
        cls._factories[provider_type.lower().strip()] = factory

    @classmethod
    def get_adapter(
        cls,
        config: UniversityIntegrationConfig,
        *,
        http_client: httpx.AsyncClient | None = None,
        contract_client: UniversityContractClient | None = None,
        allow_localhost: bool = False,
        **kwargs: Any,
    ) -> SISAdapter:
        provider = config.provider_type.lower().strip()
        if provider == "fake_university":
            client = contract_client or UniversityContractClient(base_url=config.base_url)
            return FakeUniversityAdapter(
                client,
                http_client=http_client,
                base_url=config.base_url,
            )
        if provider == "generic_rest":
            return GenericRestAdapter(
                config,
                http_client=http_client,
                allow_localhost=allow_localhost,
            )

        factory = cls._factories.get(provider)
        if not factory:
            raise SISIntegrationError(
                "UNSUPPORTED_SIS_PROVIDER",
                f"No SIS adapter registered for provider type '{config.provider_type}'",
                status_code=400,
            )
        return factory(config, {"http_client": http_client, "allow_localhost": allow_localhost, **kwargs})


# Default registration
AdapterRegistry.register(
    "fake_university",
    lambda cfg, kwargs: FakeUniversityAdapter(
        kwargs.get("contract_client") or UniversityContractClient(base_url=cfg.base_url),
        http_client=kwargs.get("http_client"),
        base_url=cfg.base_url,
    ),
)

AdapterRegistry.register(
    "generic_rest",
    lambda cfg, kwargs: GenericRestAdapter(
        cfg,
        http_client=kwargs.get("http_client"),
        allow_localhost=kwargs.get("allow_localhost", False),
    ),
)

