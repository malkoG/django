# [TODO] WKTAdapter
class WKTAdapter:
    """
    An adaptor for Geometries sent to the MySQL and Oracle database backends.
    """

    # [TODO] WKTAdapter > __init__
    def __init__(self, geom):
        self.wkt = geom.wkt
        self.srid = geom.srid

    # [TODO] WKTAdapter > __eq__
    def __eq__(self, other):
        return (
            isinstance(other, WKTAdapter)
            and self.wkt == other.wkt
            and self.srid == other.srid
        )

    # [TODO] WKTAdapter > __hash__
    def __hash__(self):
        return hash((self.wkt, self.srid))

    # [TODO] WKTAdapter > __str__
    def __str__(self):
        return self.wkt

    # [TODO] WKTAdapter > _fix_polygon
    @classmethod
    def _fix_polygon(cls, poly):
        # Hook for Oracle.
        return poly