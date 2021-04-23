
import os
import sys

here = (os.path.abspath(os.path.dirname(__file__)))
src = os.path.join(here, "src")
sys.path.append(src)

from setuptools import find_packages
from setuptools import setup

with open("README.md") as f:
    LONG_DESCRIPTION = f.read()
  
setup(
    
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    zip_safe=False,

    name="TripleStore",
    description="Python 3 triplestore for arbitrary entity relations and inference.",
    license= "MIT",
    url="https://github.com/amogorkon/triplestore",
    version="0.1.1",
    author="Anselm Kiefner",
    author_email="triplestore-pypi@anselm.kiefner.de",
    python_requires= ">=3.8",

    keywords=["triplestore", "rdf", "semantic", "web", "sparql"],
    classifiers=[
        "Development Status :: 3 - Alpha"
        "Intended Audience :: Developers"
        "Intended Audience :: Science/Research"
        "Intended Audience :: Information Technology"
        "Natural Language :: English"
        "License :: OSI Approved :: MIT License"
        "Operating System :: OS Independent"
        "Programming Language :: Python :: 3 :: Only"
        "Topic :: Scientific/Engineering :: Information Analysis"
        "Topic :: Database"
    ]
)
