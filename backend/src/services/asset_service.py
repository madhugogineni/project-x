from schemas.asset import AssetBlueprintResponse


def get_asset_blueprint() -> AssetBlueprintResponse:
    return AssetBlueprintResponse(
        required_fields=["institution_name", "container_type", "asset_name", "account_reference"],
        optional_fields=[
            "approximate_value",
            "currency_code",
            "nominee_recorded",
            "reference_note",
        ],
        document_support=True,
    )
