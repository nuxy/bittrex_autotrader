init:
	pip install -r requirements.txt

docs:
	python -m pydoc -w bittrex_autotrader

dist:
	mkdir bittrex_autotrader && touch bittrex_autotrader/__init__.py
	cp bittrex_autotrader.py bittrex_autotrader/bittrex_autotrader
	python setup.py sdist
