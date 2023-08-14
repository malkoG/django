from ctypes import c_uint

from django.contrib.gis import gdal
from django.contrib.gis.geos import prototypes as capi
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.geometry import GEOSGeometry


# [TODO] Point
class Point(GEOSGeometry):
    _minlength = 2
    _maxlength = 3
    has_cs = True

    # [TODO] Point > __init__
    def __init__(self, x=None, y=None, z=None, srid=None):
        """
        The Point object may be initialized with either a tuple, or individual
        parameters.

        For example:
        >>> p = Point((5, 23))  # 2D point, passed in as a tuple
        >>> p = Point(5, 23, 8)  # 3D point, passed in with individual parameters
        """
        if x is None:
            coords = []
        elif isinstance(x, (tuple, list)):
            # Here a tuple or list was passed in under the `x` parameter.
            coords = x
        elif isinstance(x, (float, int)) and isinstance(y, (float, int)):
            # Here X, Y, and (optionally) Z were passed in individually, as parameters.
            if isinstance(z, (float, int)):
                coords = [x, y, z]
            else:
                coords = [x, y]
        else:
            raise TypeError("Invalid parameters given for Point initialization.")

        point = self._create_point(len(coords), coords)

        # Initializing using the address returned from the GEOS
        #  createPoint factory.
        super().__init__(point, srid=srid)

    # [TODO] Point > _to_pickle_wkb
    def _to_pickle_wkb(self):
        return None if self.empty else super()._to_pickle_wkb()

    # [TODO] Point > _from_pickle_wkb
    def _from_pickle_wkb(self, wkb):
        return self._create_empty() if wkb is None else super()._from_pickle_wkb(wkb)

    # [TODO] Point > _ogr_ptr
    def _ogr_ptr(self):
        return (
            gdal.geometries.Point._create_empty() if self.empty else super()._ogr_ptr()
        )

    # [TODO] Point > _create_empty
    @classmethod
    def _create_empty(cls):
        return cls._create_point(None, None)

    # [TODO] Point > _create_point
    @classmethod
    def _create_point(cls, ndim, coords):
        """
        Create a coordinate sequence, set X, Y, [Z], and create point
        """
        if not ndim:
            return capi.create_point(None)

        if ndim < 2 or ndim > 3:
            raise TypeError("Invalid point dimension: %s" % ndim)

        cs = capi.create_cs(c_uint(1), c_uint(ndim))
        i = iter(coords)
        capi.cs_setx(cs, 0, next(i))
        capi.cs_sety(cs, 0, next(i))
        if ndim == 3:
            capi.cs_setz(cs, 0, next(i))

        return capi.create_point(cs)

    # [TODO] Point > _set_list
    def _set_list(self, length, items):
        ptr = self._create_point(length, items)
        if ptr:
            srid = self.srid
            capi.destroy_geom(self.ptr)
            self._ptr = ptr
            if srid is not None:
                self.srid = srid
            self._post_init()
        else:
            # can this happen?
            raise GEOSException("Geometry resulting from slice deletion was invalid.")

    # [TODO] Point > _set_single
    def _set_single(self, index, value):
        self._cs.setOrdinate(index, 0, value)

    # [TODO] Point > __iter__
    def __iter__(self):
        "Iterate over coordinates of this Point."
        for i in range(len(self)):
            yield self[i]

    # [TODO] Point > __len__
    def __len__(self):
        "Return the number of dimensions for this Point (either 0, 2 or 3)."
        if self.empty:
            return 0
        if self.hasz:
            return 3
        else:
            return 2

    # [TODO] Point > _get_single_external
    def _get_single_external(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        elif index == 2:
            return self.z

    _get_single_internal = _get_single_external

    # [TODO] Point > x
    @property
    def x(self):
        "Return the X component of the Point."
        return self._cs.getOrdinate(0, 0)

    # [TODO] Point > x
    @x.setter
    def x(self, value):
        "Set the X component of the Point."
        self._cs.setOrdinate(0, 0, value)

    # [TODO] Point > y
    @property
    def y(self):
        "Return the Y component of the Point."
        return self._cs.getOrdinate(1, 0)

    # [TODO] Point > y
    @y.setter
    def y(self, value):
        "Set the Y component of the Point."
        self._cs.setOrdinate(1, 0, value)

    # [TODO] Point > z
    @property
    def z(self):
        "Return the Z component of the Point."
        return self._cs.getOrdinate(2, 0) if self.hasz else None

    # [TODO] Point > z
    @z.setter
    def z(self, value):
        "Set the Z component of the Point."
        if not self.hasz:
            raise GEOSException("Cannot set Z on 2D Point.")
        self._cs.setOrdinate(2, 0, value)

    # ### Tuple setting and retrieval routines. ###
    # [TODO] Point > tuple
    @property
    def tuple(self):
        "Return a tuple of the point."
        return self._cs.tuple

    # [TODO] Point > tuple
    @tuple.setter
    def tuple(self, tup):
        "Set the coordinates of the point with the given tuple."
        self._cs[0] = tup

    # The tuple and coords properties
    coords = tuple