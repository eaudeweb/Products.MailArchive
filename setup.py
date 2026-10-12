""" MailArchive installer
"""
import os
from setuptools import setup, find_namespace_packages

NAME = 'Products.MailArchive'
VERSION = '1.6'

setup(name=NAME,
      version=VERSION,
      description="Browse a mail archive in Unix MBOX format",
      long_description=open("README.rst").read(),
      classifiers=[
           "Framework :: Zope2",
           "Programming Language :: Python",
           "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='eea',
      author='European Environment Agency (EEA)',
      author_email='webadmin@eea.europa.eu',
      url="https://github.com/eea/Products.MailArchive",
      license='GPL',
      packages=find_namespace_packages(include=['Products.*']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
      ],
      )
