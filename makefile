.PHONY: FORCE

docs: FORCE
	sphinx-build -b html doc build/html
