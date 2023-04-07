# Bittrex AutoTrader

Bittrex currency exchange autotrading script *in a nutshell*.

## Installation

    $ pip3 install bittrex_autotrader

## Dependencies

This package requires Python (3.6 or greater) to work.

To manually install the Python script dependencies, generate API documentation, and create a source distribution:

    $ make
    $ make lint
    $ make docs
    $ make dist

## Configuration options

The following options can be passed as script arguments or defined in a file:

| Option | Description                   | Example       | Default value       |
|--------|-------------------------------|---------------|---------------------|
| apikey | Bittrex issued API key.       | XxXxxXXxXxx.. |                     |
| secret | Bittrex issued API secret.    | XxXxxXXxXxx.. |                     |
| market | String literal for the        | BTC-XXX       | BTC-LTC market.     |
| units  | BUY/SELL total units.         | 0             | 1                   |
| spread | BUY/SELL markup/markdown      | 0.0/0.0       | 0.1/0.1 percentage. |
| method | Moving Average calculation    | method        | arithmetic method.  |
| delay  | Seconds to delay order status | 0             | 30 requests.        |
| prompt | Require user interaction to   | False         | True begin trading. |

## Basic usage

To run the script:

    $ bittrex_autotrader --conf bittrex_autotrader.conf

Assuming there are no open orders, the default configuration requires the user to decide the first type of trade;

    1. BUY in at markdown (need units to trade)
    2. SELL out at markup (need liquidity)

    Enter your choice as a number or unique substring (Control-C aborts):

Make a choice then press Enter.

The script will then retrieve the latest market rates, calculate an asking price based on your configuration and submit an order to Bittrex.

Once an order has completed, the script will again retrieve the latest market rates and submit a new order of the opposite type.

If an order is cancelled (via the Bittrex Web UI), the script will recalculate based on the latest market rates and submit an order of the same type.

If the script is stopped and re-run while an order is outstanding, it will resume monitoring and continue as normal once the order is completed or cancelled.

### Running as a service

If you wish to automate the running of the script (using [Supervisor](http://supervisord.org) for example), set the 'prompt' configuration option to 'False'.

On startup, the script will automatically check for an open order and wait for completion or cancellation before initiating an order of the opposite type.

If you do not have any open orders it will initiate a 'SELL' order by default. If you do not have enough funds to carry out this operation, the script will end.

## Bittrex API (v3)

Outside of the basic trading functionality a partial implementation of the Bittrex API has been provided for those would want to extend this script.

### Usage Example

    #!/usr/bin/env python3.6

    from bittrex_autotrader.request import BittrexApiRequest

    api_req = BittrexApiRequest(api_key, secret)
    ticker  = api_req.public_ticker(market)

    print ticker['askRate']

## Developer Notes

- If you are new to cryptocurrencies please, and I stress, **DO NOT USE THIS SCRIPT**.
- Certain markets are more volatile than others. It's very easy to get priced out of a market, so choose wisely.
- Based on the defined `spread` you can gain/lose units of value. _I take no responsiblity for your losses.

## License and Warranty

This package is distributed in the hope that it will be useful, but without any warranty; without even the implied warranty of merchantability or fitness for a particular purpose.

*Bittrex AutoTrader* is provided under the terms of the [MIT license](http://www.opensource.org/licenses/mit-license.php)

[Bittrex](https://bittrex.com) is a registered trademark of Bittrex, INC

## Author

[Marc S. Brooks](https://github.com/nuxy)
