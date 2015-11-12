#!/bin/bash

BASEDIR=$(dirname $(readlink -f $0))
cd $BASEDIR

# Generate CA
./generate_ca.sh

for ((  i = 1 ;  i <= 64;  i++  ))
do
    # Generate certificates
    cd $BASEDIR
    ./generate_server_tls.sh h$i /usr/local/libvirt/h$i

    # Copy authority
    cd ~/.cert
    if [ ! -d /usr/local/libvirt/h$i/etc/pki ];
    then
        mkdir -p /usr/local/libvirt/h$i/etc/pki
    fi
    if [ ! -d /usr/local/libvirt/h$i/etc/pki/CA ];
    then
        mkdir -p /usr/local/libvirt/h$i/etc/pki/CA
    fi
    cp cacert.pem /usr/local/libvirt/h$i/etc/pki/CA
done
