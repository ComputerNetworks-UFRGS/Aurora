#!/bin/bash

# Generate Certificate Authority
if [ ! -d ~/.cert ];
then
  mkdir ~/.cert
fi

cd ~/.cert
certtool --generate-privkey > cakey.pem
echo -e "cn = UFRGS (self-signed)\nca\ncert_signing_key" > ca.info
certtool --generate-self-signed --load-privkey cakey.pem --template ca.info --outfile cacert.pem

if [ ! -d /etc/pki ];
then
  mkdir /etc/pki
fi
if [ ! -d /etc/pki/CA ];
then
  mkdir /etc/pki/CA
fi
cp cacert.pem /etc/pki/CA
