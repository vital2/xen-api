#!/bin/bash

mount -t glusterfs 128.238.77.30:volume1 /mnt/vlab-datastore
xl sched-credit -d Domain-0 -w 2048

#Disable Netfilter on Bridges (Xen xl usage)
iptables -I FORWARD -m physdev --physdev-is-bridged -j ACCEPT

# create bonds for course networks
/home/vlab/source/xen-api/scripts/xen_course_network_startup.sh