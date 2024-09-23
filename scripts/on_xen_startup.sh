#!/bin/bash

# Mount NFS share
mount -t nfs -o defaults Vlab-gluster3:/mnt/vlab-datastore-7T /mnt/vlab-datastore

# Increase CPU priority for Domain-0 (to ensure it gets more CPU time)
xl sched-credit -d Domain-0 -w 2048

# Disable Netfilter on Bridges (Xen xl usage)
iptables -I FORWARD -m physdev --physdev-is-bridged -j ACCEPT

# Create bonds for course networks
/home/vital/source/xen-api/scripts/xen_course_network_startup.sh
