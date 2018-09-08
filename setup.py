#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='dataclass_factory',
    description='An utility class for creating instances of dataclasses',
    long_description='An utility class for creating instances of dataclasses previously converted using with asdict()',
    version='0.4',
    url='https://github.com/tishka17/dataclass_factory',
    author='A. Tikhonov',
    author_email='17@itishka.org',
    license='Apache2',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3'
    ],
    packages=['dataclass_factory'],
    install_requires=[
        'dataclasses',
    ],
)
