#!/bin/bash

if [ $# -lt 1 ];
then
  echo "You need to specify the hostname"
  exit
fi

HNAME=$1

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
echo -e "organization = UFRGS (test server)\ncn = $HNAME\ntls_www_server\nencryption_key\nsigning_key" > server.info
certtool --generate-privkey > serverkey.pem
certtool --generate-certificate \
         --template server.info \
         --load-privkey serverkey.pem \
         --load-ca-certificate cacert.pem \
         --load-ca-privkey cakey.pem \
         --outfile servercert.pem
if [ ! -d /etc/pki ];
then
  mkdir /etc/pki
fi
if [ ! -d /etc/pki/libvirt ];
then
  mkdir /etc/pki/libvirt
fi
cp servercert.pem /etc/pki/libvirt/servercert.pem
if [ ! -d /etc/pki/libvirt/private ];
then
  mkdir /etc/pki/libvirt/private
fi 
cp serverkey.pem /etc/pki/libvirt/private/serverkey.pem

