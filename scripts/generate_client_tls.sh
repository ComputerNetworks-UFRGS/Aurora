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

echo -e "country = BR\nstate = RS\nlocality = Porto Alegre\norganization = UFRGS (testing client)\ncn = $HNAME\ntls_www_client\nencryption_key\nsigning_key" > client.info

certtool --generate-privkey > clientkey.pem

certtool --generate-certificate \
	--load-privkey clientkey.pem \
	--load-ca-certificate cacert.pem \
	--load-ca-privkey cakey.pem \
	--template client.info \
	--outfile clientcert.pem

# Installing the certificate
if [ ! -d /etc/pki/libvirt ];
then
  mkdir /etc/pki/libvirt
fi
cp clientcert.pem /etc/pki/libvirt/clientcert.pem
if [ ! -d /etc/pki/libvirt/private ];
then
  mkdir /etc/pki/libvirt/private
fi 
cp clientkey.pem /etc/pki/libvirt/private/clientkey.pem

# Installing CA
if [ ! -d /etc/pki/CA ];
then
  mkdir /etc/pki/CA
fi
cp cacert.pem /etc/pki/CA/cacert.pem

