#!/usr/bin/env python

import os
# NOTE: Distutils requires unix path format so this won't work on windows
#       but we will never deploy on that platform
projdir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
import nltk


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        # PUT YOUR PRE-INSTALL SCRIPT HERE or CALL A FUNCTION
        develop.run(self)
        # PUT YOUR POST-INSTALL SCRIPT HERE or CALL A FUNCTION


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        # PUT YOUR PRE-INSTALL SCRIPT HERE or CALL A FUNCTION
        install.run(self)
        # PUT YOUR POST-INSTALL SCRIPT HERE or CALL A FUNCTION
        nltk.download('wordnet')
        nltk.download('punkt')


setup(
    name='marbles',
    version='0.1',
    description='Marbles AI SDK',
    author='Marbles AI, Inc.',
    license='Marbles AI Proprietary License',
    url='http://www.marbles.ai',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: Other/Proprietary License',
        'Programming Language :: Python :: 2.7',
        'Topic :: Text Processing :: Linguistic',
    ],
    packages=find_packages(exclude=['*.test', '*.test.*', 'test.*', '*.log', '*.nlp', 'nlp.*', '*.nlp.*']),
    package_data={
        'marbles.newsfeed': ['data/phantomjs'],
        'marbles.ie.ccg': ['data/*.dat', 'data/phantomjs', 'data/vnxml/*.xml'],
        'marbles.ie.kb': ['data/vnxml/*.xml'],
    },
    install_requires=[
        'networkx',
        'pypeg2',
        'rdflib',
        'nltk',
        'statistics',
        'protobuf==3.2.0',
        'grpcio==1.1.3',
        'selenium',
        'beautifulsoup4',
        'feedparser',
        'wikipedia',
        'boto3',
        'feedgen',
        'watchtower',
        'requests',
        'python_daemon',
        'regex'
    ],
    scripts=[
        'services/ccgparser/ccgparser.py',
        'services/newsreader/newsreader.py'
    ],
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
    include_package_data=True,
    zip_safe=False,
    # If we split into newsfeed and ie then this is required
    #namespace_packages=['marbles']
)
