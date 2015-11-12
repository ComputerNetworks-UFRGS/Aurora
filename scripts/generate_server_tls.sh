#!/bin/bash

if [ $# -lt 1 ];
then
    echo "You need to specify the hostname"
    echo -e "\n\tUsage: generate_server_tls.sh HOSTNAME [ INSTALL_PATH (e.g., /usr/local) ]\n"
    exit
fi
HNAME=$1

if [ $# -eq 2 ];
then
    INSTALL_PATH=$2
else
    INSTALL_PATH=""
fi

if [ $# -gt 2 ];
then
    echo "Too many arguments"
    echo -e "\n\tUsage: generate_server_tls.sh HOSTNAME [ INSTALL_PATH (e.g., /usr/local) ]\n"
    exit
fi

if [ ! -d ~/.cert ];
then
  mkdir ~/.cert
fi

cd ~/.cert

if [ ! -f cacert.pem ];
then
  echo "Could not find cacert.pem file. Generate a authority certificate first."
  exit
fi

if [ ! -f cakey.pem ];
then
  echo "Could not find cakey.pem file. Generate a authority certificate first."
  exit
fi

# Server certificate
echo "##### Creating certificates for host $HNAME #####"
echo -e "organization = UFRGS (test server)\ncn = $HNAME\ntls_www_server\nencryption_key\nsigning_key\nexpiration_days=3650" > server.info
certtool --generate-privkey > serverkey.pem
certtool --generate-certificate \
         --template server.info \
         --load-privkey serverkey.pem \
         --load-ca-certificate cacert.pem \
         --load-ca-privkey cakey.pem \
         --outfile servercert.pem

# Install certificates
if [ ! -d $INSTALL_PATH/etc/pki/libvirt/private ];
then
    mkdir -p $INSTALL_PATH/etc/pki/libvirt/private
fi
cp servercert.pem $INSTALL_PATH/etc/pki/libvirt/servercert.pem
cp serverkey.pem $INSTALL_PATH/etc/pki/libvirt/private/serverkey.pem
chmod 600 $INSTALL_PATH/etc/pki/libvirt/private/serverkey.pem

