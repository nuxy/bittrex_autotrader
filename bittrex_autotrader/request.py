"""
  bittrex_autotrader
  Bittrex currency exchange autotrading script in a nutshell.

  Copyright 2018-2020, Marc S. Brooks (https://mbrooks.info)
  Licensed under the MIT license:
  http://www.opensource.org/licenses/mit-license.php
"""

# Standard libraries.
import hashlib
import hmac
import json
import sys
import time

# External modules.
import requests

class BittrexAutoTraderRequest:
    """
    Bittrex API request handler.
    """

    # Bittrex API URL
    BASE_URL = 'https://api.bittrex.com/v3'

    # Total retries on failed connection.
    CONNECT_RETRIES = 10

    # Delay between failed requests.
    CONNECT_WAIT = 5

    def __init__(self, apikey, secret):
        """
        Create a new instance of the Api

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
        url = BittrexAutoTraderRequest.BASE_URL + '/' + uri

        data = ''

        if method == 'GET':
            if values:
                url += BittrexAutoTraderRequest._create_query_str(values)
        else:
            data = json.dumps(values)

        req = None

        for _ in range(BittrexAutoTraderRequest.CONNECT_RETRIES):

            # Sign authentication requests.
            if auth is True:
                timestamp = str(round(time.time() * 1000))

                content_hash = BittrexAutoTraderRequest._hash_content(data)

                signature = BittrexAutoTraderRequest._sign_request(
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
                time.sleep(BittrexAutoTraderRequest.CONNECT_WAIT)
            else:
                break

        res = req.json()

        if res is None:
            print('Script failure: Connection timeout', file=sys.stderr)

            sys.exit(1)

        if req.ok is False:
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
