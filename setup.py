from distutils.core import setup

version = '0.0.6'

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
  classifiers = [],
)
