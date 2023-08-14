"""
 The OGRGeometry is a wrapper for using the OGR Geometry class
 (see https://gdal.org/api/ogrgeometry_cpp.html#_CPPv411OGRGeometry).
 OGRGeometry may be instantiated when reading geometries from OGR Data Sources
 (e.g. SHP files), or when given OGC WKT (a string).

 While the 'full' API is not present yet, the API is "pythonic" unlike
 the traditional and "next-generation" OGR Python bindings.  One major
 advantage OGR Geometries have over their GEOS counterparts is support
 for spatial reference systems and their transformation.

 Example:
  >>> from django.contrib.gis.gdal import OGRGeometry, OGRGeomType, SpatialReference
  >>> wkt1, wkt2 = 'POINT(-90 30)', 'POLYGON((0 0, 5 0, 5 5, 0 5)'
  >>> pnt = OGRGeometry(wkt1)
  >>> print(pnt)
  POINT (-90 30)
  >>> mpnt = OGRGeometry(OGRGeomType('MultiPoint'), SpatialReference('WGS84'))
  >>> mpnt.add(wkt1)
  >>> mpnt.add(wkt1)
  >>> print(mpnt)
  MULTIPOINT (-90 30,-90 30)
  >>> print(mpnt.srs.name)
  WGS 84
  >>> print(mpnt.srs.proj)
  +proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs
  >>> mpnt.transform(SpatialReference('NAD27'))
  >>> print(mpnt.proj)
  +proj=longlat +ellps=clrk66 +datum=NAD27 +no_defs
  >>> print(mpnt)
  MULTIPOINT (-89.99993037860248 29.99979788655764,-89.99993037860248 29.99979788655764)

  The OGRGeomType class is to make it easy to specify an OGR geometry type:
  >>> from django.contrib.gis.gdal import OGRGeomType
  >>> gt1 = OGRGeomType(3) # Using an integer for the type
  >>> gt2 = OGRGeomType('Polygon') # Using a string
  >>> gt3 = OGRGeomType('POLYGON') # It's case-insensitive
  >>> print(gt1 == 3, gt1 == 'Polygon') # Equivalence works w/non-OGRGeomType objects
  True True
"""
import sys
from binascii import b2a_hex
from ctypes import byref, c_char_p, c_double, c_ubyte, c_void_p, string_at

from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.envelope import Envelope, OGREnvelope
from django.contrib.gis.gdal.error import GDALException, SRSException
from django.contrib.gis.gdal.geomtype import OGRGeomType
from django.contrib.gis.gdal.prototypes import geom as capi
from django.contrib.gis.gdal.prototypes import srs as srs_api
from django.contrib.gis.gdal.srs import CoordTransform, SpatialReference
from django.contrib.gis.geometry import hex_regex, json_regex, wkt_regex
from django.utils.encoding import force_bytes


