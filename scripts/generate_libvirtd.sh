#!/bin/bash

HNAME=`hostname -s`

# Creating configuration file
if [ ! -d /root/$HNAME ];
then
	mkdir /root/$HNAME
fi

echo -e "listen_tls = 0" > /root/$HNAME/libvirtd.conf
echo -e "listen_tcp = 1" >> /root/$HNAME/libvirtd.conf
echo -e "unix_sock_group = \"libvirtd\"" >> /root/$HNAME/libvirtd.conf 
echo -e "unix_sock_rw_perms = \"0770\"" >> /root/$HNAME/libvirtd.conf
echo -e "auth_unix_ro = \"none\"" >> /root/$HNAME/libvirtd.conf
echo -e "auth_unix_rw = \"none\"" >> /root/$HNAME/libvirtd.conf
echo -e "key_file = \"/etc/pki/libvirt/$HNAME/private/serverkey.pem\"" >> /root/$HNAME/libvirtd.conf
echo -e "cert_file = \"/etc/pki/libvirt/$HNAME/servercert.pem\"" >> /root/$HNAME/libvirtd.conf

# Creating directory for logs
if [ ! -d /var/log/libvirt/ ];
then
	mkdir /var/log/libvirt/
fi
echo -e "log_level = 1" >> /root/$HNAME/libvirtd.conf
echo -e "log_outputs=\"3:file:/var/log/libvirt/$HNAME-server.log\"" >> /root/$HNAME/libvirtd.conf

