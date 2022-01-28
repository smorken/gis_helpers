import numpy as np
from osgeo import gdal
from spatial_inventory_rollback.raster import gdal_helpers
from spatial_inventory_rollback.raster import raster_chunks


def get_area(lat_range, cell_size):

    RadiusOfEarthInMeters = 6378137.0
    DiameterOfEarthInMetersPerDeg = 2.0 * np.pi * RadiusOfEarthInMeters / 360.0

    y_length = DiameterOfEarthInMetersPerDeg * cell_size
    deg_of_long_at_lat = (
        2
        * np.pi
        * RadiusOfEarthInMeters
        * np.cos(np.radians(lat_range))
        / 360.0
    )
    x_length = deg_of_long_at_lat * cell_size
    return x_length * y_length


def compute_areas(y_res, y_size, origin_y):
    """Computes an area column for a column of a north-up raster in
    wgs84 projection.

    Args:
        y_res (float): the raster resolution in wgs84 units
        y_size (int): the number of pixels in the raster column
        origin_y (float): the y coordinate of the upper left corner
            of the north most pixel in the column.

    Returns:
        numpy.ndarray: the array of areas along the column (north-most first)
    """
    cell_size = abs(y_res)

    # Converting pixels to latitude
    # Create index vector representing the vertical dimension (Latitude)
    y_range = np.arange(0, y_size)

    # Get latitude of index. Note: (yres/2) correspond to half a pixel
    lat_range = (y_range * y_res) + origin_y + (y_res / 2)

    # Create array of size with dimension of image
    # 1d array with dim of pixel per latitude
    area_vector = get_area(lat_range, cell_size)

    return area_vector


def create_wgs84_area_raster(
    src_path, out_path, scale_factor=1.0, max_chunk_size=5000 * 5000
):
    """Create a geotiff file whose value is area based on the specified
    projected src_path.  The output raster assumes the input raster's
    projection, resolution and dimension. The raster at src_path is assumed
    to be wgs84 and North up.

    Args:
        src_path (str): path to a wgs84 raster
        out_path (str): path to the output area raster
        scale_factor (float, optional): Conversion factor to multiply by the
            value on the output raster. The default units area m^2.  For
            example to convert to hectares set the scale_factor equal to
            0.0001. Defaults to 1.0.
        max_chunk_size (int, optional): The maximum number of pixels to store
            in memory when writing the output buffer. Defaults to 2.5e7.

    Raises:
        ValueError: The raster at the specified src_path is not a North up
            raster.
    """
    src = gdal.Open(src_path)
    origin_x, xres, x_skew, origin_y, y_skew, yres = src.GetGeoTransform()
    if x_skew != 0 or y_skew != 0:
        raise ValueError("raster must be North up")
    y_size = src.RasterYSize
    x_size = src.RasterXSize
    area_vector = compute_areas(yres, y_size, origin_y)

    if max_chunk_size < y_size:
        max_chunk_size = y_size

    chunks = raster_chunks.get_raster_chunks(
        width=x_size,
        height=y_size,
        chunk_width=max_chunk_size / area_vector.shape[0],
        chunk_height=y_size,
    )
    gdal_helpers.create_empty_raster(
        src_path,
        out_path,
        data_type=np.float32,
        nodata=-1.0,
        driver_name="GTiff",
        options=gdal_helpers.get_default_geotiff_creation_options(),
    )
    area_vector_col = area_vector.reshape((y_size, 1)) * scale_factor
    for chunk in chunks:
        gdal_helpers.write_output(
            out_path,
            data=np.repeat(area_vector_col, chunk.x_size, axis=1),
            x_off=chunk.x_off,
            y_off=0,
        )
