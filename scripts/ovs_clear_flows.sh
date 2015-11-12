#!/bin/bash

cd /var/run/openvswitch/

for f in as*.mgmt; do
    echo "Clear -> $f"
    /usr/bin/ovs-ofctl del-flows $f
done

for f in es*.mgmt; do
    echo "Clear -> $f"
    /usr/bin/ovs-ofctl del-flows $f
done

for f in cs*.mgmt; do
    echo "Clear -> $f"
    /usr/bin/ovs-ofctl del-flows $f
done

for f in hostbr*.mgmt; do
    echo "Clear -> $f"
    /usr/bin/ovs-ofctl del-flows $f
done
