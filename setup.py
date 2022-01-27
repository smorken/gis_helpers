import os
from setuptools import setup
from setuptools import find_packages


this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

package_data = []


with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="gis_heleprs",
    version="0.1.0",
    description="Scripts to clean up CBM-CFS3 data",
    keywords=["cbm-cfs3"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="mit",
    packages=find_packages(exclude=["test*"]),
    package_data={"rollback_ipyleaflet": package_data},
    entry_points={},
    install_requires=requirements,
)
