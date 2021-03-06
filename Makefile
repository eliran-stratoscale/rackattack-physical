UPSETO_REQUIREMENTS_FULFILLED = $(shell upseto checkRequirements 2> /dev/null; echo $$?)
all: validate_requirements unittest build check_convention

clean:
	sudo rm -fr build

unittest: validate_python_requirements
	@UPSETO_JOIN_PYTHON_NAMESPACES=Yes PYTHONPATH=. python -m coverage run -m rackattack.physical.tests.runner
	@python -m coverage report --show-missing --fail-under=75 --include=rackattack/* --omit="rackattack/physical/tests/*"

.PHONY: integration_test
integration_test:
	sudo ./sh/integration_test

check_convention:
	pep8 rackattack --max-line-length=109

check_before_commit: check_convention unittest

.PHONY: build
build: validate_requirements build/rackattack.physical.egg build/rackattack.physical.reclamation.egg

build/rackattack.physical.egg: rackattack/physical/main.py
	-mkdir $(@D)
	python -m upseto.packegg --entryPoint=$< --output=$@ --createDeps=$@.dep --compile_pyc --joinPythonNamespaces
-include build/rackattack.physical.egg.dep

build/rackattack.physical.reclamation.egg: rackattack/physical/main_reclamationserver.py
	-mkdir $(@D)
	python -m upseto.packegg --entryPoint=$< --output=$@ --createDeps=$@.dep --compile_pyc --joinPythonNamespaces
-include build/rackattack.physical.reclamation.egg.dep

install_pika:
	-sudo mkdir /usr/share/rackattack.physical
	sudo cp pika-stable/pika-git-ref-6226dc0.egg /usr/share/rackattack.physical

install: validate_python_requirements install_pika build/rackattack.physical.egg build/rackattack.physical.reclamation.egg
	-sudo systemctl stop rackattack-physical.service
	-sudo systemctl stop rackattack-physical-reclamation.service
	-sudo mkdir /usr/share/rackattack.physical
	sudo cp build/rackattack.physical.egg /usr/share/rackattack.physical
	sudo cp build/rackattack.physical.reclamation.egg /usr/share/rackattack.physical
	sudo cp rackattack-physical.service /usr/lib/systemd/system/rackattack-physical.service
	sudo cp rackattack-physical-reclamation.service /usr/lib/systemd/system/rackattack-physical-reclamation.service
	sudo systemctl enable rackattack-physical.service
	sudo systemctl enable rackattack-physical-reclamation.service
	if ["$(DONT_START_SERVICE)" == ""]; then sudo systemctl start rackattack-physical; systemctl start rackattack-physical-reclamation; fi

uninstall:
	-sudo systemctl stop rackattack-physical
	-sudo systemctl disable rackattack-physical.service
	-sudo systemctl disable rackattack-physical-reclamation.service
	-sudo rm -fr /usr/lib/systemd/system/rackattack-physical.service
	-sudo rm -fr /usr/lib/systemd/system/rackattack-physical-reclamation.service
	sudo rm -fr /usr/share/rackattack.physical

prepareForCleanBuild: install_pika

.PHONY: validate_python_requirements
validate_python_requirements:
ifneq ($(SKIP_REQUIREMENTS),1)
ifeq ($(UPSETO_REQUIREMENTS_FULFILLED),1)
	$(error Upseto requirements not fulfilled. Run with SKIP_REQUIREMENTS=1 to skip requirements validation.)
	exit 1
else
	$(info ***********************************************************************)
	$(info * Note: Run with SKIP_REQUIREMENTS=1 to skip requirements validation. *)
	$(info ***********************************************************************)
	@sleep 4
endif
	@echo "Validating PIP requirements..."
	@sudo pip install -r requirements.txt
	@echo "PIP requirements satisfied."
else
	@echo "Skipping requirements validation."
endif

.PHONY: validate_requirements
validate_requirements: validate_python_requirements
ifneq ($(SKIP_REQUIREMENTS),1)
	sh/validate_packages_prerequisites.sh
else
	@echo "Skipping requirements validation."
endif

.PHONY: configure_nat
configure_nat:
ifeq ($(INTERFACE),)
	$(error Please set the INTERFACE makefile argument to the name of the network interface which is used as the public gateway.)
endif
	sudo UPSETO_JOIN_PYTHON_NAMESPACES=Yes PYTHONPATH=. python -m rackattack.physical.configurenat $(INTERFACE)

build/rackattack-physical.dockerfile: docker/rackattack-physical.dockerfile.m4 docker/rackattack-physical-base.dockerfile
	-mkdir $(@D)
	m4 -Idocker $< > $@

build/rackattack-physical-reclamation.dockerfile: docker/rackattack-physical-reclamation.dockerfile.m4 docker/rackattack-physical-base.dockerfile
	-mkdir $(@D)
	m4 -Idocker $< > $@

.PHONY: rackattack-physical-docker-image
rackattack-physical-docker-image: build/rackattack-physical.dockerfile
	docker build -f $< -t rackattack-physical:v5 build

.PHONY: rackattack-physical-reclamation-docker-image
rackattack-physical-reclamation-image: build/rackattack-physical-reclamation.dockerfile
	docker build -f $< -t rackattack-physical-reclamation:v5 build

run-rackattack-physical-docker-container: rackattack-physical-docker-image
	if [ $(docker ps | grep -c "rackattack-physical:") -ge 1 ]; then echo "Cannot start rackattack while another rackattack container is running."; exit 1; fi
	-rm /var/lib/rackattackphysical/cid
	docker run -v /etc/rackattack-physical/:/etc/rackattack-physical/ -v /usr/share/rackattack.physical/reclamation_requests_fifo:/usr/share/rackattack.physical/reclamation_requests_fifo -v /usr/share/rackattack.physical/soft_reclamations_failure_msg_fifo:/usr/share/rackattack.physical/soft_reclamations_failure_msg_fifo -v /var/lib/rackattackphysical/:/var/lib/rackattackphysical/ -p 1013:1013 -p 1014:1014 -p 1015:1015 -p 1016:1016 -p 67:67/udp -p 69:69 -p 53:53/udp --rm --cap-add NET_ADMIN --cidfile=/var/lib/rackattackphysical/cid rackattack-physical:v5

run-rackattack-physical-reclamation-docker-container: rackattack-physical-reclamation-docker-image
	if [ $(docker ps | grep -c "rackattack-physical-reclamation:") -ge 1 ]; then echo "Cannot start rackattack while another rackattack container is running."; exit 1; fi
	docker run -v /etc/rackattack.physical/:/etc/rackattack-physical -v /usr/share/rackattack.physical/reclamation_requests_fifo:/usr/share/rackattack.physical/reclamation_requests_fifo -v /usr/share/rackattack.physical/soft_reclamations_failure_msg_fifo:/usr/share/rackattack.physical/soft_reclamations_failure_msg_fifo --rm rackattack-physical-reclamation:v5

install_container: rackattack-physical-reclamation-image rackattack-physical-reclamation-image
	sleep 5
	sh/pipework br0 docker-`cat /var/lib/rackattackphysical/cid` 192.168.1.1/24
