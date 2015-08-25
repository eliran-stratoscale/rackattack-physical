from rackattack.common.reclaimhost import ReclaimHostSpooler


class ReclaimPhysicalHostSpooler(ReclaimHostSpooler):
    def __init__(self, *args, **kwargs):
        ReclaimHostSpooler.__init__(self, *args, **kwargs)

    def _handleColdReclamationRequest(self, host):
        credentials = host.ipmiLoginCredentials()
        args = [credentials["hostname"],
                credentials["username"],
                credentials["password"]]
        self._sendRequest("cold", args)
        host.coldRestart()
