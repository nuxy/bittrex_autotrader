#!/usr/bin/env python3.6

"""
  bittrex_autotrader
  Bittrex currency exchange autotrading script in a nutshell.

  Copyright 2018-2020, Marc S. Brooks (https://mbrooks.info)
  Licensed under the MIT license:
  http://www.opensource.org/licenses/mit-license.php
"""

# Standard libraries.
import csv
import io
import time

# External modules.
import humanfriendly.prompts
import humanfriendly.tables
import humanfriendly.terminal
import humanfriendly.terminal.spinners
import numpy

# Package modules.
from .config  import values as BittrexAutoTraderConfig
from .request import BittrexAutoTraderRequest

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
        self.api_req = BittrexAutoTraderRequest(options['apikey'], options['secret'])
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
            prompt_choice = humanfriendly.prompts.prompt_for_choice(
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

                if order['status'] == 'OPEN':
                    BittrexAutoTrader._wait(
                        label='Order in progress. Waiting',
                        seconds=float(self.delay)
                    )
                    continue

                if order['status'] == 'CLOSED' and order['fillQuantity'] == '0.00000000':
                    next_trade = 'BUY' if next_trade == 'SELL' else 'SELL'

                    print('Order remotely cancelled.', "\n")

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
        print(f'Created new {trade_type} order.')

        # Get BUY/SELL orders market totals.
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
            stdout['rows'].append(['Bid', humanfriendly.prompts.ansi_wrap(
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
            stdout['rows'].append(['Ask', humanfriendly.prompts.ansi_wrap(
                format(trader_ask, '.8f'),
                bold=True
            )])

            self._submit(trade_type, trader_ask)

        stdout['rows'].append(['Qty', format(float(self.units), '.8f')])

        # Output human-friendly results.
        print(humanfriendly.tables.format_pretty_table(
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
                print(humanfriendly.terminal.ansi_wrap(
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
        with humanfriendly.terminal.spinners.AutomaticSpinner(label, show_time=timer):
            time.sleep(seconds)

#
# Start program.
#
if __name__ == '__main__':

    # Let's get this party started.
    BittrexAutoTrader(
        BittrexAutoTraderConfig()
    ).run()
