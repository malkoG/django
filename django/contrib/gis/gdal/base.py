from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.ptr import CPointerBase


# [TODO] GDALBase
class GDALBase(CPointerBase):
    null_ptr_exception_class = GDALException