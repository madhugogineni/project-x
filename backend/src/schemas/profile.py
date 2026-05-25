from pydantic import BaseModel


class ProfileTypeCatalog(BaseModel):
    supported_types: list[str]
