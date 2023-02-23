"""Setup package"""

from setuptools import setup, find_packages  # type: ignore

with open("README.md", "r") as fh: # pylint: disable=unspecified-encoding
    LONG_DESCRIPTION = fh.read()

setup(
    name="pyrinnaitouch",
    packages=find_packages(exclude=["tests", "tests.*"]),
    version="0.12.4",
    license="mit",
    description="A python interface to the Rinnai Touch Wifi controller",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Funtastix",
    url="https://github.com/funtastix/pyrinnaitouch",
    download_url="https://github.com/funtastix/pyrinnaitouch/archive/refs/tags/v0.12.1.tar.gz",
    keywords=[
        "Rinnai Touch",
        "Brivis",
        "IoT",
    ],
    python_requires=">=3.9",
    tests_require=["pytest"],
    install_requires=[
        "asyncio",
        "async_timeout",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Home Automation",
        "Topic :: System :: Hardware",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
