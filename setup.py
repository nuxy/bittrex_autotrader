from setuptools import setup

version = '0.1.0'

setup(
  name = 'bittrex_autotrader',
  packages = ['bittrex_autotrader'],
  version = version,
  description = 'Bittrex currency exchange autotrading script in a nutshell.',
  author = 'Marc S. Brooks',
  author_email = 'devel@mbrooks.info',
  url = 'https://github.com/nuxy/bittrex_autotrader',
  download_url = 'https://github.com/nuxy/bittrex_autotrader/archive/0.0.{0}.tar.gz'.format(version),
  keywords = ['trading-bot', 'api-client', 'cryptocurrency', 'bittrex'],
  install_requires = ['humanfriendly >= 4.4.1', 'numpy >= 1.13.1', 'requests >= 2.20.0'],
  scripts = ['bittrex_autotrader/bittrex_autotrader'],
  long_description = open('README.rst', 'r').read(),
)
