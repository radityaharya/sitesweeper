import sys
from setuptools import setup, find_packages

if sys.version_info[0] < 3:
    with open("README.md", "r") as fh:
        long_description = fh.read()
else:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()

setup(
    name="sitesweeper",
    version="1.0.2",
    description="Sitesweeper is a python package to help you automate your web scraping process, outputing pages to a file",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Raditya Harya",
    author_email="contact@radityaharya.com",
    url="https://github.com/radityaharya/sitesweeper",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4",
        "pdfkit",
        "requests",
        "PyPDF2",
        "lxml",
    ],
)
