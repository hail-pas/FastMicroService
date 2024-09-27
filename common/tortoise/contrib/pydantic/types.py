from typing import Literal

from pydantic import Field, BaseModel


class GeoDataType(BaseModel):
    type_: Literal["Point", "Polygon", "LineString", "MultiPolygon", "MultiLineString", "MultiPoint"] = Field(
        alias="type",
    )
    coordinates: dict[str, float] | list[dict[str, float]] | list[list[dict[str, float]]] | list[
        list[list[dict[str, float]]]
    ] = Field(
        description="点位信息",
    )  # ruff: noqa: E501
