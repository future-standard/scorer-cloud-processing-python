#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup


def main():
    setup(
        name="scorer-cloudprocessing",
        version="0.1.3",
        description="A Software Development Kit for Scorer Cloud Processing",
        packages=["scorer"],
        install_requires=["pyzmq", "numpy"],
    )


if __name__ == "__main__":
    main()
