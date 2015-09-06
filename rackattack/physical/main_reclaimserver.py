import yaml
import logging
import argparse
import threading
import inaugurator.server.config
from rackattack.common import tftpboot
from rackattack.physical import config
from rackattack.physical import network
from rackattack.physical.coldreclaim import coldReclaim
from rackattack.common.reclaimserver import IOLoop
from rackattack.physical.config import (RECLAMATION_REQUESTS_FIFO_PATH,
                                        SOFT_RECLAMATION_FAILURE_MSG_FIFO_PATH)


class InauguratorCommandLine:
    def __init__(self, netmask, osmosisServerIP, inauguratorServerIP, inauguratorServerPort,
                 inauguratorGatewayIP, rootPassword, withLocalObjectStore):
        self._netmask = netmask
        self._osmosisServerIP = osmosisServerIP
        self._inauguratorServerIP = inauguratorServerIP
        self._inauguratorServerPort = inauguratorServerPort
        self._inauguratorGatewayIP = inauguratorGatewayIP
        self._rootPassword = rootPassword
        self._withLocalObjectStore = withLocalObjectStore

    def __call__(self, id, mac, ip, clearDisk):
        result = tftpboot._INAUGURATOR_COMMAND_LINE % dict(
            macAddress=mac, ipAddress=ip, netmask=self._netmask,
            osmosisServerIP=self._osmosisServerIP, inauguratorServerIP=self._inauguratorServerIP,
            inauguratorServerPort=self._inauguratorServerPort,
            inauguratorGatewayIP=self._inauguratorGatewayIP,
            rootPassword=self._rootPassword,
            id=id)
        if self._withLocalObjectStore:
            result += " --inauguratorWithLocalObjectStore"
        if clearDisk:
            result += " --inauguratorClearDisk"
        return result


def configureLogger():
    logger = logging.getLogger("reclamation")
    logger.setLevel(logging.INFO)
    streamHandler = logging.StreamHandler()
    streamHandler.setLevel(logging.INFO)
    logger.addHandler(streamHandler)


def main():
    configureLogger()
    with open(config.CONFIGURATION_FILE, "r") as f:
        conf = yaml.load(f.read())
    network.setGatewayIP(conf['GATEWAY_IP'])
    netmask = network.NETMASK
    inauguratorServerIP = network.BOOTSERVER_IP_ADDRESS
    inauguratorServerPort = inaugurator.server.config.PORT
    inauguratorGatewayIP = network.GATEWAY_IP_ADDRESS
    osmosisServerIP = conf['OSMOSIS_SERVER_IP']
    rootPassword = config.ROOT_PASSWORD
    withLocalObjectStore = config.WITH_LOCAL_OBJECT_STORE
    inauguratorCommandLine = InauguratorCommandLine(netmask,
                                                    osmosisServerIP,
                                                    inauguratorServerIP,
                                                    inauguratorServerPort,
                                                    inauguratorGatewayIP,
                                                    rootPassword,
                                                    withLocalObjectStore)
    ioLoop = IOLoop(inauguratorCommandLine,
                    reclamationRequestFifoPath=RECLAMATION_REQUESTS_FIFO_PATH,
                    softReclamationFailedMsgFifoPath=SOFT_RECLAMATION_FAILURE_MSG_FIFO_PATH)
    ioLoop.registerAction("cold", coldReclaim)
    ioLoop.run()

if __name__ == "__main__":
    main()
