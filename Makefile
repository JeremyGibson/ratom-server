update_requirements:
	pip install -U -q pip-tools
	pip-compile --output-file=requirements/base/base.txt requirements/base/base.in
	pip-compile --output-file=requirements/dev/dev.txt requirements/dev/dev.in
	pip-compile --output-file=requirements/deploy/deploy.txt requirements/deploy/deploy.in

install_requirements:
	@echo 'Installing pip-tools...'
	export PIP_REQUIRE_VIRTUALENV=true; \
	pip install -U -q pip-tools
	@echo 'Installing requirements...'
	pip-sync requirements/base/base.txt requirements/dev/dev.txt

setup:
	@echo 'Setting up the environment...'
	make install_requirements
