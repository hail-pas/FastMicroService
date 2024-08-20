from typing import Union, Literal

from pydantic import Field, BaseModel


class GeoDataType(BaseModel):
    type_: Literal["Point", "Polygon", "LineString", "MultiPolygon", "MultiLineString", "MultiPoint"] = Field(
        alias="type",
    )
    coordinates: Union[
        dict[str, float],  # Point
        list[dict[str, float]],  # MultiPoint
        list[list[dict[str, float]]],  # Polygon
        list[list[list[dict[str, float]]]],  # MultiPolygon
    ] = Field(description="点位信息")
