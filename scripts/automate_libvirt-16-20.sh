#!/bin/bash

for ((  i = 18 ;  i <= 20;  i++  ))
do
  # Compiling libvirt
  cd ~/libvirt-16-20/libvirt-1.0.0
  echo "##### Installing libvirt for host $i #####"
  ./configure --quiet --with-selinux=no --with-vbox=no --with-vmware=no --with-parallels=no --with-openvz=no --prefix=/usr/local/libvirt/h$i 
  make 
  make install

  # Generate certificates
  # Copy authority
  cd ~/cert
  if [ ! -d /usr/local/libvirt/h$i/etc/pki ];
  then
    mkdir /usr/local/libvirt/h$i/etc/pki
  fi
  if [ ! -d /usr/local/libvirt/h$i/etc/pki/CA ];
  then
    mkdir /usr/local/libvirt/h$i/etc/pki/CA
  fi
  cp cacert.pem /usr/local/libvirt/h$i/etc/pki/CA
  # Server certificate
  echo "##### Creating certificates for host $i #####"
  echo -e "organization = UFRGS (test server)\ncn = h$i\ntls_www_server\nencryption_key\nsigning_key" > h$i-server.info
  certtool --generate-privkey > h$i-server_key.pem
  certtool --generate-certificate \
            --template h$i-server.info \
            --load-privkey h$i-server_key.pem \
            --load-ca-certificate cacert.pem \
            --load-ca-privkey cakey.pem \
            --outfile h$i-server_certificate.pem

  if [ ! -d /usr/local/libvirt/h$i/etc/pki/libvirt ];
  then
    mkdir /usr/local/libvirt/h$i/etc/pki/libvirt
  fi
  cp h$i-server_certificate.pem /usr/local/libvirt/h$i/etc/pki/libvirt/servercert.pem
  if [ ! -d /usr/local/libvirt/h$i/etc/pki/libvirt/private ];
  then
    mkdir /usr/local/libvirt/h$i/etc/pki/libvirt/private
  fi 
  cp h$i-server_key.pem /usr/local/libvirt/h$i/etc/pki/libvirt/private/serverkey.pem

  # Configure libvirtd.conf
  echo "listen_tls = 1" > /usr/local/libvirt/h$i/etc/libvirt/libvirtd.conf
  echo "listen_tcp = 1" >> /usr/local/libvirt/h$i/etc/libvirt/libvirtd.conf
  echo "tcp_auth = \"none\"" >> /usr/local/libvirt/h$i/etc/libvirt/libvirtd.conf
  echo "key_file = \"/usr/local/libvirt/h$i/etc/pki/libvirt/private/serverkey.pem\"" >> /usr/local/libvirt/h$i/etc/libvirt/libvirtd.conf
  echo "cert_file = \"/usr/local/libvirt/h$i/etc/pki/libvirt/servercert.pem\"" >> /usr/local/libvirt/h$i/etc/libvirt/libvirtd.conf
  echo "ca_file = \"/usr/local/libvirt/h$i/etc/pki/CA/cacert.pem\"" >> /usr/local/libvirt/h$i/etc/libvirt/libvirtd.conf
  # Create alias for easy starting the daemons
  cd /usr/local/sbin
  ln -s ../libvirt/h$i/sbin/libvirtd libvirtd-h$i
  # Remove autostart NAT network (not needed in the platform)
  rm /usr/local/libvirt/h$i/etc/libvirt/qemu/networks/autostart/default.xml
done
