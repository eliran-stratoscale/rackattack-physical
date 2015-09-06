import os
import yaml
import random
import tempfile
import rackattack.physical.config
from rackattack.physical.tests.integration import use_local_inaugurator
from rackattack.common import reclaimserver


use_local_inaugurator.verify()


FAKE_REBOOTS_PIPE_NAME = os.path.join("/var", "lib", "rackattackphysical", "fake_reboots_pipe")
RACK_CONFIG_FILE_PATH = os.path.join("/var", "lib", "rackattackphysical", "integration_test_rack.yaml")


def useFakeRackConf():
    assert hasattr(rackattack.physical.config, "RACK_YAML")
    rackattack.physical.config.RACK_YAML = RACK_CONFIG_FILE_PATH


def useFakeIPMITool():
    assert hasattr(rackattack.physical.config, "IPMITOOL_FILENAME")
    rackattack.physical.config.IPMITOOL_FILENAME = "sh/ipmitool_mock"

if __name__ == "__main__":
    useFakeRackConf()
    useFakeIPMITool()
    nrRacks = 6
    nrHostsInRack = 64
    hosts = [dict(id="rack%02d-server%02d" % (rackIdx, hostIdx),
                  ipmiLogin=dict(username="root",
                                 password="strato",
                                 hostname="rack%02d-server%02d-fake-ipmi" % (rackIdx, hostIdx)),
                  primaryMAC="rack%02d-server%02d-primary-mac" % (rackIdx, hostIdx),
                  secondaryMAC="rack%02d-server%02d-secondary-mac" % (rackIdx, hostIdx),
                  topology=dict(rackID="rack%02d" % (rackIdx,)),
                  offline=False) for hostIdx in xrange(1, nrHostsInRack + 1)
             for rackIdx in xrange(1, nrRacks + 1)]
    rackConf = dict(HOSTS=hosts)
    with open(rackattack.physical.config.RACK_YAML, "w") as configFile:
        yaml.dump(rackConf, configFile)
    # Cannot import main since python does not support spwaning threads from an import context
    mainPath = os.path.join(os.curdir, "rackattack", "physical", "main.py")
    execfile(mainPath)
    neverEnds = threading.Event()
    neverEnds.wait()
