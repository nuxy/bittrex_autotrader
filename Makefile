init:
	pip3 install -r requirements.txt

lint:
	pylint bittrex_autotrader

docs:
	python3.6 -m pydoc -w bittrex_autotrader

dist:
	mkdir bittrex_autotrader && touch bittrex_autotrader/__init__.py
	cp bittrex_autotrader.py bittrex_autotrader/bittrex_autotrader
	python3 setup.py sdist
