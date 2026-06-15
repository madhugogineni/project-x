from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    service: str
    environment: str


class ModuleStatus(BaseModel):
    name: str
    status: str
    description: str


class PlatformReadinessResponse(BaseModel):
    profile_types: list[str]
    modules: list[ModuleStatus]


class DbPingResponse(BaseModel):
    status: str = Field(examples=["ok", "error"])
    database_url_host: str
    detail: str | None = None
