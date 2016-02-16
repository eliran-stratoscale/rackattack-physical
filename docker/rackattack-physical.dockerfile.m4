include(rackattack-physical-base.dockerfile)

# Install other tools
RUN yum update -y && \
    yum install -y \
    dnsmasq \
    net-tools \
    tcpdump \
    iptables

EXPOSE 1013 1014 1015 1016 53 67/udp 68 69

ENV PYTHONPATH /usr/share/rackattack.physical/rackattack.physical.egg

RUN wget --no-check-certificate https://raw.github.com/jpetazzo/pipework/master/pipework && \
    chmod +x pipework

CMD \
    echo Setting up iptables... &&\
    iptables -t nat -A POSTROUTING -j MASQUERADE ! -d 127.0.0.0/8 &&\
    echo Waiting for pipework to give us the eth1 interface... &&\
    ./pipework --wait &&\
    myIP=$(ip addr show dev eth1 | awk -F '[ /]+' '/global/ {print $3}') &&\
    mySUBNET=$(echo $myIP | cut -d '.' -f 1,2,3) &&\
    echo Starting...&&\
    /usr/bin/python -m rackattack.physical.main
