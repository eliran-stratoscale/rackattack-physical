import os
import random
from rackattack.common import reclaimserver
from rackattack.physical import config, ipmi
from rackattack.physical.tests.integration.main import useFakeRackConf, useFakeIPMITool


ORIG_SOFT_RECLAIM = reclaimserver.SoftReclaim


class FakeSoftReclaim(ORIG_SOFT_RECLAIM):
    def __init__(self,
                 hostID,
                 hostname,
                 username,
                 password,
                 macAddress,
                 inauguratorCommandLine,
                 softReclamationFailedMsgFifoWriteFd,
                 inauguratorKernel,
                 inauguratorInitRD):
        hostname = "10.0.0.101"
        username = "root"
        password = "strato"
        macAddress = hostID + "-primary-mac"
        self._ipmi = ipmi.IPMI(hostID + "-fake-ipmi", "root", "strato")
        assert hasattr(self, "_KEXEC_CMD")
        self._KEXEC_CMD = "echo"
        ORIG_SOFT_RECLAIM.__init__(self,
                                   hostID,
                                   hostname,
                                   username,
                                   password,
                                   macAddress,
                                   inauguratorCommandLine,
                                   softReclamationFailedMsgFifoWriteFd,
                                   inauguratorKernel,
                                   inauguratorInitRD)

    def run(self):
        logging.info("Faking kexec reset by physically restarting host %(id)s", dict(id=self._hostID))
        ORIG_SOFT_RECLAIM.run(self)
        self._ipmi._powerCycle()

    def _validateUptime(self):
        uptime = self._getUptime()
        if random.randint(0, 9) == 0:
            raise UptimeTooLong(100000)


if __name__ == "__main__":
    useFakeRackConf()
    useFakeIPMITool()
    assert hasattr(reclaimserver, "SoftReclaim")
    reclaimserver.SoftReclaim = FakeSoftReclaim
    # Cannot import main since python does not support spwaning threads from an import context
    mainPath = os.path.join(os.curdir, "rackattack", "physical", "main_reclaimserver.py")
    execfile(mainPath)
    neverEnds = threading.Event()
    neverEnds.wait()
