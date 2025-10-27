.PHONY: FORCE

# sphinx-apidoc -o doc/api patchtree
docs: FORCE
	sphinx-build -b html doc build/html
