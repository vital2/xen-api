#!/bin/bash

function create_bond {
    vlan=$1
    vconfig add bond0 $vlan
    ifconfig bond0.$vlan up

}

function add_bridge_if {
  brdg=$1
  bond=$2
  echo "Creating $bond on $brdg"
  brctl addbr $brdg
  ifconfig $brdg up
  brctl addif $brdg $bond
}

nets=$(psql -U postgres -d vital_db -t -c "SELECT c.id from vital_course c join vital_network_configuration n on c.id=n.course_id where c.status='ACTIVE'")
set -f
array=(${nets// / })

for var in "${array[@]}"
do
    create_bond $var
    net_name=$(psql -U postgres -d vital_db -t -c "SELECT n.name from vital_network_configuration n where n.is_course_net=True and n.course_id="+$var)
    add_bridge_if net_name "bond0."+$var
done
