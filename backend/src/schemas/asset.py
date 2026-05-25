from pydantic import BaseModel


class AssetBlueprintResponse(BaseModel):
    required_fields: list[str]
    optional_fields: list[str]
    document_support: bool
