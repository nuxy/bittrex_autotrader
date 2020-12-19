"""
  bittrex_autotrader
  Bittrex currency exchange autotrading script in a nutshell.

  Copyright 2018-2020, Marc S. Brooks (https://mbrooks.info)
  Licensed under the MIT license:
  http://www.opensource.org/licenses/mit-license.php
"""

# Standard libraries.
import setuptools

VERSION = '0.1.0'

setuptools.setup(
    name='bittrex_autotrader',
    version=VERSION,
    author='Marc S. Brooks',
    author_email='devel@mbrooks.info',
    description='Bittrex currency exchange autotrading script in a nutshell.',
    long_description=open('README.rst', 'r').read(),
    url='https://github.com/nuxy/bittrex_autotrader',
    download_url='https://github.com/nuxy/bittrex_autotrader/archive/{0}.tar.gz'.format(VERSION),
    packages=setuptools.find_packages(),
    scripts=['bin/bittrex_autotrader'],
    keywords=['trading-bot', 'api-client', 'cryptocurrency', 'bittrex'],
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Utilities',
    ]
)
