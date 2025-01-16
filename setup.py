import pathlib

from setuptools import find_packages, setup

LONG_DESCRIPTION = pathlib.Path("README.md").read_text()

setup(
    name="TripleStore",
    version="0.2.0",
    description="Python 3 triplestore for arbitrary entity relations and inference.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/amogorkon/triplestore",
    author="Anselm Kiefner",
    author_email="triplestore-pypi@anselm.kiefner.de",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.12",
    keywords=["triplestore", "rdf", "semantic", "web", "sparql"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Information Technology",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
    ],
    zip_safe=False,
)
