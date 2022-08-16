import setuptools


setuptools.setup(
    name="GES-echem-suite",
    version="0.2.0a",
    description="",
    long_description="",
    packages=["echemsuite"],
    package_data={"echemsuite": ["cellcycling/*", "cyclicvoltammetry/*",],},
    install_requires=[],
)