# For more information, see the OGR C API source code:
#  https://gdal.org/api/vector_c_api.html
#
# The OGR_G_* routines are relevant here.
# [TODO] OGRGeometry
class OGRGeometry(GDALBase):
    """Encapsulate an OGR geometry."""

    destructor = capi.destroy_geom

    # [TODO] OGRGeometry > __init__
    def __init__(self, geom_input, srs=None):
        """Initialize Geometry on either WKT or an OGR pointer as input."""
        str_instance = isinstance(geom_input, str)

        # If HEX, unpack input to a binary buffer.
        if str_instance and hex_regex.match(geom_input):
            geom_input = memoryview(bytes.fromhex(geom_input))
            str_instance = False

        # Constructing the geometry,
        if str_instance:
            wkt_m = wkt_regex.match(geom_input)
            json_m = json_regex.match(geom_input)
            if wkt_m:
                if wkt_m["srid"]:
                    # If there's EWKT, set the SRS w/value of the SRID.
                    srs = int(wkt_m["srid"])
                if wkt_m["type"].upper() == "LINEARRING":
                    # OGR_G_CreateFromWkt doesn't work with LINEARRING WKT.
                    #  See https://trac.osgeo.org/gdal/ticket/1992.
                    g = capi.create_geom(OGRGeomType(wkt_m["type"]).num)
                    capi.import_wkt(g, byref(c_char_p(wkt_m["wkt"].encode())))
                else:
                    g = capi.from_wkt(
                        byref(c_char_p(wkt_m["wkt"].encode())), None, byref(c_void_p())
                    )
            elif json_m:
                g = self._from_json(geom_input.encode())
            else:
                # Seeing if the input is a valid short-hand string
                # (e.g., 'Point', 'POLYGON').
                OGRGeomType(geom_input)
                g = capi.create_geom(OGRGeomType(geom_input).num)
        elif isinstance(geom_input, memoryview):
            # WKB was passed in
            g = self._from_wkb(geom_input)
        elif isinstance(geom_input, OGRGeomType):
            # OGRGeomType was passed in, an empty geometry will be created.
            g = capi.create_geom(geom_input.num)
        elif isinstance(geom_input, self.ptr_type):
            # OGR pointer (c_void_p) was the input.
            g = geom_input
        else:
            raise GDALException(
                "Invalid input type for OGR Geometry construction: %s"
                % type(geom_input)
            )

        # Now checking the Geometry pointer before finishing initialization
        # by setting the pointer for the object.
        if not g:
            raise GDALException(
                "Cannot create OGR Geometry from input: %s" % geom_input
            )
        self.ptr = g

        # Assigning the SpatialReference object to the geometry, if valid.
        if srs:
            self.srs = srs

        # Setting the class depending upon the OGR Geometry Type
        self.__class__ = GEO_CLASSES[self.geom_type.num]

    # Pickle routines
    # [TODO] OGRGeometry > __getstate__
    def __getstate__(self):
        srs = self.srs
        if srs:
            srs = srs.wkt
        else:
            srs = None
        return bytes(self.wkb), srs

    # [TODO] OGRGeometry > __setstate__
    def __setstate__(self, state):
        wkb, srs = state
        ptr = capi.from_wkb(wkb, None, byref(c_void_p()), len(wkb))
        if not ptr:
            raise GDALException("Invalid OGRGeometry loaded from pickled state.")
        self.ptr = ptr
        self.srs = srs

    # [TODO] OGRGeometry > _from_wkb
    @classmethod
    def _from_wkb(cls, geom_input):
        return capi.from_wkb(
            bytes(geom_input), None, byref(c_void_p()), len(geom_input)
        )

    # [TODO] OGRGeometry > _from_json
    @staticmethod
    def _from_json(geom_input):
        return capi.from_json(geom_input)

    # [TODO] OGRGeometry > from_bbox
    @classmethod
    def from_bbox(cls, bbox):
        "Construct a Polygon from a bounding box (4-tuple)."
        x0, y0, x1, y1 = bbox
        return OGRGeometry(
            "POLYGON((%s %s, %s %s, %s %s, %s %s, %s %s))"
            % (x0, y0, x0, y1, x1, y1, x1, y0, x0, y0)
        )

    # [TODO] OGRGeometry > from_json
    @staticmethod
    def from_json(geom_input):
        return OGRGeometry(OGRGeometry._from_json(force_bytes(geom_input)))

    # [TODO] OGRGeometry > from_gml
    @classmethod
    def from_gml(cls, gml_string):
        return cls(capi.from_gml(force_bytes(gml_string)))

    # ### Geometry set-like operations ###
    # g = g1 | g2
    # [TODO] OGRGeometry > __or__
    def __or__(self, other):
        "Return the union of the two geometries."
        return self.union(other)

    # g = g1 & g2
    # [TODO] OGRGeometry > __and__
    def __and__(self, other):
        "Return the intersection of this Geometry and the other."
        return self.intersection(other)

    # g = g1 - g2
    # [TODO] OGRGeometry > __sub__
    def __sub__(self, other):
        "Return the difference this Geometry and the other."
        return self.difference(other)

    # g = g1 ^ g2
    # [TODO] OGRGeometry > __xor__
    def __xor__(self, other):
        "Return the symmetric difference of this Geometry and the other."
        return self.sym_difference(other)

    # [TODO] OGRGeometry > __eq__
    def __eq__(self, other):
        "Is this Geometry equal to the other?"
        return isinstance(other, OGRGeometry) and self.equals(other)

    # [TODO] OGRGeometry > __str__
    def __str__(self):
        "WKT is used for the string representation."
        return self.wkt

    # #### Geometry Properties ####
    # [TODO] OGRGeometry > dimension
    @property
    def dimension(self):
        "Return 0 for points, 1 for lines, and 2 for surfaces."
        return capi.get_dims(self.ptr)

    # [TODO] OGRGeometry > _get_coord_dim
    def _get_coord_dim(self):
        "Return the coordinate dimension of the Geometry."
        return capi.get_coord_dim(self.ptr)

    # [TODO] OGRGeometry > _set_coord_dim
    def _set_coord_dim(self, dim):
        "Set the coordinate dimension of this Geometry."
        if dim not in (2, 3):
            raise ValueError("Geometry dimension must be either 2 or 3")
        capi.set_coord_dim(self.ptr, dim)

    coord_dim = property(_get_coord_dim, _set_coord_dim)

    # [TODO] OGRGeometry > geom_count
    @property
    def geom_count(self):
        "Return the number of elements in this Geometry."
        return capi.get_geom_count(self.ptr)

    # [TODO] OGRGeometry > point_count
    @property
    def point_count(self):
        "Return the number of Points in this Geometry."
        return capi.get_point_count(self.ptr)

    # [TODO] OGRGeometry > num_points
    @property
    def num_points(self):
        "Alias for `point_count` (same name method in GEOS API.)"
        return self.point_count

    # [TODO] OGRGeometry > num_coords
    @property
    def num_coords(self):
        "Alias for `point_count`."
        return self.point_count

    # [TODO] OGRGeometry > geom_type
    @property
    def geom_type(self):
        "Return the Type for this Geometry."
        return OGRGeomType(capi.get_geom_type(self.ptr))

    # [TODO] OGRGeometry > geom_name
    @property
    def geom_name(self):
        "Return the Name of this Geometry."
        return capi.get_geom_name(self.ptr)

    # [TODO] OGRGeometry > area
    @property
    def area(self):
        "Return the area for a LinearRing, Polygon, or MultiPolygon; 0 otherwise."
        return capi.get_area(self.ptr)

    # [TODO] OGRGeometry > envelope
    @property
    def envelope(self):
        "Return the envelope for this Geometry."
        # TODO: Fix Envelope() for Point geometries.
        return Envelope(capi.get_envelope(self.ptr, byref(OGREnvelope())))

    # [TODO] OGRGeometry > empty
    @property
    def empty(self):
        return capi.is_empty(self.ptr)

    # [TODO] OGRGeometry > extent
    @property
    def extent(self):
        "Return the envelope as a 4-tuple, instead of as an Envelope object."
        return self.envelope.tuple

    # #### SpatialReference-related Properties ####

    # The SRS property
    # [TODO] OGRGeometry > _get_srs
    def _get_srs(self):
        "Return the Spatial Reference for this Geometry."
        try:
            srs_ptr = capi.get_geom_srs(self.ptr)
            return SpatialReference(srs_api.clone_srs(srs_ptr))
        except SRSException:
            return None

    # [TODO] OGRGeometry > _set_srs
    def _set_srs(self, srs):
        "Set the SpatialReference for this geometry."
        # Do not have to clone the `SpatialReference` object pointer because
        # when it is assigned to this `OGRGeometry` it's internal OGR
        # reference count is incremented, and will likewise be released
        # (decremented) when this geometry's destructor is called.
        if isinstance(srs, SpatialReference):
            srs_ptr = srs.ptr
        elif isinstance(srs, (int, str)):
            sr = SpatialReference(srs)
            srs_ptr = sr.ptr
        elif srs is None:
            srs_ptr = None
        else:
            raise TypeError(
                "Cannot assign spatial reference with object of type: %s" % type(srs)
            )
        capi.assign_srs(self.ptr, srs_ptr)

    srs = property(_get_srs, _set_srs)

    # The SRID property
    # [TODO] OGRGeometry > _get_srid
    def _get_srid(self):
        srs = self.srs
        if srs:
            return srs.srid
        return None

    # [TODO] OGRGeometry > _set_srid
    def _set_srid(self, srid):
        if isinstance(srid, int) or srid is None:
            self.srs = srid
        else:
            raise TypeError("SRID must be set with an integer.")

    srid = property(_get_srid, _set_srid)

    # #### Output Methods ####
    # [TODO] OGRGeometry > _geos_ptr
    def _geos_ptr(self):
        from django.contrib.gis.geos import GEOSGeometry

        return GEOSGeometry._from_wkb(self.wkb)

    # [TODO] OGRGeometry > geos
    @property
    def geos(self):
        "Return a GEOSGeometry object from this OGRGeometry."
        from django.contrib.gis.geos import GEOSGeometry

        return GEOSGeometry(self._geos_ptr(), self.srid)

    # [TODO] OGRGeometry > gml
    @property
    def gml(self):
        "Return the GML representation of the Geometry."
        return capi.to_gml(self.ptr)

    # [TODO] OGRGeometry > hex
    @property
    def hex(self):
        "Return the hexadecimal representation of the WKB (a string)."
        return b2a_hex(self.wkb).upper()

    # [TODO] OGRGeometry > json
    @property
    def json(self):
        """
        Return the GeoJSON representation of this Geometry.
        """
        return capi.to_json(self.ptr)

    geojson = json

    # [TODO] OGRGeometry > kml
    @property
    def kml(self):
        "Return the KML representation of the Geometry."
        return capi.to_kml(self.ptr, None)

    # [TODO] OGRGeometry > wkb_size
    @property
    def wkb_size(self):
        "Return the size of the WKB buffer."
        return capi.get_wkbsize(self.ptr)

    # [TODO] OGRGeometry > wkb
    @property
    def wkb(self):
        "Return the WKB representation of the Geometry."
        if sys.byteorder == "little":
            byteorder = 1  # wkbNDR (from ogr_core.h)
        else:
            byteorder = 0  # wkbXDR
        sz = self.wkb_size
        # Creating the unsigned character buffer, and passing it in by reference.
        buf = (c_ubyte * sz)()
        capi.to_wkb(self.ptr, byteorder, byref(buf))
        # Returning a buffer of the string at the pointer.
        return memoryview(string_at(buf, sz))

    # [TODO] OGRGeometry > wkt
    @property
    def wkt(self):
        "Return the WKT representation of the Geometry."
        return capi.to_wkt(self.ptr, byref(c_char_p()))

    # [TODO] OGRGeometry > ewkt
    @property
    def ewkt(self):
        "Return the EWKT representation of the Geometry."
        srs = self.srs
        if srs and srs.srid:
            return "SRID=%s;%s" % (srs.srid, self.wkt)
        else:
            return self.wkt

    # #### Geometry Methods ####
    # [TODO] OGRGeometry > clone
    def clone(self):
        "Clone this OGR Geometry."
        return OGRGeometry(capi.clone_geom(self.ptr), self.srs)

    # [TODO] OGRGeometry > close_rings
    def close_rings(self):
        """
        If there are any rings within this geometry that have not been
        closed, this routine will do so by adding the starting point at the
        end.
        """
        # Closing the open rings.
        capi.geom_close_rings(self.ptr)

    # [TODO] OGRGeometry > transform
    def transform(self, coord_trans, clone=False):
        """
        Transform this geometry to a different spatial reference system.
        May take a CoordTransform object, a SpatialReference object, string
        WKT or PROJ, and/or an integer SRID.  By default, return nothing
        and transform the geometry in-place. However, if the `clone` keyword is
        set, return a transformed clone of this geometry.
        """
        if clone:
            klone = self.clone()
            klone.transform(coord_trans)
            return klone

        # Depending on the input type, use the appropriate OGR routine
        # to perform the transformation.
        if isinstance(coord_trans, CoordTransform):
            capi.geom_transform(self.ptr, coord_trans.ptr)
        elif isinstance(coord_trans, SpatialReference):
            capi.geom_transform_to(self.ptr, coord_trans.ptr)
        elif isinstance(coord_trans, (int, str)):
            sr = SpatialReference(coord_trans)
            capi.geom_transform_to(self.ptr, sr.ptr)
        else:
            raise TypeError(
                "Transform only accepts CoordTransform, "
                "SpatialReference, string, and integer objects."
            )

    # #### Topology Methods ####
    # [TODO] OGRGeometry > _topology
    def _topology(self, func, other):
        """A generalized function for topology operations, takes a GDAL function and
        the other geometry to perform the operation on."""
        if not isinstance(other, OGRGeometry):
            raise TypeError(
                "Must use another OGRGeometry object for topology operations!"
            )

        # Returning the output of the given function with the other geometry's
        # pointer.
        return func(self.ptr, other.ptr)

    # [TODO] OGRGeometry > intersects
    def intersects(self, other):
        "Return True if this geometry intersects with the other."
        return self._topology(capi.ogr_intersects, other)

    # [TODO] OGRGeometry > equals
    def equals(self, other):
        "Return True if this geometry is equivalent to the other."
        return self._topology(capi.ogr_equals, other)

    # [TODO] OGRGeometry > disjoint
    def disjoint(self, other):
        "Return True if this geometry and the other are spatially disjoint."
        return self._topology(capi.ogr_disjoint, other)

    # [TODO] OGRGeometry > touches
    def touches(self, other):
        "Return True if this geometry touches the other."
        return self._topology(capi.ogr_touches, other)

    # [TODO] OGRGeometry > crosses
    def crosses(self, other):
        "Return True if this geometry crosses the other."
        return self._topology(capi.ogr_crosses, other)

    # [TODO] OGRGeometry > within
    def within(self, other):
        "Return True if this geometry is within the other."
        return self._topology(capi.ogr_within, other)

    # [TODO] OGRGeometry > contains
    def contains(self, other):
        "Return True if this geometry contains the other."
        return self._topology(capi.ogr_contains, other)

    # [TODO] OGRGeometry > overlaps
    def overlaps(self, other):
        "Return True if this geometry overlaps the other."
        return self._topology(capi.ogr_overlaps, other)

    # #### Geometry-generation Methods ####
    # [TODO] OGRGeometry > _geomgen
    def _geomgen(self, gen_func, other=None):
        "A helper routine for the OGR routines that generate geometries."
        if isinstance(other, OGRGeometry):
            return OGRGeometry(gen_func(self.ptr, other.ptr), self.srs)
        else:
            return OGRGeometry(gen_func(self.ptr), self.srs)

    # [TODO] OGRGeometry > boundary
    @property
    def boundary(self):
        "Return the boundary of this geometry."
        return self._geomgen(capi.get_boundary)

    # [TODO] OGRGeometry > convex_hull
    @property
    def convex_hull(self):
        """
        Return the smallest convex Polygon that contains all the points in
        this Geometry.
        """
        return self._geomgen(capi.geom_convex_hull)

    # [TODO] OGRGeometry > difference
    def difference(self, other):
        """
        Return a new geometry consisting of the region which is the difference
        of this geometry and the other.
        """
        return self._geomgen(capi.geom_diff, other)

    # [TODO] OGRGeometry > intersection
    def intersection(self, other):
        """
        Return a new geometry consisting of the region of intersection of this
        geometry and the other.
        """
        return self._geomgen(capi.geom_intersection, other)

    # [TODO] OGRGeometry > sym_difference
    def sym_difference(self, other):
        """
        Return a new geometry which is the symmetric difference of this
        geometry and the other.
        """
        return self._geomgen(capi.geom_sym_diff, other)

    # [TODO] OGRGeometry > union
    def union(self, other):
        """
        Return a new geometry consisting of the region which is the union of
        this geometry and the other.
        """
        return self._geomgen(capi.geom_union, other)


