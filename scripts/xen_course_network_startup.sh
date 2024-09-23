#!/bin/bash

function create_bond {
    vlan=$1
    vconfig add bond0 $vlan
    # ifconfig bond0.$vlan up
    ip link set bond0.$vlan up
}

function add_bridge_if {
  brdg=$1
  bond=$2
  echo "Creating $bond on $brdg"
  brctl addbr $brdg
  # ifconfig $brdg up
  ip link set dev $brdg up
  brctl addif $brdg $bond
}

# reading from config file
host=$(awk -F ":" '/VITAL_DB_HOST/ {print $2}' /home/vital/config.ini | tr -d ' ')
database=$(awk -F ":" '/VITAL_DB_NAME/ {print $2}' /home/vital/config.ini | tr -d ' ')
user=$(awk -F ":" '/VITAL_DB_USER/ {print $2}' /home/vital/config.ini | tr -d ' ')
pass=$(awk -F ":" '/VITAL_DB_PWD/ {print $2}' /home/vital/config.ini | tr -d ' ')

nets=$(PGPASSWORD=$pass psql -U $user -d $database -h $host -t -c "SELECT c.id from vital_course c join vital_network_configuration n on c.id=n.course_id where c.status='ACTIVE' and n.is_course_net=True")
set -f
array=(${nets// / })

for var in "${array[@]}"
do
    echo "Creating for $var"
    create_bond $var
    # set host and password for each server
    net_name=$(PGPASSWORD=$pass psql -U postgres -d vital_db -h $host -t -c "SELECT n.name from vital_network_configuration n where n.is_course_net=True and n.course_id="+$var)
    echo "Creating bridge for $net_name"
    add_bridge_if $net_name bond0.$var
done
