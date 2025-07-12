# Variables
ACTIVATE=. venv/bin/activate &&
include .env

ODOO_SRC=src/odoo
ADDONS_DIR=./extra-addons
GITMODULES_FILE=.gitmodules
DOCKER_COMPOSE=docker-compose
GIT=git
DATE=$(shell date +'%Y%m%d%H%M%S')

.PHONY: modules clean-modules symlinks sync-addons docker/requirements.txt $(ODOO_SRC) push build

all: init-dev modules symlinks docker/requirements.txt

build: symlinks docker/requirements.txt
	$(DOCKER_COMPOSE) build odoo

push:
	$(DOCKER_COMPOSE) push odoo


clean: clean-modules

clean-modules:
	rm -rf .git/modules/*
	rm -rf extra-addons/.src
	$(GIT) submodule deinit --force --all

modules:
	@echo "Creating directories..."
	mkdir -p extra-addons/.src
	@echo "Adding submodules..."
	for module in $$($(GIT) config -f .gitmodules --get-regexp '^submodule\..*\.path$$' | awk '{print $$2}'); do \
		url=$$($(GIT) config -f .gitmodules --get submodule.$$module.url); \
		branch=$$($(GIT) config -f .gitmodules --get submodule.$$module.branch || echo "master"); \
		echo "Adding $$module ($$url:$$branch)"; \
		$(GIT) submodule add -f -b $$branch $$url $$module || true; \
	done
	@echo "Initializing and updating..."
	$(GIT) submodule update --init --recursive --force
	$(GIT) submodule foreach --recursive 'git checkout $$(git config -f $$toplevel/.gitmodules submodule.$$name.branch || echo master)'
	$(GIT) submodule foreach --recursive 'git pull'

symlinks:
	cd $(ADDONS_DIR) && find . -maxdepth 1 -type l -delete ; \
	for addon in $$(find .src -type f -name __manifest__.py | sed 's/__manifest__.py//g'); do \
		[ -d "$$addon" ] && ln -sf "$$addon" .; \
	done

docker/requirements.txt:
	$(ACTIVATE)	setuptools-odoo-make-default --odoo-version-override="$(ODOO_VERSION)" --addons-dir "$(ADDONS_DIR)" && \
	$(ACTIVATE) (setuptools-odoo-get-requirements --addons-dir "$(ADDONS_DIR)" | \
	grep -v 'csv' | grep -v 'infobip' | grep -v "cryptography"| grep -v 'ldap' | grep -v 'en_core_web_sm' |\
	sed -e 's/pysftp/pysftp==0.2.8/' -e 's/facturx/factur-x/' \
	-e 's/PIL/Pillow/' -e 's/cv2/opencv-python/' -e 's/speech_recognition/speechrecognition/'; \
	echo "pyOpenSSL==22.0.0"; echo "cryptography==36.0.2"; echo "lxml_html_clean"; echo "fsspec[gcs]")\
	> docker/requirements.txt

init: venv
	$(ACTIVATE) pip install --upgrade pip setuptools-odoo wheel -r src/odoo/requirements.txt -r docker/requirements.txt

venv:
	python3 -m venv venv

init-dev: $(ODOO_SRC) init

$(ODOO_SRC):
	if [ -d "$(ODOO_SRC)" ]; then cd $(ODOO_SRC) && git pull; else git clone --depth=1 -b $(ODOO_VERSION) https://github.com/odoo/odoo $(ODOO_SRC); fi
	perl -p -i -e 's/(greenlet|gevent|psycopg2|requests)[>=<~\\!].*$$/\1/' $(ODOO_SRC)/requirements.txt


local-data/odoo.conf:
	mkdir -p local-data
	touch local-data/odoo.conf

run: local-data/odoo.conf
	$(ACTIVATE) src/odoo/odoo-bin \
	-c ./local-data/odoo.conf -i web \
	--limit-time-cpu=600 --limit-time-real=600 --db_host=localhost --db_user=odoo --db_password=odoo \
	--addons-path=src/odoo/addons/,extra-addons/ -d ${ODOO_DATABASE}

upgrade: local-data/odoo.conf
	$(ACTIVATE) src/odoo/odoo-bin \
	-c ./local-data/odoo.conf --stop-after-init --no-http \
	--limit-time-cpu=600 --limit-time-real=600 --db_host=localhost --db_user=odoo --db_password=odoo \
	--addons-path=src/odoo/addons/,extra-addons/ -d ${ODOO_DATABASE} -u all

up:
	$(DOCKER_COMPOSE) up odoo

run-config:
	@echo "Creating IntelliJ run configuration..."
	@mkdir -p .idea/runConfigurations
	@echo '<?xml version="1.0" encoding="UTF-8"?>' > .idea/runConfigurations/Odoo.xml
	@echo '<component name="ProjectRunConfigurationManager">' >> .idea/runConfigurations/Odoo.xml
	@echo '  <configuration default="false" name="Odoo" type="PythonConfigurationType" factoryName="Python">' >> .idea/runConfigurations/Odoo.xml
	@echo '    <module name="$$PROJECT_NAME$$" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="INTERPRETER_OPTIONS" value="" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="PARENT_ENVS" value="true" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <envs>' >> .idea/runConfigurations/Odoo.xml
	@echo '      <env name="PYTHONUNBUFFERED" value="1" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    </envs>' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="SDK_HOME" value="$$PROJECT_DIR$$/venv/bin/python" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="SDK_NAME" value="Python 3.9 (venv)" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="WORKING_DIRECTORY" value="$$PROJECT_DIR$$" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="IS_MODULE_SDK" value="false" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="ADD_CONTENT_ROOTS" value="true" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="ADD_SOURCE_ROOTS" value="true" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="SCRIPT_NAME" value="$$PROJECT_DIR$$/src/odoo/odoo-bin" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="PARAMETERS" value="-c ./local-data/odoo.conf -i web --limit-time-cpu=600 --limit-time-real=600 --db_host=localhost --db_user=odoo --db_password=odoo --addons-path=src/odoo/addons/,extra-addons/ -d ${ODOO_DATABASE}" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="SHOW_COMMAND_LINE" value="false" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <option name="EMULATE_TERMINAL" value="true" />' >> .idea/runConfigurations/Odoo.xml
	@echo '    <method v="2" />' >> .idea/runConfigurations/Odoo.xml
	@echo '  </configuration>' >> .idea/runConfigurations/Odoo.xml
	@echo '</component>' >> .idea/runConfigurations/Odoo.xml
	@echo "IntelliJ run configuration created at .idea/runConfigurations/Odoo.xml"