# The subclasses for OGR Geometry.
# [TODO] Point
class Point(OGRGeometry):
    # [TODO] Point > _geos_ptr
    def _geos_ptr(self):
        from django.contrib.gis import geos

        return geos.Point._create_empty() if self.empty else super()._geos_ptr()

    # [TODO] Point > _create_empty
    @classmethod
    def _create_empty(cls):
        return capi.create_geom(OGRGeomType("point").num)

    # [TODO] Point > x
    @property
    def x(self):
        "Return the X coordinate for this Point."
        return capi.getx(self.ptr, 0)

    # [TODO] Point > y
    @property
    def y(self):
        "Return the Y coordinate for this Point."
        return capi.gety(self.ptr, 0)

    # [TODO] Point > z
    @property
    def z(self):
        "Return the Z coordinate for this Point."
        if self.coord_dim == 3:
            return capi.getz(self.ptr, 0)

    # [TODO] Point > tuple
    @property
    def tuple(self):
        "Return the tuple of this point."
        if self.coord_dim == 2:
            return (self.x, self.y)
        elif self.coord_dim == 3:
            return (self.x, self.y, self.z)

    coords = tuple


# [TODO] LineString
class LineString(OGRGeometry):
    # [TODO] LineString > __getitem__
    def __getitem__(self, index):
        "Return the Point at the given index."
        if 0 <= index < self.point_count:
            x, y, z = c_double(), c_double(), c_double()
            capi.get_point(self.ptr, index, byref(x), byref(y), byref(z))
            dim = self.coord_dim
            if dim == 1:
                return (x.value,)
            elif dim == 2:
                return (x.value, y.value)
            elif dim == 3:
                return (x.value, y.value, z.value)
        else:
            raise IndexError(
                "Index out of range when accessing points of a line string: %s." % index
            )

    # [TODO] LineString > __len__
    def __len__(self):
        "Return the number of points in the LineString."
        return self.point_count

    # [TODO] LineString > tuple
    @property
    def tuple(self):
        "Return the tuple representation of this LineString."
        return tuple(self[i] for i in range(len(self)))

    coords = tuple

    # [TODO] LineString > _listarr
    def _listarr(self, func):
        """
        Internal routine that returns a sequence (list) corresponding with
        the given function.
        """
        return [func(self.ptr, i) for i in range(len(self))]

    # [TODO] LineString > x
    @property
    def x(self):
        "Return the X coordinates in a list."
        return self._listarr(capi.getx)

    # [TODO] LineString > y
    @property
    def y(self):
        "Return the Y coordinates in a list."
        return self._listarr(capi.gety)

    # [TODO] LineString > z
    @property
    def z(self):
        "Return the Z coordinates in a list."
        if self.coord_dim == 3:
            return self._listarr(capi.getz)


