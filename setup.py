import setuptools


setuptools.setup(
    name="GES-echem-suite",
    version="0.1.7a",
    description="",
    long_description="",
    packages=["echemsuite"],
    package_data={'echemsuite': ['cellcycling/*', 'cyclicvoltammetry/*',],},
    install_requires=[],
)
