from pathlib import Path
from setuptools import setup, find_packages 

current_dir = Path(__file__).parent.resolve()

with open(current_dir / "README.md", encoding="utf-8") as f:
    long_description = f.read()
    
setup(
    name="pydumbinit",
    version="0.1",
    py_modules=["pydumbinit"],
    url="https://github.com/isidentical/pydumbinit",
    description = "Simple init system that uses signal proxiying for managining children. Inspired from yelp/dumb-init",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    entry_points = {
        "console_scripts": [
            "pdinit = pydumbinit.main",
        ],
    },
)
