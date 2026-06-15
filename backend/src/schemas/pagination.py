from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100

ItemT = TypeVar("ItemT")


class PaginatedResponse(BaseModel, Generic[ItemT]):
    items: list[ItemT] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    has_more: bool


def build_paginated_response(
    *,
    items: list[ItemT],
    total: int,
    limit: int,
    offset: int,
) -> PaginatedResponse[ItemT]:
    return PaginatedResponse[ItemT](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )
