# bittrex_autotrader

Bittrex currency exchange autotrading script _in a nutshell_.

:skull: This is **currently in development**. You have been warned :skull:

## Dependencies

To install the Python script dependencies:

    $ make

## Basic Usage

    $ ./bittrex_autotrader.py --conf bittrex_autotrader.conf

## Configuration options

The following options can be passed as script arguments or defined in a file:

| Option | Description                          | Format                           | Default value |
| -------| -------------------------------------|----------------------------------|---------------|
| apikey | Bittrex issued API key.              | XxXxxXXxXxxXxxXxXxxXxXxxXXxXxxXx |               |
| secret | Bittrex issued API secret.           | XxXxxXXxXxxXxxXxXxxXxXxxXXxXxxXx |               |
| market | String literal for the market.       | BTC-LTC                          | BTC-LTC       |
| units  | BUY/SELL total units.                | 1                                | 1             |
| spread | BUY/SELL markup/markdown percentage. | 0.0/0.0                          | 0.1/0.1       |

## Donations

If this script makes you money, buy me :beer:

    Bitcoin:  1Cvr9aHNmV2riULkfgEqofQtuhxCBe7A16
    Litecoin: LcMKbewQftytYnmsGTk63BW7yPCnUKFNni

## License and Warranty

This package is distributed in the hope that it will be useful, but without any warranty; without even the implied warranty of merchantability or fitness for a particular purpose.

_bittrex_autotrader_ is provided under the terms of the [MIT license](http://www.opensource.org/licenses/mit-license.php)

## Author

[Marc S. Brooks](https://github.com/nuxy)
