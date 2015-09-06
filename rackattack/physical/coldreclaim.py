import time
import asyncio
import logging
import multiprocessing.pool


from rackattack.physical import config


@asyncio.coroutine
def ipmiPowerCommand(hostname, username, password, command):
    cmdLine = [config.IPMITOOL_FILENAME, "power", command, "-H",
               hostname, "-U", username, "-P", password]
    print(cmdLine)
    process = asyncio.create_subprocess_exec(*cmdLine)
    yield from process

@asyncio.coroutine
def coldReclaim(hostname, username, password):
    yield from ipmiPowerCommand(hostname, username, password, "off")
    yield from ipmiPowerCommand(hostname, username, password, "on")
