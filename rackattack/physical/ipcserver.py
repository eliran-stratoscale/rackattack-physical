from rackattack.tcp import heartbeat
from rackattack.common import baseipcserver
from rackattack.physical import network
from rackattack.common.hoststatemachine import STATE_DESTROYED
import logging


class IPCServer(baseipcserver.BaseIPCServer):
    def __init__(self, publicNATIP, osmosisServerIP, dnsmasq, allocations, hosts, dynamicConfig):
        self._publicNATIP = publicNATIP
        self._osmosisServerIP = osmosisServerIP
        self._dnsmasq = dnsmasq
        self._allocations = allocations
        self._hosts = hosts
        self._dynamicConfig = dynamicConfig
        baseipcserver.BaseIPCServer.__init__(self)

    def cmd_allocate(self, requirements, allocationInfo, peer):
        import cProfile
        cProfile.runctx("allocation = self._allocations.create(requirements, allocationInfo)",
                        globals(), locals(), "allocate.txt")
        # allocation = self._allocations.create(requirements, allocationInfo)
        # return allocation.index()
        return self._allocations._allocations[-1].index()

    def cmd_allocation__inauguratorsIDs(self, id, peer):
        allocation = self._allocations.byIndex(id)
        if allocation.dead():
            raise Exception("Must not fetch nodes from a dead allocation")
        result = {}
        for name, stateMachine in allocation.allocated().iteritems():
            host = stateMachine.hostImplementation()
            result[name] = host.id()
        return result

    def cmd_allocation__nodes(self, id, peer):
        allocation = self._allocations.byIndex(id)
        if allocation.dead():
            raise Exception("Must not fetch nodes from a dead allocation")
        if not allocation.done():
            raise Exception("Must not fetch nodes from a not done allocation")
        result = {}
        for name, stateMachine in allocation.allocated().iteritems():
            host = stateMachine.hostImplementation()
            result[name] = dict(
                id=host.id(),
                primaryMACAddress=host.primaryMACAddress(),
                secondaryMACAddress=host.secondaryMACAddress(),
                ipAddress=host.ipAddress(),
                netmask=network.NETMASK,
                inauguratorServerIP=network.GATEWAY_IP_ADDRESS,
                gateway=network.GATEWAY_IP_ADDRESS,
                osmosisServerIP=self._osmosisServerIP)
        return result

    def cmd_allocation__free(self, id, peer):
        allocation = self._allocations.byIndex(id)
        if 'profile' in allocation._requirements.keys()[0]:
            # import cProfile
            # cProfile.runctx("self._allocations.byIndex(id).free()", globals(), locals(),
            #                 "/root/free-profiling.txt")
            import yappi
            yappi.start()
            allocation.free()
            yappi.stop()
            stats = yappi.get_func_stats()
            stats = yappi.convert2pstats(stats)
            stats.dump_stats("/root/free-profiling.txt")
        else:
            allocation.free()
        # Callgraph:
        # import pycallgraph
        # from pycallgraph import PyCallGraph
        # from pycallgraph.output import GraphvizOutput
        # graphviz = GraphvizOutput()
        # graphviz.output_file = "/root/bla.png"
        # with PyCallGraph(output=graphviz):
        #     self._allocations.byIndex(id).free()
        # self._allocations.byIndex(id).free()

    def cmd_allocation__done(self, id, peer):
        allocation = self._allocations.byIndex(id)
        return allocation.done()

    def cmd_allocation__dead(self, id, peer):
        allocation = self._allocations.byIndex(id)
        return allocation.dead()

    def cmd_heartbeat(self, ids, peer):
        for id in ids:
            allocation = self._allocations.byIndex(id)
            allocation.heartbeat()
        return heartbeat.HEARTBEAT_OK

    def _findNode(self, allocationID, nodeID):
        allocation = self._allocations.byIndex(allocationID)
        for stateMachine in allocation.inaugurated().values():
            if stateMachine.hostImplementation().id() == nodeID:
                return stateMachine
        raise Exception("Node with id '%s' was not found in this allocation" % nodeID)

    def cmd_node__rootSSHCredentials(self, allocationID, nodeID, peer):
        stateMachine = self._findNode(allocationID, nodeID)
        credentials = stateMachine.hostImplementation().rootSSHCredentials()
        return network.translateSSHCredentials(
            index=stateMachine.hostImplementation().index(),
            credentials=credentials,
            publicNATIP=self._publicNATIP,
            peer=peer)

    def cmd_node__coldRestart(self, allocationID, nodeID, peer):
        stateMachine = self._findNode(allocationID, nodeID)
        logging.info("Cold restarting node %(node)s by allocator request", dict(node=nodeID))
        stateMachine.hostImplementation().coldRestart()

    def cmd_node__answerDHCP(self, allocationID, nodeID, shouldAnswer, peer):
        stateMachine = self._findNode(allocationID, nodeID)
        logging.info("Should answer DHCP: %(should)s node %(node)s", dict(node=nodeID, should=shouldAnswer))
        if shouldAnswer:
            self._dnsmasq.addIfNotAlready(
                stateMachine.hostImplementation().primaryMACAddress(),
                stateMachine.hostImplementation().ipAddress())
        else:
            self._dnsmasq.remove(stateMachine.hostImplementation().primaryMACAddress())

    def cmd_admin__queryStatus(self, peer):
        allocations = [dict(
            index=a.index(),
            allocationInfo=a.allocationInfo(),
            allocated={k: v.hostImplementation().index() for k, v in a.allocated().iteritems()},
            done=a.dead() or a.done(),
            dead=a.dead()
            ) for a in self._allocations.all()]
        hosts = self._onlineHosts() + self._offlineHosts()
        return dict(allocations=allocations, hosts=hosts)

    def _offlineHosts(self):
        return [dict(index=host.index(),
                     id=host_id,
                     primaryMACAddress=host.primaryMACAddress(),
                     secondaryMACAddress=host.secondaryMACAddress(),
                     ipAddress=host.ipAddress(),
                     state="OFFLINE")
                for host_id, host in self._dynamicConfig.getOfflineHosts().iteritems()]

    def _onlineHosts(self):
        STATE = {
            1: "QUICK_RECLAIMATION_IN_PROGRESS",
            2: "SLOW_RECLAIMATION_IN_PROGRESS",
            3: "CHECKED_IN",
            4: "INAUGURATION_LABEL_PROVIDED",
            5: "INAUGURATION_DONE",
            6: "DESTROYED"}
        statesOfHostsThatHaveMachines = dict([(machine.hostImplementation().id(), machine.state())
                                             for machine in self._hosts.all()])
        return [dict(index=host.index(),
                     id=hostID,
                     primaryMACAddress=host.primaryMACAddress(),
                     secondaryMACAddress=host.secondaryMACAddress(),
                     ipAddress=host.ipAddress(),
                     state=STATE[statesOfHostsThatHaveMachines.get(hostID, STATE_DESTROYED)])
                for hostID, host in self._dynamicConfig.getOnlineHosts().iteritems()]
