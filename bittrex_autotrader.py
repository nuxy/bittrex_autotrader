#!/usr/bin/env python

"""
  bittrex_autotrader.py
  Bittrex currency exchange autotrading script in a nutshell.

  Copyright 2017, Marc S. Brooks (https://mbrooks.info)
  Licensed under the MIT license:
  http://www.opensource.org/licenses/mit-license.php

  Dependencies:
    humanfriendly
    numpy
    requests

  Notes:
   - This script has been tested to work with Unix-like operating systems
   - This script can be run via cronjob

  .. seealso:: https://bittrex.com/Home/Api
"""

import argparse
import ConfigParser
import csv
import hashlib
import hmac
import humanfriendly
import numpy
import requests
import StringIO
import sys
import time

#
# Bittrex API autotrader object.
#
class BittrexAutoTrader(object):
    """
    Bittrex API autotrader object.

    Dependencies:
        humanfriendly
        numpy
    """

    def __init__(self, options):
        """
        Create a new instance of BittrexAutoTrader

        Args:
            options (dict):
                Dictionary of options.

        Attributes:
            apiReq (BittrexApiRequest):
                Instance of BittrexApiRequest object.
            market (str):
                String literal for the market (ie. BTC-LTC).
            units (float):
                BUY/SELL total units.
            spread (array):
                BUY/SELL markup/markdown percentage.
            method (str):
                Moving Average calculation method.
            delay (str):
                Seconds to delay order status requests (default: 30).
            orders (list):
                List of orders as dictionary items.
            active (int):
                Incremented value for orders.
        """
        self.apiReq = BittrexApiRequest(options['apikey'], options['secret'])
        self.market = options['market']
        self.units  = options['units']
        self.spread = options['spread'].split('/')
        self.method = options['method']
        self.delay  = options['delay']
        self.orders = []
        self.active = 0

    def run(self):
        """
        Prompt transaction type and start trading.
        """

        # Prompt for first transaction type (trade BUY/SELL).
        prompt_choice = humanfriendly.prompt_for_choice(
            [
                'BUY in at markdown (need units to trade)',
                'SELL out at markup (need liquidity)'
            ],
            default='SELL'
        )

        next_trade = prompt_choice.split(' ', 1)[0]

        while True:

            # Check for open orders.
            if self.orders:
                order = self.apiReq.account_order(
                    self.orders[self.active - 1]['OrderUuid']
                )

                if order['IsOpen']:
                    BittrexAutoTrader._wait(seconds=float(self.delay))
                    continue

            # Submit a new order.
            self.submit_order(next_trade)

            next_trade = 'BUY' if next_trade == 'SELL' else 'SELL'

    def submit_order(self, trade_type='BUY'):
        """
        Submit an order to the Bittrex API.

        Args:
            trade_type (str):
                BUY or SELL (default: BUY).
        """

        # Get BUY/SELL order market totals.
        market_totals = self.get_market_totals(trade_type)

        market_max = round(market_totals.max(), 8)

        # Calculate Moving Average (TODO: weights).
        if self.method == 'weighted':
            moving_avg = round(market_totals.average(weights=None), 8)
        else:
            moving_avg = round(market_totals.mean(), 8)

        # Get current ASK/BID orders.
        ticker = self.apiReq.public_ticker(self.market)

        # Calculate units (50k Satoshi min requirement).
        total_units = 0.0005 / float(ticker['Last'])
        if total_units < self.units:
            total_units = self.units

        # Format human-friendly results.
        currency_symbol = self.market.replace('BTC-', '')

        stdout = {
            'cols': [trade_type, currency_symbol],
            'rows': []
        }

        # Perform trade operation.
        if trade_type == 'BUY':
            ticker_bid = float(ticker['Bid'])
            trader_bid = round(
                (ticker_bid - (ticker_bid * float(self.spread[1]))), 8
            )

            stdout['rows'].append(['Avg', format(moving_avg, '.8f')])
            stdout['rows'].append(['Max', format(market_max, '.8f')])
            stdout['rows'].append(['Ask', format(ticker_bid, '.8f')])
            stdout['rows'].append(['Bid', format(trader_bid, '.8f')])

            uuid = (self.apiReq.market_buy_limit(
                self.market, total_units, trader_bid
            ))['uuid']
        else:
            ticker_ask = float(ticker['Ask'])
            trader_ask = round(
                (ticker_ask + (ticker_ask * float(self.spread[0]))), 8
            )

            stdout['rows'].append(['Avg', format(moving_avg, '.8f')])
            stdout['rows'].append(['Max', format(market_max, '.8f')])
            stdout['rows'].append(['Bid', format(ticker_ask, '.8f')])
            stdout['rows'].append(['Ask', format(trader_ask, '.8f')])

            uuid = (self.apiReq.market_sell_limit(
                self.market, total_units, trader_ask
            ))['uuid']

        # Store and index the order data.
        self.orders.append(self.apiReq.account_order(uuid))
        self.active += 1

        # Output human-friendly results.
        print humanfriendly.tables.format_pretty_table(
            stdout['rows'],
            stdout['cols']
        ), "\n", time.strftime(' %Y-%m-%d %H:%M:%S '), "\n"

    def get_market_totals(self, trade_type='SELL'):
        """
        Returns BUY/SELL order market totals as ndarray.

        Args:
            trade_type (str):
                BUY or SELL (default: BUY).

        Returns:
            ndarray
        """
        market_history = self.apiReq.public_market_history(self.market)

        return BittrexAutoTrader._numpy_loadtxt(
            BittrexAutoTrader._list_of_dict_filter_by(
                market_history, 'OrderType', trade_type
            ),
            ['Price']
        )

    @staticmethod
    def _list_of_dict_filter_by(data, key, value):
        """
        Returns list of dictionary items filtered by key/value.

        Args:
            data (dict):
                Data to filter.
            key (str):
                Dictionary key search.
            value (str):
                Dictionary key value match.

        Returns:
            list
        """
        return [
            item for i, item in enumerate(data) if data[i].get(key) == value
        ]

    @staticmethod
    def _list_of_dict_to_csv(data, keys=None):
        """
        Returns list of prefiltered dictionary items as CSV string.

        Args:
            data (dict):
                Data to convert.
            keys (list):
                Columns to exclude from result.

        Returns:
            string
        """
        output = StringIO.StringIO()

        # Filter items by key names.
        writer = csv.DictWriter(output, fieldnames=keys)
        for item in data:
            filtered_item = dict(
                (key, value) for key, value in item.iteritems() if key in keys
            )
            writer.writerow(filtered_item)

        return output.getvalue()

    @staticmethod
    def _numpy_calc_sma(a, n):
        """
        Return Simple Moving Average for a given data sequence.

        Args:
            a (list):
                One-dimensional input array.
            n (int):
                Number of days (n-day).

        Returns:
            list
        """
        return numpy.convolve(a, numpy.ones((n,)) / n, mode='valid')

    @staticmethod
    def _numpy_loadtxt(data, keys=None, converters=None):
        """
        Returns list of prefiltered dictionary items as ndarray.

        Args:
            data: dict
                Data to convert.
            keys: list
                Columns to exclude from result.

        Returns:
            ndarray
        """
        return numpy.loadtxt(
            StringIO.StringIO(
                BittrexAutoTrader._list_of_dict_to_csv(data, keys)
            ),
            converters=converters,
            delimiter=',',
            unpack=True
        )

    @staticmethod
    def _wait(label='Waiting', seconds=10, timer=False):
        """
        Suspend execution for given number of seconds while showing a spinner.

        Args:
            label (str):
                The label for the spinner (default: Waiting).
            seconds (float):
                Seconds to delay execution (default: 10).
            timer (bool):
                Show the elapsed time (default: False).
        """
        with humanfriendly.AutomaticSpinner(label, show_time=timer) as spinner:
            time.sleep(seconds)

