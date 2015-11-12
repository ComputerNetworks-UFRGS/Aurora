#!/bin/bash

BASEDIR=$(dirname $(readlink -f $0))

for ((  i = 1 ;  i <= 64;  i++  ))
do
    # Compiling libvirt
    mkdir /tmp/h$i
    tar -zxf ~/libvirt-1.2.12.tar.gz -C /tmp/h$i
    echo "##### Installing libvirt for host $i #####"
    cd $BASEDIR
    ./compile_libvirt.sh /tmp/h$i/libvirt-1.2.12 /usr/local/libvirt/h$i &

    # Create alias for easy starting the daemons
    cd /usr/local/sbin
    ln -s /usr/local/libvirt/h$i/sbin/libvirtd libvirtd-h$i
done
