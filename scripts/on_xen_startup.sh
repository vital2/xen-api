#!/bin/bash

#mount -t glusterfs gusterfs1-dev:volume1 /mnt/vlab-datastore
# mount -t glusterfs Vlab-gluster1:/vlab /mnt/vlab-datastore
##ap4414 EDIT: added nfs mount to /etc/fstab
#gusterfs1-dev:volume1 /mnt/vlab-datastore/ nfs async,hard,intr,rw,nolock 0 0

xl sched-credit -d Domain-0 -w 2048

#Disable Netfilter on Bridges (Xen xl usage)
iptables -I FORWARD -m physdev --physdev-is-bridged -j ACCEPT

# create bonds for course networks
/home/vital/source/xen-api/scripts/xen_course_network_startup.sh
