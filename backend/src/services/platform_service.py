from core.config import get_settings
from schemas.health import (
    HealthResponse,
    ModuleStatus,
    PlatformReadinessResponse,
)


def get_health_response() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.project_name,
        environment=settings.environment
    )


def get_platform_readiness() -> PlatformReadinessResponse:
    return PlatformReadinessResponse(
        profile_types=["PRIMARY", "ADVISOR", "NOMINEE"],
        modules=[
            ModuleStatus(
                name="Asset Registry",
                status="scaffolded",
                description="Container-first asset modeling with nominee-aware fields."
            ),
            ModuleStatus(
                name="Document Vault",
                status="scaffolded",
                description="Encrypted file workflows are reserved for backend-managed uploads."
            ),
            ModuleStatus(
                name="Release Workflow",
                status="planned",
                description=(
                    "Inactivity checks and nominee release rules will layer onto "
                    "profile access."
                )
            ),
        ]
    )
