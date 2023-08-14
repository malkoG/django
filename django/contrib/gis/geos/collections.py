"""
 This module houses the Geometry Collection objects:
 GeometryCollection, MultiPoint, MultiLineString, and MultiPolygon
"""
from django.contrib.gis.geos import prototypes as capi
from django.contrib.gis.geos.geometry import GEOSGeometry, LinearGeometryMixin
from django.contrib.gis.geos.libgeos import GEOM_PTR
from django.contrib.gis.geos.linestring import LinearRing, LineString
from django.contrib.gis.geos.point import Point
from django.contrib.gis.geos.polygon import Polygon


# [TODO] GeometryCollection
class GeometryCollection(GEOSGeometry):
    _typeid = 7

    # [TODO] GeometryCollection > __init__
    def __init__(self, *args, **kwargs):
        "Initialize a Geometry Collection from a sequence of Geometry objects."
        # Checking the arguments
        if len(args) == 1:
            # If only one geometry provided or a list of geometries is provided
            #  in the first argument.
            if isinstance(args[0], (tuple, list)):
                init_geoms = args[0]
            else:
                init_geoms = args
        else:
            init_geoms = args

        # Ensuring that only the permitted geometries are allowed in this collection
        # this is moved to list mixin super class
        self._check_allowed(init_geoms)

        # Creating the geometry pointer array.
        collection = self._create_collection(len(init_geoms), init_geoms)
        super().__init__(collection, **kwargs)

    # [TODO] GeometryCollection > __iter__
    def __iter__(self):
        "Iterate over each Geometry in the Collection."
        for i in range(len(self)):
            yield self[i]

    # [TODO] GeometryCollection > __len__
    def __len__(self):
        "Return the number of geometries in this Collection."
        return self.num_geom

    # ### Methods for compatibility with ListMixin ###
    # [TODO] GeometryCollection > _create_collection
    def _create_collection(self, length, items):
        # Creating the geometry pointer array.
        geoms = (GEOM_PTR * length)(
            *[
                # this is a little sloppy, but makes life easier
                # allow GEOSGeometry types (python wrappers) or pointer types
                capi.geom_clone(getattr(g, "ptr", g))
                for g in items
            ]
        )
        return capi.create_collection(self._typeid, geoms, length)

    # [TODO] GeometryCollection > _get_single_internal
    def _get_single_internal(self, index):
        return capi.get_geomn(self.ptr, index)

    # [TODO] GeometryCollection > _get_single_external
    def _get_single_external(self, index):
        "Return the Geometry from this Collection at the given index (0-based)."
        # Checking the index and returning the corresponding GEOS geometry.
        return GEOSGeometry(
            capi.geom_clone(self._get_single_internal(index)), srid=self.srid
        )

    # [TODO] GeometryCollection > _set_list
    def _set_list(self, length, items):
        "Create a new collection, and destroy the contents of the previous pointer."
        prev_ptr = self.ptr
        srid = self.srid
        self.ptr = self._create_collection(length, items)
        if srid:
            self.srid = srid
        capi.destroy_geom(prev_ptr)

    _set_single = GEOSGeometry._set_single_rebuild
    _assign_extended_slice = GEOSGeometry._assign_extended_slice_rebuild

    # [TODO] GeometryCollection > kml
    @property
    def kml(self):
        "Return the KML for this Geometry Collection."
        return "<MultiGeometry>%s</MultiGeometry>" % "".join(g.kml for g in self)

    # [TODO] GeometryCollection > tuple
    @property
    def tuple(self):
        "Return a tuple of all the coordinates in this Geometry Collection"
        return tuple(g.tuple for g in self)

    coords = tuple


# MultiPoint, MultiLineString, and MultiPolygon class definitions.
# [TODO] MultiPoint
class MultiPoint(GeometryCollection):
    _allowed = Point
    _typeid = 4


# [TODO] MultiLineString
class MultiLineString(LinearGeometryMixin, GeometryCollection):
    _allowed = (LineString, LinearRing)
    _typeid = 5


# [TODO] MultiPolygon
class MultiPolygon(GeometryCollection):
    _allowed = Polygon
    _typeid = 6


# Setting the allowed types here since GeometryCollection is defined before
# its subclasses.
GeometryCollection._allowed = (
    Point,
    LineString,
    LinearRing,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon,
)