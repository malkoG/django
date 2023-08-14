from django.contrib.gis import gdal


# [TODO] SpatialRefSysMixin
class SpatialRefSysMixin:
    """
    The SpatialRefSysMixin is a class used by the database-dependent
    SpatialRefSys objects to reduce redundant code.
    """

    # [TODO] SpatialRefSysMixin > srs
    @property
    def srs(self):
        """
        Return a GDAL SpatialReference object.
        """
        # TODO: Is caching really necessary here?  Is complexity worth it?
        if hasattr(self, "_srs"):
            # Returning a clone of the cached SpatialReference object.
            return self._srs.clone()
        else:
            # Attempting to cache a SpatialReference object.

            # Trying to get from WKT first.
            try:
                self._srs = gdal.SpatialReference(self.wkt)
                return self.srs
            except Exception as e:
                msg = e

            try:
                self._srs = gdal.SpatialReference(self.proj4text)
                return self.srs
            except Exception as e:
                msg = e

            raise Exception(
                "Could not get OSR SpatialReference from WKT: %s\nError:\n%s"
                % (self.wkt, msg)
            )

    # [TODO] SpatialRefSysMixin > ellipsoid
    @property
    def ellipsoid(self):
        """
        Return a tuple of the ellipsoid parameters:
        (semimajor axis, semiminor axis, and inverse flattening).
        """
        return self.srs.ellipsoid

    # [TODO] SpatialRefSysMixin > name
    @property
    def name(self):
        "Return the projection name."
        return self.srs.name

    # [TODO] SpatialRefSysMixin > spheroid
    @property
    def spheroid(self):
        "Return the spheroid name for this spatial reference."
        return self.srs["spheroid"]

    # [TODO] SpatialRefSysMixin > datum
    @property
    def datum(self):
        "Return the datum for this spatial reference."
        return self.srs["datum"]

    # [TODO] SpatialRefSysMixin > projected
    @property
    def projected(self):
        "Is this Spatial Reference projected?"
        return self.srs.projected

    # [TODO] SpatialRefSysMixin > local
    @property
    def local(self):
        "Is this Spatial Reference local?"
        return self.srs.local

    # [TODO] SpatialRefSysMixin > geographic
    @property
    def geographic(self):
        "Is this Spatial Reference geographic?"
        return self.srs.geographic

    # [TODO] SpatialRefSysMixin > linear_name
    @property
    def linear_name(self):
        "Return the linear units name."
        return self.srs.linear_name

    # [TODO] SpatialRefSysMixin > linear_units
    @property
    def linear_units(self):
        "Return the linear units."
        return self.srs.linear_units

    # [TODO] SpatialRefSysMixin > angular_name
    @property
    def angular_name(self):
        "Return the name of the angular units."
        return self.srs.angular_name

    # [TODO] SpatialRefSysMixin > angular_units
    @property
    def angular_units(self):
        "Return the angular units."
        return self.srs.angular_units

    # [TODO] SpatialRefSysMixin > units
    @property
    def units(self):
        "Return a tuple of the units and the name."
        if self.projected or self.local:
            return (self.linear_units, self.linear_name)
        elif self.geographic:
            return (self.angular_units, self.angular_name)
        else:
            return (None, None)

    # [TODO] SpatialRefSysMixin > get_units
    @classmethod
    def get_units(cls, wkt):
        """
        Return a tuple of (unit_value, unit_name) for the given WKT without
        using any of the database fields.
        """
        return gdal.SpatialReference(wkt).units

    # [TODO] SpatialRefSysMixin > get_spheroid
    @classmethod
    def get_spheroid(cls, wkt, string=True):
        """
        Class method used by GeometryField on initialization to
        retrieve the `SPHEROID[..]` parameters from the given WKT.
        """
        srs = gdal.SpatialReference(wkt)
        sphere_params = srs.ellipsoid
        sphere_name = srs["spheroid"]

        if not string:
            return sphere_name, sphere_params
        else:
            # `string` parameter used to place in format acceptable by PostGIS
            if len(sphere_params) == 3:
                radius, flattening = sphere_params[0], sphere_params[2]
            else:
                radius, flattening = sphere_params
            return 'SPHEROID["%s",%s,%s]' % (sphere_name, radius, flattening)

    # [TODO] SpatialRefSysMixin > __str__
    def __str__(self):
        """
        Return the string representation, a 'pretty' OGC WKT.
        """
        return str(self.srs)