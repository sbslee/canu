from setuptools import setup, find_packages
from pathlib import Path

long_description = (Path(__file__).parent / "README.md").read_text()

exec(open("canu/version.py").read())

setup(
    name="canu",
    version=__version__,
    author='Seung-been "Steven" Lee',
    author_email="sbstevenlee@gmail.com",
    description="An opinionated tool for managing your chatbot projects",
    url="https://github.com/sbslee/canu",
    packages=find_packages(),
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown"
)