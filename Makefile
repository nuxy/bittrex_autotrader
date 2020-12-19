init:
	pip3 install -r requirements.txt

lint:
	pylint bittrex_autotrader

docs:
	python3.6 -m pydoc -w bittrex_autotrader/request.py

dist:
	mkdir bin && cp bittrex_autotrader/__main__.py bin/bittrex_autotrader
	python3.6 setup.py sdist
