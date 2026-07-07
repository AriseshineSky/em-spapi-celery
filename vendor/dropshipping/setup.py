# -*- coding: utf-8 -*-

from os import path
from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'dropshipping', 'VERSION'), 'rb') as f:
  version = f.read().decode('ascii').strip()

setup(
  name='dropshipping',
  version=version,
  description='A library aims to support dropshipping amazon',
  url='https://bitbucket.org/johnnyxiang/dropshipping',
  author='Neal Wong',
  author_email='neal.wkacc@gmail.com,johnnyxiang2017@gmail.com',
  license='MIT',
  packages=find_packages(),
  include_package_data=True,
  install_requires=[
    'requests',
    'mws<=0.8.9',
    'elasticsearch<7.0.0',
    'wrapt',
    'PyPyDispatcher',
    'pyyaml',
    'six',
    'pydispatch',
    'python-amazon-sp-api==1.4.3',
    'dataclasses',
    'python-telegram-bot<=12.8',
  ],
)
