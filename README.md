# Bittrex AutoTrader

Bittrex currency exchange autotrading script _in a nutshell_.

## Dependencies

To install the Python script dependencies and generate API documentation:

    $ make

## Basic Usage

    $ ./bittrex_autotrader.py --conf bittrex_autotrader.conf

## Configuration options

The following options can be passed as script arguments or defined in a file:

| Option | Description                             | Example                          | Default value |
| -------| ----------------------------------------|----------------------------------|---------------|
| apikey | Bittrex issued API key.                 | XxXxxXXxXxxXxxXxXxxXxXxxXXxXxxXx |               |
| secret | Bittrex issued API secret.              | XxXxxXXxXxxXxxXxXxxXxXxxXXxXxxXx |               |
| market | String literal for the market.          | BTC-XXX                          | BTC-LTC       |
| units  | BUY/SELL total units.                   | 0                                | 1             |
| spread | BUY/SELL markup/markdown percentage.    | 0.0/0.0                          | 0.1/0.1       |
| method | Moving Average calculation method.      | method                           | arithmetic    |
| delay  | Seconds to delay order status requests. | 0                                | 30            |

## Bittrex API

Outside of the basic trading functionality a full implementation of the Bittrex API has been provided for those would want to extend this script.  Runnning `make` will generate the class HTML documentation.

### Usage Example

    #!/usr/bin/env python

    from bittrex_autotrader import BittrexApiRequest

    apiReq = BittrexApiRequest(apikey, secret)
    ticker = apiReq.public_ticker(market)

    print ticker['Ask']

## Developer Notes

* If you are new to cryptocurrencies please, and I stress, **do NOT use this script**. :skull: You have been warned. :skull:
* Certain markets are more volatile than others. It's very easy to get priced out of a market, so choose wisely.
* Based on the defined `spread` you can gain/lose units of value.  I take no responsiblity for your losses.
* New features will be added when I have free time available.  You can motivate me by _donating_ below.

## Donations

If this script makes you ~~money~~ happy then buy me a :beer: using one of the crypto-currencies below:

    Bitcoin:  1Cvr9aHNmV2riULkfgEqofQtuhxCBe7A16
    Litecoin: LcMKbewQftytYnmsGTk63BW7yPCnUKFNni

## License and Warranty

This package is distributed in the hope that it will be useful, but without any warranty; without even the implied warranty of merchantability or fitness for a particular purpose.

_Bittrex AutoTrader_ is provided under the terms of the [MIT license](http://www.opensource.org/licenses/mit-license.php)

[Bittrex](https://bittrex.com) is a registered trademark of Bittrex, INC

## Author

[Marc S. Brooks](https://github.com/nuxy)
