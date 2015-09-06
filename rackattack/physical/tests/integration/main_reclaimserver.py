import os
import time
import random
import asyncio
from rackattack.common import reclaimserver
#from rackattack.physical import config, ipmi
from rackattack.physical.tests.integration.main import (useFakeRackConf, useFakeIPMITool,
    FAKE_REBOOTS_PIPE_NAME)
from rackattack.physical.coldreclaim import coldReclaim


ORIG_SOFT_RECLAIM = reclaimserver.SoftReclaim


fakeRebootRequestfd = None


class FakeSoftReclaim(ORIG_SOFT_RECLAIM):
    def __init__(self,
                 inauguratorCommandLine,
                 softReclamationFailedMsgFifoWriteFd,
                 hostID,
                 hostname,
                 username,
                 password,
                 macAddress):
        hostname = "10.0.0.101"
        username = "root"
        password = "strato"
        self._hostID = hostID
        macAddress = hostID + "-primary-mac"
        self._ipmiHostname = hostID + "-fake-ipmi"
        #self._ipmi = ipmi.IPMI(self._ipmiHostname, "root", "strato")
        assert hasattr(self, "_KEXEC_CMD")
        self._KEXEC_CMD = "echo"
        ORIG_SOFT_RECLAIM.__init__(self,
                                   inauguratorCommandLine,
                                   softReclamationFailedMsgFifoWriteFd,
                                   hostID,
                                   hostname,
                                   username,
                                   password,
                                   macAddress)

    @asyncio.coroutine
    def run(self):
        print("Faking kexec reset by physically restarting host %(id)s" % dict(id=self._hostID))
        yield from ORIG_SOFT_RECLAIM.run(self)
        self._informFakeConsumersManagerOfReboot()

    @asyncio.coroutine
    def _validateUptime(self, sftp):
        uptime = yield from self._getUptime(sftp)
        print("Uptime: %s" % (str(uptime),))
        #if random.randint(0, 9) == 0:
        #    print("Uptime too long")
        #    raise ValueError(100000)

    def _informFakeConsumersManagerOfReboot(self):
        hostRequest = "%(hostname)s," % dict(hostname=self._ipmiHostname)
        hostRequest = hostRequest.encode("utf-8")
        before = time.time()
        os.write(fakeRebootRequestfd, hostRequest)
        after = time.time()
        print("Writing to fifo took %(amount)s seconds" % dict(amount=before - after))

@asyncio.coroutine
def fakeSoftReclaim(self, inauguratorCommandLine, softReclamationFailedMsgFifoWriteFd, *args, **kwargs):
    print(*args)
    softReclaim = FakeSoftReclaim(inauguratorCommandLine,
                                  softReclamationFailedMsgFifoWriteFd,
                                  *args,
                                  **kwargs)
    yield from softReclaim.run()


if __name__ == "__main__":
    useFakeRackConf()
    useFakeIPMITool()
    print("Opening fake reboot manager's request fifo write end...")
    global fakeRebootRequestfd
    fakeRebootRequestfd = os.open(FAKE_REBOOTS_PIPE_NAME, os.O_WRONLY)
    print("Fifo open.")
    assert hasattr(reclaimserver, "SoftReclaim")
    reclaimserver.IOLoop._softReclaim = fakeSoftReclaim
    # Cannot import main since python does not support spwaning threads from an import context
    mainPath = os.path.join(os.curdir, "rackattack", "physical", "main_reclaimserver.py")
    with open(mainPath) as f:
        code = compile(f.read(), mainPath, 'exec')
        exec(code, globals(), locals())