#
# Bittrex AutoTrader config object.
#
class BittrexAutoTraderConfig(object):
    """
    Bittrex AutoTrader config object.
    """

    @staticmethod
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

        args, remaining_args = arg_parser.parse_known_args()

        # Return configuration values from file.
        if args.conf:
            config_parser = ConfigParser.SafeConfigParser()
            config_parser.read([args.conf])

            return dict(config_parser.items('config'))

        # Return command-line argument values.
        else:
            return vars(args)

#
# Bittrex API request object.
#
class BittrexApiRequest(object):
    """
    Bittrex API request object.

    Dependencies:
        requests
    """

    BASE_URL = 'https://bittrex.com/api/v1.1/'

    def __init__(self, apikey, secret):
        """
        Create a new instance of the BittrexApiRequest

        Args:
            apikey (str):
                Bittrex issued API key.
            secret (str):
                Bittrex issued API secret.

        Attributes:
            apikey (str):
                Bittrex issued API key.
            secret (str):
                Bittrex issued API secret.
        """
        self.apikey = apikey
        self.secret = secret

    def public_markets(self):
        """
        Get the open and available trading markets along with other meta data.

        Returns:
            list
        """
        return self.get('public/getmarkets')

    def public_currencies(self):
        """
        Get all supported currencies along with other meta data.

        Returns:
            list
        """
        return self.get('public/getcurrencies')

    def public_ticker(self, market):
        """
        Get the current tick values for a market.

        Args:
            market (str):
                String literal (ie. BTC-LTC).

        Returns:
            list
        """
        return self.get('public/getticker', {
            'market': market
        })

    def public_market_summaries(self):
        """
        Get the last 24 hour summary of all active exchanges.

        Returns:
            list
        """
        return self.get('public/getmarketsummaries')

    def public_market_summary(self, market):
        """
        Get the last 24 hour summary of all active exchanges.

        Args:
            market (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.

        Returns:
            list
        """
        return self.get('public/getmarketsummary', {
            'market': market
        })

    def public_market_history(self, market):
        """
        Get the latest trades that have occured for a specific market.

        Args:
            market (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.

        Returns:
            list
        """
        return self.get('public/getmarkethistory', {
            'market': market
        })

    def public_order_book(self, market, book_type):
        """
        Get the orderbook for a given market.

        Args:
            market (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.
            book_type (str):
                Buy, sell or both to identify the type of orderbook.

        Returns:
            list
        """
        return self.get('public/getorderbook', {
            'market': market,
            'type': book_type
        })

    def market_buy_limit(self, market, quantity, rate):
        """
        Send a buy order in a specific market.

        Args:
            market (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.
            quantity (float):
                The amount to purchase.
            rate (float):
                Rate at which to place the order.

        Returns:
            list
        """
        return self.get('market/buylimit', {
            'market': market,
            'quantity': quantity,
            'rate': rate
        }, signed=True)

    def market_sell_limit(self, market, quantity, rate):
        """
        Send a sell order in a specific market.

        Args:
            market (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.
            quantity (float):
                The amount to sell.
            rate: (float)
                Rate at which to place the order.

        Returns:
            list
        """
        return self.get('market/selllimit', {
            'market': market,
            'quantity': quantity,
            'rate': rate
        }, signed=True)

    def market_cancel(self, uuid):
        """
        Send a cancel a buy or sell order.

        Args:
            uuid (str):
                UUID of buy or sell order.
        """
        return self.get('market/cancel', {
            'uuid': uuid
        }, signed=True)

    def market_open_orders(self, market):
        """
        Get all orders that you currently have opened.

        Args:
            market (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.

        Returns:
            list
        """
        return self.get('market/getopenorders', {
            'market': market
        }, signed=True)

    def account_balances(self):
        """
        Get all balances from your account.

        Returns:
            list
        """
        return self.get('account/getbalances', signed=True)

    def account_balance(self, currency):
        """
        Get the balance from your account for a specific currency.

        Args:
            currency (float):
                String literal (ie. BTC). If omitted, return all currency.

        Returns:
            list
        """
        return self.get('account/getbalance', {
            'currency': currency
        }, signed=True)

    def account_deposit_address(self, currency):
        """
        Get existing, or generate new address for a specific currency.

        Args:
            currency (float):
                String literal (ie. BTC). If omitted, return all currency.

        Returns:
            list
        """
        return self.get('account/getdepositaddress', {
            'currency': currency
        }, signed=True)

    def account_withdraw(self, currency, quantity, address, paymentid):
        """
        Send request to withdraw funds from your account.

        Args:
            currency (float):
                String literal (ie. BTC). If omitted, return all currency.
            quantity (str):
                The amount to withdrawl.
            address (str):
                The address where to send the funds.
            paymentid (str):
                CryptoNotes/BitShareX/Nxt field (memo/paymentid optional).

        Returns:
            list
        """
        return self.get('account/getwithdraw', {
            'currency': currency,
            'quantity': quantity,
            'address': address,
            'paymentid': paymentid
        }, signed=True)

    def account_order(self, uuid):
        """
        Get a single order by uuid.

        Args:
            uuid (str):
                UUID of buy or sell order.

        Return:
            list
        """
        return self.get('account/getorder', {
            'uuid': uuid
        }, signed=True)

    def account_order_history(self, market):
        """
        Get order history.

        Args:
            market (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.

        Returns:
            list
        """
        return self.get('account/getorderhistory', {
            'market': market
        }, signed=True)

    def account_deposit_history(self, currency):
        """
        Get deposit history.

        Args:
            currency (float):
                String literal (ie. BTC). If omitted, return all currency.

        Returns:
            list
        """
        return self.get('account/getdeposithistory', {
            'currency': currency
        }, signed=True)

    def account_withdrawl_history(self, currency):
        """
        Get withdrawl history.

        Args:
            currency (float):
                String literal (ie. BTC). If omitted, return all currency.

        Returns:
            list
        """
        return self.get('account/getwithdrawlhistory', {
            'currency': currency
        }, signed=True)

    def get(self, method, params=dict, headers=None, signed=False):
        """
        Construct and send a HTTP request to the Bittrex API.

        Args:
            method (str):
                URI resource that references an API service.
            params (dict):
                Dictionary that contains name/value parameters (optional).
            headers (dict):
                Dictionary that contains HTTP header key/values (optional).
            signed (bool):
                Authenticate using a signed header (optional).

        Returns:
            list
        """

        # Add parameters required for signed requests.
        if signed == True:
            params['apikey'] = self.apikey
            params['nonce'] = str(int(time.time()))

        # Create query string from parameter items.
        query_str = []
        for name, value in params.iteritems():
            query_str.append(name + '=' + str(value))

        # Format the URL with query string.
        uri = [BittrexApiRequest.BASE_URL + method]
        uri.append('?' + '&'.join(query_str))
        url = ''.join(uri)

        # Create the signed HTTP header.
        if headers is None:
            headers = {}

        if signed == True:
            headers['apisign'] = BittrexApiRequest._sign(self.secret, url)

        # Send the API request.
        req = requests.get(url, headers=headers)
        res = req.json()

        if res['success'] == False:
            print >> sys.stderr, "Bittex response: %s" % res['message']
            sys.exit(1)

        # Return list of dicts.
        return res['result']

    @staticmethod
    def _sign(secret, message):
        """
        Return signed message using the HMAC algorithm.

        Args:
            secret (str):
                Bittrex issued API secret.
            message (str):
                Message to convert.

        Returns:
            str

        .. seealso:: https://www.bittrex.com/Manage#sectionApi
        """
        return hmac.new(secret, message, hashlib.sha512).hexdigest()

#
# Start program.
#
if __name__ == '__main__':

    # Let's get this party started.
    BittrexAutoTrader(
        BittrexAutoTraderConfig.values()
    ).run()
