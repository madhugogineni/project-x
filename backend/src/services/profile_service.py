from db.models.profile import ProfileType
from schemas.profile import ProfileTypeCatalog


def get_supported_profile_types() -> ProfileTypeCatalog:
    return ProfileTypeCatalog(supported_types=[profile_type.value for profile_type in ProfileType])
