import os
from contextlib import contextmanager
import numpy as np
from osgeo import gdal
from osgeo import gdal_array
from spatial_inventory_rollback.raster.raster_bound import RasterBound
from spatial_inventory_rollback.application import log_helper

logger = log_helper.get_logger()


class GDALHelperDataset:
    def __init__(
        self,
        path: str,
        data: np.ndarray,
        data_bounds: RasterBound,
        raster_bounds: RasterBound,
        nodata: int,
    ):
        self.path = path
        self.data = data
        self.data_bounds = data_bounds
        self.raster_bounds = raster_bounds
        self.nodata = nodata


@contextmanager
def __open(*args):
    """pass args to gdal.Open

    Raises:
        ValueError: raised if the first arg is not an existing file
        ValueError: gdal.Open did not return an open dataset

    Returns:
        object: return value of gdal.Open
    """
    if not os.path.exists(args[0]):
        raise ValueError("specified path does not exist {}".format(args[0]))
    dataset = gdal.Open(*args)
    if not dataset:
        raise ValueError("failed to open '{}'".format(args[0]))
    try:
        yield dataset
    finally:
        del dataset


@contextmanager
def __open_band(band_num, *args):
    with __open(*args) as dataset:
        band = dataset.GetRasterBand(band_num)
        try:
            yield band
        finally:
            del band


def get_raster_dimension(path):
    """Gets the pixel dimension of the raster at the specified path.

    Args:
        path (str): path to a raster dataset

    Returns:
        RasterBound: object with the pixel extent of the raster
    """
    with __open(path) as dataset:
        bounds = RasterBound(0, 0, dataset.RasterXSize, dataset.RasterYSize)
        return bounds


def get_raster_no_data(path, band_num=1):
    """Get the no-data value from the raster at the specified path

    Args:
        path (str): the path to a raster dataset
        band_num (int, optional): The band number for which to fetch the
            no_data value. Defaults to 1.

    Returns:
        float: the no_data value for the raster
    """
    with __open_band(band_num, path) as band:
        return band.GetNoDataValue()


def write_output(path, data, x_off, y_off, band_num=1):
    """write a rectangular output to the specified raster dataset

    Args:
        path (str): path to a raster dataset
        data (numpy.ndarray): 2d data rectangle to write
        x_off (int): the x raster coordinate of the upper left corner of the
            data rectangle
        y_off (int): the y raster coordinate of the upper left corner of the
            data rectangle
    """
    logger.debug(
        f"writing raster {path} size: {data.shape} offset: ({x_off}, {y_off})"
    )
    with __open_band(band_num, path, gdal.GA_Update) as band:
        band.WriteArray(data, x_off, y_off)


def read_dataset(path, bounds=None, raster_band=1):
    """Read an entire raster or a rectangular section of a raster

    Args:
        path (str): path to a raster dataset
        bounds (RasterBound, optional): if specified defines the rectangular
            section to read
        raster_band (int, optional): the raster band to read. Defaults to 1.

    Raises:
        ValueError: the specified coordinate parameters are out of bounds

    Returns:
        object: an object with fields:

            - path: the path to the raster dataset
            - data: a 2d array of the raster data
            - data_bounds: a raster_bound object specifying the pixel extent
                of the returned data
            - raster_bounds: a raster_bound object specifying the pixel extent
                of the entire raster
            - nodata: the raster nodata value
    """

    with __open(path) as dataset:
        x_off = 0
        y_off = 0
        x_size = dataset.RasterXSize
        y_size = dataset.RasterYSize
        if bounds:
            if bounds.x_size < 1 or bounds.y_size < 1:
                raise ValueError("x_size, y_size may not be less than 1")
            if bounds.x_off < 0 or bounds.y_off < 0:
                raise ValueError("x_off, y_off may not be less than 0")
            if x_size - bounds.x_off < bounds.x_size:
                raise ValueError("x_off, x_size out of bounds")
            if y_size - bounds.y_off < bounds.y_size:
                raise ValueError("y_off, y_size out of bounds")
            x_off = bounds.x_off
            y_off = bounds.y_off
            x_size = bounds.x_size
            y_size = bounds.y_size

        band = dataset.GetRasterBand(raster_band)
        logger.debug(
            f"reading raster {path} size: ({x_size}, {y_size}) "
            f"offset: ({x_off}, {y_off})"
        )
        result = GDALHelperDataset(
            path=path,
            data=np.array(band.ReadAsArray(x_off, y_off, x_size, y_size)),
            data_bounds=RasterBound(x_off, y_off, x_size, y_size),
            raster_bounds=RasterBound(
                0, 0, dataset.RasterXSize, dataset.RasterYSize
            ),
            nodata=band.GetNoDataValue(),
        )

        del band
        return result


def get_default_geotiff_creation_options():
    """Returns package default gdal options for creating geotiff rasters.

    Returns:
        list: list of options
    """
    return ["COMPRESS=DEFLATE", "BIGTIFF=YES"]


def create_empty_raster(
    source_path,
    dest_path,
    driver_name=None,
    data_type=None,
    nodata=None,
    raster_band=1,
    options=[],
):
    """
    Create an empty single band raster file based on the dimensions and
    geospatial metadata of the source raster. The created raster optionally
    takes on datatype and nodata of the source raster.

    Args:
        source_path (str): path to the source raster
        dest_path (str): path to the created raster
        driver_name (str, optional): name of gdal driver to use. For example
            'GTiff'.  If not specified, the source_path's driver type is used.
        data_type (int, optional): A numeric type defined in numpy. If not
            specified the source raster data type is used. Defaults to None.
        nodata (float, int, optional): The nodata value to use in the new
            raster. If not specified the nodata value defined in the source
            raster is used. Defaults to None.
        raster_band (int, optional): The raster band in the source raster to
            reference. Defaults to 1.
        options (list, optional): list of creation options passed to gdal
            driver.Create options parameter
    """
    if not options:
        options = []
    with __open(source_path) as source_dataset:
        driver = None
        if driver_name:
            driver = gdal.GetDriverByName(driver_name)
        else:
            driver = source_dataset.GetDriver()
        if data_type:
            gdal_data_type = gdal_array.NumericTypeCodeToGDALTypeCode(
                data_type
            )
            if not gdal_data_type:
                raise ValueError(
                    f"specified data_type {data_type} is not convertable to "
                    "a gdal data type."
                )
        else:
            gdal_data_type = source_dataset.GetRasterBand(raster_band).DataType

        new_dataset = driver.Create(
            dest_path,
            int(source_dataset.RasterXSize),
            int(source_dataset.RasterYSize),
            1,
            gdal_data_type,
            options,
        )
        new_dataset.SetGeoTransform(source_dataset.GetGeoTransform())
        new_dataset.SetProjection(source_dataset.GetProjection())
        if nodata is not None:
            new_dataset.GetRasterBand(1).SetNoDataValue(nodata)
        else:
            new_dataset.GetRasterBand(1).SetNoDataValue(
                source_dataset.GetRasterBand(raster_band).GetNoDataValue()
            )

        del new_dataset
