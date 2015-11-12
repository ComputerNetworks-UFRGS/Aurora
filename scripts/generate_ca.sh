#!/bin/bash

# Generate Certificate Authority
if [ ! -d ~/.cert ];
then
    mkdir ~/.cert
fi

cd ~/.cert

if [ ! -f cakey.pem ];
then
    certtool --generate-privkey > cakey.pem
fi

if [ -f cacert.pem ];
then
    echo "A certificate (cacert.pem) file already exists. "
    while true; do
        read -p "Would you like to create a new one? (yes or no) " yn
        case $yn in
            [Yy]* ) echo -e "cn = UFRGS (self-signed)\nca\ncert_signing_key\nexpiration_days=3650" > ca.info;
                    certtool --generate-self-signed --load-privkey cakey.pem --template ca.info --outfile cacert.pem;
                    break
                    ;;
            [Nn]* ) exit;;
            * ) echo "Please answer yes or no.";;
        esac
  done
fi

if [ ! -d /etc/pki ];
then
  mkdir /etc/pki
fi
if [ ! -d /etc/pki/CA ];
then
  mkdir /etc/pki/CA
fi
cp cacert.pem /etc/pki/CA
