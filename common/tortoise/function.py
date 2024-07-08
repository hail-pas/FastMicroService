from pypika import CustomFunction
from tortoise.expressions import Function


class STAsWKBFunc(Function):
    """
    from shapely import wkb
    from shapely.geometry import mapping


    geo_data_binary = f.geo_data_wkb
    geom = wkb.loads(geo_data_binary)
    geojson = mapping(geom)

    """

    database_func = CustomFunction(
        "ST_AsWKB",
        [
            "name",
        ],
    )
