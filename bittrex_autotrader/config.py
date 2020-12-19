"""
  bittrex_autotrader
  Bittrex currency exchange autotrading script in a nutshell.

  Copyright 2018-2020, Marc S. Brooks (https://mbrooks.info)
  Licensed under the MIT license:
  http://www.opensource.org/licenses/mit-license.php
"""

# Standard libraries.
import sys

# External modules.
import argparse
import configparser
import pkg_resources

def values():
    """
    Return command-line arguments / configuration values as a dictionary.

    Returns:
        dict

    .. seealso:: bittrex_autotrader.conf.example
    """
    argv = sys.argv

    arg_parser = argparse.ArgumentParser()

    # Configuration options can be passed as script arguments.
    arg_parser.add_argument(
        '--conf',
        help='Configuration file (bittrex_autotrader.conf)',
        metavar='FILE'
    )

    arg_parser.add_argument(
        '--apikey',
        help='Bittrex issued API key.',
        required='--conf' not in argv
    )

    arg_parser.add_argument(
        '--secret',
        help='Bittrex issued API secret.',
        required='--conf' not in argv
    )

    arg_parser.add_argument(
        '--market',
        help='String literal for the market (ie. BTC-LTC)',
        default='BTC-LTC'
    )

    arg_parser.add_argument(
        '--units',
        help='BUY/SELL total units (default: 1.0)',
        default='1.0'
    )

    arg_parser.add_argument(
        '--spread',
        help='BUY/SELL markup/markdown percentage (default: 0.1/0.1)',
        default='0.1/0.1'
    )

    arg_parser.add_argument(
        '--method',
        help='Moving Average calculation method (default: arithmetic)',
        default='arithmetic'
    )

    arg_parser.add_argument(
        '--delay',
        help='Seconds to delay order status requests (default: 30)',
        default='30'
    )

    arg_parser.add_argument(
        '--prompt',
        help='Require user interaction to begin trading (default: true)',
        default=True
    )

    arg_parser.add_argument(
        '--version',
        action='version',
        version=pkg_resources.get_distribution('bittrex_autotrader').version
    )

    args, _ = arg_parser.parse_known_args()

    # Return configuration values from file.
    if args.conf:
        config_parser = configparser.ConfigParser()
        config_parser.read([args.conf])

        return dict(config_parser.items('config'))

    # Return command-line argument values.
    return vars(args)