# LinearRings are used in Polygons.
# [TODO] LinearRing
class LinearRing(LineString):
    pass


# [TODO] Polygon
class Polygon(OGRGeometry):
    # [TODO] Polygon > __len__
    def __len__(self):
        "Return the number of interior rings in this Polygon."
        return self.geom_count

    # [TODO] Polygon > __getitem__
    def __getitem__(self, index):
        "Get the ring at the specified index."
        if 0 <= index < self.geom_count:
            return OGRGeometry(
                capi.clone_geom(capi.get_geom_ref(self.ptr, index)), self.srs
            )
        else:
            raise IndexError(
                "Index out of range when accessing rings of a polygon: %s." % index
            )

    # Polygon Properties
    # [TODO] Polygon > shell
    @property
    def shell(self):
        "Return the shell of this Polygon."
        return self[0]  # First ring is the shell

    exterior_ring = shell

    # [TODO] Polygon > tuple
    @property
    def tuple(self):
        "Return a tuple of LinearRing coordinate tuples."
        return tuple(self[i].tuple for i in range(self.geom_count))

    coords = tuple

    # [TODO] Polygon > point_count
    @property
    def point_count(self):
        "Return the number of Points in this Polygon."
        # Summing up the number of points in each ring of the Polygon.
        return sum(self[i].point_count for i in range(self.geom_count))

    # [TODO] Polygon > centroid
    @property
    def centroid(self):
        "Return the centroid (a Point) of this Polygon."
        # The centroid is a Point, create a geometry for this.
        p = OGRGeometry(OGRGeomType("Point"))
        capi.get_centroid(self.ptr, p.ptr)
        return p


