import rasterio
from rasterio.features import shapes


def tiff_to_geo_json(tiff_path: str) -> dict:
    """Returns the features in the specified tiff path as a geo-json formatted
    dict.  Best suited for categorical data rather than continuous variables
    which will make at worst a polygon per pixel.

    Args:
        tiff_path (str): path to a geo-tiff file

    Returns:
        dict: a geo json "FeatureCollection" dictionary
    """
    mask = None
    with rasterio.Env():
        with rasterio.open(tiff_path) as src:
            image = src.read(1)  # first band
            results = (
                {
                    "type": "Feature",
                    "properties": {"raster_val": v},
                    "geometry": s,
                }
                for i, (s, v) in enumerate(
                    shapes(image, mask=mask, transform=src.transform)
                )
            )

    result = {"type": "FeatureCollection", "features": list(results)}
    return result
