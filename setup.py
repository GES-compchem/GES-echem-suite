import setuptools


setuptools.setup(
    name="GES-echem-suite",
    version="0.1.20a",
    description="",
    long_description="",
    packages=["echemsuite"],
    package_data={"echemsuite": ["cellcycling/*", "cyclicvoltammetry/*",],},
    install_requires=[],
)
