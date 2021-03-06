#!/bin/bash

# Determine package manager
YUM_CMD=$(which yum)
APT_GET_CMD=$(which apt-get)
if [[ "$YUM_CMD" != "" ]]; then
sudo yum install -y syslinux-tftpboot;
rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc;
sudo yum install -y --nogpg rabbitmq-server;
elif [[ "$APT_GET_CMD" != "" ]]; then
sudo apt-get -y install syslinux pxelinux rabbitmq-server;
sudo systemctl stop rabbimq-server
sudo systemctl disable rabbimq-server
else
echo "Error: Package manager was not found. Cannot continue with the installation.";
exit 1;
fi
which solvent > /dev/null || (echo "Error: solvent was not found. Please install it first." && exit 1)
