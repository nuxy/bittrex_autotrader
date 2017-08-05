#!/usr/bin/env python

"""
  bittrex_autotrader.py
  Bittrex currency exchange autotrading script in a nutshell.

  Copyright 2017, Marc S. Brooks (https://mbrooks.info)
  Licensed under the MIT license:
  http://www.opensource.org/licenses/mit-license.php

  .. note::
   - This script has been tested to work with Unix-like operating systems
   - This script can be run via cronjob

  .. seealso:: https://bittrex.com/Home/Api
"""

import argparse
import hashlib
import hmac
import requests
import sys
import time

BASE_URL = 'https://bittrex.com/api/v1.1/'

def main():
    """
    Process command-line arguments and initialize trading routines.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', required=True)
    parser.add_argument('-s', '--secret', required=True)

    global args
    args = parser.parse_args()

    print 'Just what do you think you are doing, Dave?'
    sys.exit()

def sign(secret, message):
    """
    Sign the message using the HMAC algorithm.

    :param secret: Bittrex issued API secret.
    :param message: Message to convert.

    :return: string

    .. seealso:: https://www.bittrex.com/Manage#sectionApi
    """
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

def request(method, params=None, headers=None, signed=False):
    """
    Construct a HTTP request and send to the Bittrex API.

    :param method: URI resource that references an API service.
    :param params: Object that contains key/value parameters (optional).
    :param signed: Authenticate using a signed header (optional).

    :return: dict
    """
    url = [BASE_URL + method]

    # Add parameters required for signed requests.
    if params is None:
        params = {}

    if signed == True:
        params['apikey'] = args.key
        params['nonce'] = str(int(time.time()))

    # Create URL query string from parameter items.
    query_str = []
    for name, value in params.iteritems():
        query_str.append(name + '=' + value)

    url.append('?' + '&'.join(query_str))

    # Create the signed HTTP header.
    if headers is None:
        headers = {}

    if signed == True:
        headers['apisign'] = sign(args.secret, ''.join(url))

    # Send the API request.
    req = requests.get(''.join(url), headers=headers)
    res = req.json()

    if res['success'] == False:
        print >> sys.stderr, "Bittex response: %s" % res['message']
        sys.exit(1)

    # Return dict on success.
    return res

def public_markets():
    """
    Get the open and available trading markets along with other meta data.

    :return: dict
    """
    return request('public/getmarkets')

def public_currencies():
    """
    Get all supported currencies along with other meta data.

    :return: dict
    """
    return request('public/getcurrencies')

def public_ticker():
    """
    Get the current tick values for a market.

    :return: dict
    """
    return request('public/getticker')

def public_market_summaries():
    """
    Get the last 24 hour summary of all active exchanges.

    :return: dict
    """
    return request('public/getmarketsummaries')

def public_market_summary(market):
    """
    Get the last 24 hour summary of all active exchanges.

    :param market: String literal (ie. BTC-LTC). If omitted, return all markets.

    :return: dict
    """
    return request('public/getmarketsummary', {
        'market': market
    })

def public_market_history(market):
    """
    Get the latest trades that have occured for a specific market.

    :param market: String literal (ie. BTC-LTC). If omitted, return all markets.

    :return: dict
    """
    return request('public/getmarkethistory', {
        'market': market
    })

def public_order_book(market, book_type):
    """
    Get the orderbook for a given market.

    :param market: String literal (ie. BTC-LTC). If omitted, return all markets.
    :param book_type: buy, sell or both to identify the type of orderbook.

    :return: dict
    """
    return request('public/getorderbook', {
        'market': market,
        'type': book_type
    })

def market_buy_limit(market, quantity, rate):
    """
    Send a buy order in a specific market.

    :param market: String literal (ie. BTC-LTC). If omitted, return all markets.
    :param quantity: The amount to purchase.
    :param rate: Rate at which to place the order.

    :return: dict
    """
    return request('market/buylimit', {
        'market': market,
        'quantity': quantity,
        'rate': rate
    }, signed=True)

def market_sell_limit(market, quantity, rate):
    """
    Send a sell order in a specific market.

    :param market: String literal (ie. BTC-LTC). If omitted, return all markets.
    :param quantity: The amount to sell.
    :param rate: Rate at which to place the order.

    :return: dict
    """
    return request('market/selllimit', {
        'market': market,
        'quantity': quantity,
        'rate': rate
    }, signed=True)

def market_cancel(uuid):
    """
    Send a cancel a buy or sell order.

    :param uuid: UUID of buy or sell order.
    """
    return request('market/cancel', {
        'uuid': uuid
    }, signed=True)

def market_open_orders(market):
    """
    Get all orders that you currently have opened.

    :param market: String literal (ie. BTC-LTC). If omitted, return all markets.

    :return: dict
    """
    return request('market/getopenorders', {
        'market': market
    }, signed=True)

def account_balances():
    """
    Get all balances from your account.

    :return: dict
    """
    return request('account/getbalances', signed=True)

def account_balance(currency):
    """
    Get the balance from your account for a specific currency.

    :param currency: String literal (ie. BTC). If omitted, return all currency.

    :return: dict
    """
    return request('account/getbalance', {
        'currency': currency
    }, signed=True)

def account_deposit_address(currency):
    """
    Get existing, or generate new address for a specific currency.

    :param currency: String literal (ie. BTC). If omitted, return all currency.

    :return: dict
    """
    return request('account/getdepositaddress', {
        'currency': currency
    }, signed=True)

def account_withdraw(currency, quantity, address, paymentid):
    """
    Send request to withdraw funds from your account.

    :param currency: String literal (ie. BTC). If omitted, return all currency.
    :param quantity: The amount to withdrawl.
    :param address: The address where to send the funds.
    :param paymentid: CryptoNotes/BitShareX/Nxt field (memo/paymentid optional).

    :return: dict
    """
    return request('account/getwithdraw', {
        'currency': currency,
        'quantity': quantity,
        'address': address,
        'paymentid': paymentid
    }, signed=True)

def account_order(uuid):
    """
    Get a single order by uuid.

    :param uuid: UUID of buy or sell order.

    :return: dict
    """
    return request('account/getorder', {
        'uuid': uuid
    }, signed=True)

def account_order_history(market):
    """
    Get order history.

    :param market: String literal (ie. BTC-LTC). If omitted, return all markets.

    :return: dict
    """
    return request('account/getorderhistory', {
        'market': market
    }, signed=True)

def account_deposit_history(currency):
    """
    Get deposit history.

    :param currency: String literal (ie. BTC). If omitted, return all currency.

    :return: dict
    """
    return request('account/getdeposithistory', {
        'currency': currency
    }, signed=True)

def account_withdrawl_history(currency):
    """
    Get withdrawl history.

    :param currency: String literal (ie. BTC). If omitted, return all currency.

    :return: dict
    """
    return request('account/getwithdrawlhistory', {
        'currency': currency
    }, signed=True)

if __name__ == '__main__':
    main()