# Geometry Collection base class.
# [TODO] GeometryCollection
class GeometryCollection(OGRGeometry):
    "The Geometry Collection class."

    # [TODO] GeometryCollection > __getitem__
    def __getitem__(self, index):
        "Get the Geometry at the specified index."
        if 0 <= index < self.geom_count:
            return OGRGeometry(
                capi.clone_geom(capi.get_geom_ref(self.ptr, index)), self.srs
            )
        else:
            raise IndexError(
                "Index out of range when accessing geometry in a collection: %s."
                % index
            )

    # [TODO] GeometryCollection > __len__
    def __len__(self):
        "Return the number of geometries in this Geometry Collection."
        return self.geom_count

    # [TODO] GeometryCollection > add
    def add(self, geom):
        "Add the geometry to this Geometry Collection."
        if isinstance(geom, OGRGeometry):
            if isinstance(geom, self.__class__):
                for g in geom:
                    capi.add_geom(self.ptr, g.ptr)
            else:
                capi.add_geom(self.ptr, geom.ptr)
        elif isinstance(geom, str):
            tmp = OGRGeometry(geom)
            capi.add_geom(self.ptr, tmp.ptr)
        else:
            raise GDALException("Must add an OGRGeometry.")

    # [TODO] GeometryCollection > point_count
    @property
    def point_count(self):
        "Return the number of Points in this Geometry Collection."
        # Summing up the number of points in each geometry in this collection
        return sum(self[i].point_count for i in range(self.geom_count))

    # [TODO] GeometryCollection > tuple
    @property
    def tuple(self):
        "Return a tuple representation of this Geometry Collection."
        return tuple(self[i].tuple for i in range(self.geom_count))

    coords = tuple


# Multiple Geometry types.
# [TODO] MultiPoint
class MultiPoint(GeometryCollection):
    pass


# [TODO] MultiLineString
class MultiLineString(GeometryCollection):
    pass


# [TODO] MultiPolygon
class MultiPolygon(GeometryCollection):
    pass


# Class mapping dictionary (using the OGRwkbGeometryType as the key)
GEO_CLASSES = {
    1: Point,
    2: LineString,
    3: Polygon,
    4: MultiPoint,
    5: MultiLineString,
    6: MultiPolygon,
    7: GeometryCollection,
    101: LinearRing,
    1 + OGRGeomType.wkb25bit: Point,
    2 + OGRGeomType.wkb25bit: LineString,
    3 + OGRGeomType.wkb25bit: Polygon,
    4 + OGRGeomType.wkb25bit: MultiPoint,
    5 + OGRGeomType.wkb25bit: MultiLineString,
    6 + OGRGeomType.wkb25bit: MultiPolygon,
    7 + OGRGeomType.wkb25bit: GeometryCollection,
}