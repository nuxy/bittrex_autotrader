#!/usr/bin/env python3.6

"""
  bittrex_autotrader.py
  Bittrex currency exchange autotrading script in a nutshell.

  Copyright 2018-2020, Marc S. Brooks (https://mbrooks.info)
  Licensed under the MIT license:
  http://www.opensource.org/licenses/mit-license.php

  Dependencies:
    humanfriendly
    numpy
    requests

  Notes:
   - This script has been tested to work with Unix-like operating systems
   - This script can be run via cronjob

  .. seealso:: https://bittrex.github.io/api/v3
"""

import argparse
import configparser
import csv
import hashlib
import hmac
import io
import json
import sys
import time
import humanfriendly
import numpy
import pkg_resources
import requests

#
# Bittrex API autotrader.
#
class BittrexAutoTrader:
    """
    Bittrex API autotrader.

    Dependencies:
        humanfriendly
        numpy
    """

    # Percent Bittrex charges for BUY/SELL trades.
    TRADE_FEES = .0025

    def __init__(self, options):
        """
        Create a new instance of BittrexAutoTrader

        Args:
            options (dict):
                Dictionary of options.

        Attributes:
            api_req (BittrexApiRequest):
                Instance of BittrexApiRequest.
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
            prompt (bool):
                Require user interaction to begin trading.
        """
        self.api_req = BittrexApiRequest(options['apikey'], options['secret'])
        self.market  = options['market']
        self.units   = options['units']
        self.spread  = options['spread'].split('/')
        self.method  = options['method']
        self.delay   = options['delay']
        self.prompt  = options['prompt']

        # List of orders as dictionary items.
        self._orders = []

    def run(self):
        """
        Get open orders, prompt if necessary / determine next trade type and start trading.
        """
        self._orders = self.api_req.market_open_orders(self.market)

        if not self._orders and self.prompt == 'True':
            prompt_choice = humanfriendly.prompt_for_choice(
                [
                    'BUY in at markdown (need units to trade)',
                    'SELL out at markup (need liquidity)'
                ],
                default='SELL'
            )

            next_trade = prompt_choice.split(' ', 1)[0]
        else:
            next_trade = 'SELL'

            if self._orders and self.last_order()['type'] == 'LIMIT_SELL':
                next_trade = 'BUY'

        while True:

            # Check for open orders.
            if self._orders:
                order = self.api_req.account_order(
                    self.last_order()['id']
                )

                if order['status']:
                    BittrexAutoTrader._wait(seconds=float(self.delay))
                    continue

                # Allow user to cancel order remotely, recalculate and resubmit
                if order['closed']:
                    next_trade = 'BUY' if next_trade == 'SELL' else 'SELL'

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
        market_totals = self.market_totals(trade_type)

        market_max = round(market_totals.max(), 8)

        # Calculate Moving Average (TODO: weighted average).
        if self.method == 'weighted':
            moving_avg = round(market_totals.average(weights=None), 8)
        else:
            moving_avg = round(market_totals.mean(), 8)

        # Get current ASK/BID orders.
        ticker = self.api_req.public_ticker(self.market)

        # Format human-friendly results.
        stdout = {
            'cols': [trade_type, self.market.replace('BTC-', '')],
            'rows': []
        }

        # Perform trade operation.
        if trade_type == 'BUY':

            # Reinvest earnings.
            self._reinvest(float(ticker['lastTradeRate']))

            # Calculate markdown.
            markdown = BittrexAutoTrader._calc_decimal_percent(self.spread[1])

            # Submit limit BUY
            ticker_bid = float(ticker['bidRate'])
            trader_bid = round(
                (ticker_bid - (ticker_bid * markdown)), 8
            )

            stdout['rows'].append(['Avg', format(moving_avg, '.8f')])
            stdout['rows'].append(['Max', format(market_max, '.8f')])
            stdout['rows'].append(['Ask', format(ticker_bid, '.8f')])
            stdout['rows'].append(['Bid', humanfriendly.ansi_wrap(
                format(trader_bid, '.8f'),
                bold=True
            )])

            self._submit(trade_type, trader_bid)
        else:

            # Calculate markup.
            markup = BittrexAutoTrader._calc_decimal_percent(self.spread[0])

            # Submit limit SELL
            ticker_ask = float(ticker['askRate'])
            trader_ask = round(
                (ticker_ask + (ticker_ask * markup)), 8
            )

            stdout['rows'].append(['Avg', format(moving_avg, '.8f')])
            stdout['rows'].append(['Max', format(market_max, '.8f')])
            stdout['rows'].append(['Bid', format(ticker_ask, '.8f')])
            stdout['rows'].append(['Ask', humanfriendly.ansi_wrap(
                format(trader_ask, '.8f'),
                bold=True
            )])

            self._submit(trade_type, trader_ask)

        stdout['rows'].append(['Qty', format(float(self.units), '.8f')])

        # Output human-friendly results.
        print(humanfriendly.format_table(
            stdout['rows'],
            stdout['cols']
        ), "\n", time.strftime(' %Y-%m-%d %H:%M:%S '), "\n")

    def market_totals(self, trade_type='BUY'):
        """
        Returns BUY/SELL order market totals as ndarray.

        Args:
            trade_type (str):
                BUY or SELL (default: BUY).

        Returns:
            ndarray
        """
        market_history = self.api_req.public_market_history(self.market)

        return BittrexAutoTrader._numpy_loadtxt(
            BittrexAutoTrader._list_of_dict_filter_by(
                market_history, 'takerSide', trade_type
            ),
            ['rate']
        )

    def last_order(self, trade_type=None):
        """
        Return the last successful order by type.

        Args:
            trade_type (str):
                BUY or SELL (optional).

        Returns:
            dict
        """
        for order in reversed(self._orders):
            if not trade_type or trade_type in order['type']:
                return order

        return None

    def last_buy_price(self):
        """
        Return the last successful BUY price.

        Returns:
            float (default: 0)
        """
        order = self.last_order('BUY')

        return float(order['price']) if order else 0

    def last_sell_price(self):
        """
        Return the last successfull SELL price.

        Returns:
            float (default: 0)
        """
        order = self.last_order('SELL')

        return float(order['price']) if order else 0

    def _reinvest(self, last_price):
        """
        Update units to purchase based on total earnings available.

        Args:
            last_price (float):
                Latest market SELL price.
        """
        quantity = float(self.units)

        sell_price = self.last_sell_price()
        buy_price = self.last_buy_price()

        if sell_price and buy_price:
            earnings = (sell_price - buy_price) * quantity
            if earnings > 0:
                processed = quantity * sell_price
                available = (processed - \
                    (processed * BittrexAutoTrader.TRADE_FEES)) + earnings

                # Output human-friendly results.
                print(humanfriendly.ansi_wrap(
                    ''.join(['Total earnings: ', str(earnings)]),
                    bold=True
                ), "\n")

                # Check balance can cover purchase.
                quantity = available / last_price
                if (quantity * last_price) <= available:
                    self.units = quantity

    def _submit(self, trade_type, price):
        """
        Submit the API request and store order details.

        Args:
            trade_type (str):
                BUY or SELL (default: SELL).
        """
        if trade_type == 'BUY':
            uuid = self.api_req.market_buy_limit(
                self.market, self.units, price
            )['id']
        else:
            uuid = self.api_req.market_sell_limit(
                self.market, self.units, price
            )['id']

        self._orders.append({
            'id': uuid,
            'type': trade_type,
            'price': price,
            'quantity': self.units
        })

    @staticmethod
    def _calc_decimal_percent(num):
        """
        Returns string percentage as a decimal percent.

        Args:
            num (str):
                Percentage as string.

        Returns:
            float
        """
        num = float(num)

        return num if num < 1 else num / 100

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
        output = io.StringIO()

        # Filter items by key names.
        writer = csv.DictWriter(output, fieldnames=keys)
        for item in data:
            filtered_item = dict(
                (key, value) for key, value in item.items() if key in keys
            )
            writer.writerow(filtered_item)

        return output.getvalue()

    @staticmethod
    def _numpy_calc_sma(arr, num):
        """
        Return Simple Moving Average for a given data sequence.

        Args:
            arr (list):
                One-dimensional input array.
            num (int):
                Number of days (n-day).

        Returns:
            list
        """
        return numpy.convolve(arr, numpy.ones((num,)) / num, mode='valid')

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
            io.StringIO(
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
        with humanfriendly.AutomaticSpinner(label, show_time=timer):
            time.sleep(seconds)

#
# Bittrex AutoTrader config.
#
class BittrexAutoTraderConfig:
    """
    Bittrex AutoTrader config.
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

#
# Bittrex API request.
#
class BittrexApiRequest:
    """
    Bittrex API request.

    Dependencies:
        requests
    """

    # Bittrex API URL
    BASE_URL = 'https://api.bittrex.com/v3'

    # Total retries on failed connection.
    CONNECT_RETRIES = 10

    # Delay between failed requests.
    CONNECT_WAIT = 5

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

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Market
        """
        return self.get('markets')

    def public_currencies(self):
        """
        Get all supported currencies along with other meta data.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Currency
        """
        return self.get('currencies')

    def public_ticker(self, market_symbol):
        """
        Get the current tick values for a market.

        Args:
            market_symbol (str):
                String literal (ie. BTC-LTC).

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Ticker
        """
        return self.get(f'markets/{market_symbol}/ticker')

    def public_market_summaries(self):
        """
        Get the last 24 hour summary of all active exchanges.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/MarketSummary
        """
        return self.get('markets/summaries')

    def public_market_summary(self, market_symbol):
        """
        Get the last 24 hour summary of all active exchanges.

        Args:
            market_symbol (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/MarketSummary
        """
        return self.get(f'markets/{market_symbol}/summary')

    def public_market_history(self, market_symbol):
        """
        Get the latest trades that have occured for a specific market.

        Args:
            market_symbol (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Trade
        """
        return self.get(f'markets/{market_symbol}/trades')

    def public_order_book(self, market_symbol, depth=25):
        """
        Get the orderbook for a given market.

        Args:
            market_symbol (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.
            depth (int):
                Maximum depth to return (allowed values are [1, 25, 500])

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/OrderBook
        """
        return self.get(f'markets/{market_symbol}/orderbook', {
            'depth': depth
        })

    def market_buy_limit(self, market_symbol, quantity, rate, time_in_force='GOOD_TIL_CANCELLED'):
        """
        Send a buy order in a specific market.

        Args:
            market_symbol (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.
            quantity (float):
                The amount to purchase.
            rate (float):
                Rate at which to place the order.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Order
        """
        return self.post('orders', {
            'marketSymbol': market_symbol,
            'direction': 'BUY',
            'type': 'LIMIT',
            'quantity': quantity,
            'limit': rate,
            'timeInForce': time_in_force
        }, auth=True)

    def market_sell_limit(self, market_symbol, quantity, rate, time_in_force='GOOD_TIL_CANCELLED'):
        """
        Send a sell order in a specific market.

        Args:
            market_symbol (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.
            quantity (float):
                The amount to sell.
            rate: (float)
                Rate at which to place the order.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Order
        """
        return self.post('orders', {
            'marketSymbol': market_symbol,
            'direction': 'SELL',
            'type': 'LIMIT',
            'quantity': quantity,
            'limit': rate,
            'timeInForce': time_in_force
        }, auth=True)

    def market_cancel(self, orderid):
        """
        Send a cancel a buy or sell order.

        Args:
            orderid (str):
                ID of buy or sell order.

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Order
        """
        return self.delete(f'orders/{orderid}', auth=True)

    def market_open_orders(self, market_symbol):
        """
        Get all orders that you currently have opened.

        Args:
            market_symbol (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Order
        """
        return self.get('orders/open', {
            'marketSymbol': market_symbol
        }, auth=True)

    def account_balances(self):
        """
        Get all balances from your account.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Balance
        """
        return self.get('balances', auth=True)

    def account_balance(self, currency_symbol):
        """
        Get the balance from your account for a specific currency.

        Args:
            currency_symbol (str):
                String literal (ie. BTC). If omitted, return all currency.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Balance
        """
        return self.get(f'balances/{currency_symbol}', auth=True)

    def account_deposit_address(self, currency_symbol):
        """
        Get existing, or generate new address for a specific currency.

        Args:
            currency_symbol (str):
                String literal (ie. BTC). If omitted, return all currency.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Address
        """
        return self.get(f'addresses/{currency_symbol}', auth=True)

    def account_withdraw(self, currency_symbol, quantity, crypto_address, paymentid):
        """
        Send request to withdraw funds from your account.

        Args:
            currency_symbol (str):
                String literal (ie. BTC). If omitted, return all currency.
            quantity (str):
                The amount to withdrawl.
            crypto_address (str):
                The address where to send the funds.
            paymentid (str):
                CryptoNotes/BitShareX/Nxt field (memo/paymentid optional).

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Withdrawal
        """
        return self.post('withdrawals', {
            'currencySymbol': currency_symbol,
            'quantity': quantity,
            'cryptoAddress': crypto_address,
            'cryptoAddressTag': paymentid
        }, auth=True)

    def account_order(self, orderid):
        """
        Get a single order by ID.

        Args:
            orderid (str):
                ID of buy or sell order.

        Return:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Order
        """
        return self.get(f'orders/{orderid}', auth=True)

    def account_order_history(self, market_symbol):
        """
        Get order history.

        Args:
            market_symbol (str):
                String literal (ie. BTC-LTC). If omitted, return all markets.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Order
        """
        return self.get('orders/closed', {
            'marketSymbol': market_symbol
        }, auth=True)

    def account_deposit_history(self, currency_symbol):
        """
        Get deposit history.

        Args:
            currency_symbol (str):
                String literal (ie. BTC). If omitted, return all currency.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Withdrawal
        """
        return self.get('deposits/closed', {
            'currencySymbol': currency_symbol
        }, auth=True)

    def account_withdrawl_history(self, currency_symbol):
        """
        Get withdrawl history.

        Args:
            currency_symbol (str):
                String literal (ie. BTC). If omitted, return all currency.

        Returns:
            list

        .. seealso:: https://bittrex.github.io/api/v3#/definitions/Withdrawal
        """
        return self.get('withdrawals/closed', {
            'currencySymbol': currency_symbol
        }, auth=True)

    def get(self, uri, params=None, headers=None, auth=False):
        """
        Construct and send a HTTP GET request to the Bittrex API.

        Args:
            uri (str):
                URI that references an API service.
            params (dict):
                Dictionary that contains HTTP request name/value parameters (optional).
            headers (dict):
                Dictionary that contains HTTP request header key/values (optional).
            auth (bool):
                Authenticate with a signed request (default: False).

        Returns:
            list
        """
        return self.send_request('GET', uri, params, headers, auth)

    def post(self, uri, body=None, headers=None, auth=False):
        """
        Construct and send a HTTP POST request to the Bittrex API.

        Args:
            uri (str):
                URI that references an API service.
            body (dict):
                Dictionary that contains HTTP request body key/values (optional).
            headers (dict):
                Dictionary that contains HTTP request header key/values (optional).
            auth (bool):
                Authenticate with a signed request (default: False).

        Returns:
            list
        """
        return self.send_request('POST', uri, body, headers, auth)

    def delete(self, uri, body=None, headers=None, auth=False):
        """
        Construct and send a HTTP DELETE request to the Bittrex API.

        Args:
            uri (str):
                URI that references an API service.
            body (dict):
                Dictionary that contains HTTP request body key/values (optional).
            headers (dict):
                Dictionary that contains HTTP request header key/values (optional).
            auth (bool):
                Authenticate with a signed request (default: False).

        Returns:
            list
        """
        return self.send_request('DELETE', uri, body, headers, auth)

    def send_request(self, method, uri, values=None, headers=None, auth=False):
        """
        Construct and send a HTTP request to the Bittrex API.

        Args:
            method (str):
                HTTP request method (e.g. GET, POST, DELETE).
            uri (str):
                URI that references an API service.
            values (dict):
                Dictionary that contains request values (optional).
            headers (dict):
                Dictionary that contains HTTP header key/values (optional).
            auth (bool):
                Authenticate with a signed request (default: False).

        Returns:
            list
        """
        url = BittrexApiRequest.BASE_URL + '/' + uri

        data = ''

        if method == 'GET':
            if values:
                url += BittrexApiRequest._create_query_str(values)
        else:
            data = json.dumps(values)

        req = None

        for _ in range(BittrexApiRequest.CONNECT_RETRIES):

            # Sign authentication requests.
            if auth is True:
                timestamp = str(round(time.time() * 1000))

                content_hash = BittrexApiRequest._hash_content(data)

                signature = BittrexApiRequest._sign_request(
                    self.secret, method, url, timestamp, content_hash
                )

                if headers is None:
                    headers = {}

                headers['Api-Key']          = self.apikey
                headers['Api-Timestamp']    = timestamp
                headers['Api-Signature']    = signature
                headers['Api-Content-Hash'] = content_hash

            try:
                if method == 'GET':
                    req = requests.get(url, headers=headers)
                else:
                    req = requests.request(
                        method, url, json=values, headers=headers
                    )

            except requests.exceptions.ConnectionError:
                time.sleep(BittrexApiRequest.CONNECT_WAIT)
            else:
                break

        res = req.json()

        if res is None:
            print('Script failure: Connection timeout', file=sys.stderr)

            sys.exit(1)

        if req.status_code != 200:
            print("Bittex response: %s" % res['code'], file=sys.stderr)

            sys.exit(1)

        # Return list of dicts.
        return res

    @staticmethod
    def _create_query_str(data):
        """
        Returns a query string of name/value pairs.

        Args:
            data (dict):
                Dictionary that contains request data.

        Returns:
            str
        """
        params = []
        for name, value in data.items():
            params.append(name + '=' + str(value))

        return '?' + '&'.join(params)

    @staticmethod
    def _hash_content(data):
        """
        Returns hex-encoded SHA-512 hash for the given data.

        Args:
            data (dict):
                Dictionary that contains request data.

        Returns:
            str
        """
        return hashlib.sha512(str(data).encode('utf-8')).hexdigest()

    @staticmethod
    def _sign_request(secret, method, url, timestamp, content_hash=None):
        """
        Returns signed request using the HMAC SHA-512 algorithm.

        Args:
            secret (str):
                Bittrex issued API secret.
            method (str):
                HTTP request method (e.g. GET, POST, DELETE).
            url (str):
                Request URL (including query string).
            timestamp (str):
                Epoch timestamp in milliseconds.
            content_hash (str):
                Hex-encoded SHA-512 hash of the request body (optional).

        Returns:
            str
        """
        message = f'{timestamp}{url}{method}{content_hash}'

        return hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha512).hexdigest()

#
# Start program.
#
if __name__ == '__main__':

    # Let's get this party started.
    BittrexAutoTrader(
        BittrexAutoTraderConfig.values()
    ).run()
