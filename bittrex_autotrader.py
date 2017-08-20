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

BASE_URL = 'https://bittrex.com/api/v1.1/'

def main():
    """
    Process command-line arguments and start trading.
    """
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-c', '--config', metavar='FILE')

    args, remaining_args = arg_parser.parse_known_args()

    if args.config:
        config_parser = ConfigParser.SafeConfigParser()
        config_parser.read([args.config])

        config = dict(config_parser.items('config'))
    else:
        arg_parser.add_argument('-k', '--apikey', required=True)
        arg_parser.add_argument('-s', '--secret', required=True)
        arg_parser.add_argument('-m', '--market', required=True)
        arg_parser.add_argument('-p', '--spread')

        config = vars(arg_parser.parse_args(remaining_args))

    # Let's get this party started.
    BittrexAutoTrader(
        config['apikey'],
        config['secret'],
        config['market'],
        config['spread']
    )

#
# Bittrex API autotrader object.
#
class BittrexAutoTrader(object):
    """
    Bittrex API autotrader object.
    """

    def __init__(self, apikey, secret, market, spread):
        """
        Create a new instance of BittrexAutoTrader

        Args:
            apikey (str):
                Bittrex issued API key.
            secret (str):
                Bittrex issued API secret.
            market (str):
                String literal for the market (ie. BTC-LTC).
            spread (float):
                BUY/SELL rolling average spread value.

        Attributes:
            apiReq (BittrexApiRequest):
                Instance of BittrexApiRequest object.
            market (str):
                String literal for the market (ie. BTC-LTC).
            spread (float):
                BUY/SELL rolling average spread value.
        """
        self.apiReq = BittrexApiRequest(apikey, secret)
        self.market = market
        self.spread = spread
        self._units = 2000  # TODO: 50k Satoshi minimum.
        self.init()

    def init(self):
        """
        Initialize automatic trading (BUY/SELL <> LOW/HIGH).
        """
        active = {}

        # Check for active trades.
        while True:
            open_orders = self.apiReq.market_open_orders(self.market)

            # If no open orders exist..
            if open_orders:
                for order in open_orders:
                    if order['OrderUuid'] == active['uuid']:
                        break
            else:

                # Submit a new trade.
                active = self.submit_order(
                    'BUY' if active and 'SELL' in active['uuid'] else 'SELL'
                )

            BittrexAutoTrader._wait(seconds=30)

    def submit_order(self, trade_type='SELL'):
        """
        Submit an order to Bittrex market; wait until fulfilled.

        Args:
            trade_type (str):
                BUY or SELL (default BUY).

        Returns:
            dict
        """
        currency = self.market.replace('BTC-', '')

        # Get BUY/SELL order market totals.
        market_history = self.apiReq.public_market_history(self.market)

        price_history = BittrexAutoTrader._numpy_loadtxt(
            BittrexAutoTrader._list_of_dict_filter_by(
                market_history, 'OrderType', trade_type
            ),
            ['Price']
        )
        market_avg = round(price_history.mean(), 8)
        market_max = round(price_history.max(), 8)

        # Get account balance.
        available = (self.apiReq.account_balance(currency))['Available']

        # Get ASK/BID orders.
        ticker = self.apiReq.public_ticker(self.market)

        stdout = {
            'cols': [trade_type, currency],
            'rows': []
        }

        # Perform trade operations.
        order = {}

        if trade_type == 'BUY':
            ticker_bid = float(ticker['Bid'])
            trader_bid = round(
                ticker_bid - (ticker_bid * float(self.spread)), 8
            )

            stdout['rows'].append(['Avg', format(market_avg, '.8f')])
            stdout['rows'].append(['Max', format(market_max, '.8f')])
            stdout['rows'].append(['Ask', format(ticker_bid, '.8f')])
            stdout['rows'].append(['Bid', format(trader_bid, '.8f')])

            order = self.apiReq.market_buy_limit(
                self.market, self._units, trader_bid
            )
        else:
            ticker_ask = float(ticker['Ask'])
            trader_ask = round(
                ticker_ask + (ticker_ask * float(self.spread)), 8
            )

            stdout['rows'].append(['Avg', format(market_avg, '.8f')])
            stdout['rows'].append(['Max', format(market_max, '.8f')])
            stdout['rows'].append(['Bid', format(ticker_ask, '.8f')])
            stdout['rows'].append(['Ask', format(trader_ask, '.8f')])

            order = self.apiReq.market_sell_limit(
                self.market, self._units, trader_ask
            )

        # Output results.
        print humanfriendly.tables.format_pretty_table(
            stdout['rows'],
            stdout['cols']
        ), "\n"

        return order

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

        @statucfunction
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
                The label for the spinner.
            seconds (int):
                Seconds to delay execution.
            timer (bool):
                Show the elapsed time.
        """
        with humanfriendly.AutomaticSpinner(label, show_time=timer) as spinner:
            time.sleep(seconds)

#
# Bittrex API request object.
#
class BittrexApiRequest(object):
    """
    Bittrex API request object.
    """

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
        uri = [BASE_URL + method]
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
    main()
