
.PHONY: install test run clean

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

run:
	streamlit run dashboard/app.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
