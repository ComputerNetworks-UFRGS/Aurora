#!/bin/bash

if [ ! $# -eq 2 ];
then
    echo "Invalid number of arguiments"
    echo -e "\n\tUsage: compile_libvirt.sh SOURCE_DIR INSTALL_PATH (e.g., /usr/local)\n"
    exit
fi

SOURCE_DIR=$1
INSTALL_PATH=$2

if [ ! -d $SOURCE_DIR ];
then
    echo "Source directory not found"
    exit
fi

cd $SOURCE_DIR
./configure --quiet --with-selinux=no --with-selinux-mount=no --with-xen=no --with-xen-inotify=no --with-uml=no --with-openvz=no --with-vmware=no --with-phyp=no --with-xenapi=no --with-libxl=no --with-vbox=no --with-lxc=no --with-esx=no --with-hyperv=no --prefix=$INSTALL_PATH 
make 
make install

# Configure libvirtd.conf
HOSTUUID=`uuidgen`
echo "listen_tls = 1" > $INSTALL_PATH/etc/libvirt/libvirtd.conf
echo "listen_tcp = 1" >> $INSTALL_PATH/etc/libvirt/libvirtd.conf
echo "tcp_auth = \"none\"" >> $INSTALL_PATH/etc/libvirt/libvirtd.conf
echo "key_file = \"$INSTALL_PATH/etc/pki/libvirt/private/serverkey.pem\"" >> $INSTALL_PATH/etc/libvirt/libvirtd.conf
echo "cert_file = \"$INSTALL_PATH/etc/pki/libvirt/servercert.pem\"" >> $INSTALL_PATH/etc/libvirt/libvirtd.conf
echo "ca_file = \"$INSTALL_PATH/etc/pki/CA/cacert.pem\"" >> $INSTALL_PATH/etc/libvirt/libvirtd.conf
echo "host_uuid = \"$HOSTUUID\"" >> $INSTALL_PATH/etc/libvirt/libvirtd.conf

# Configure qemu.conf
echo "cgroup_device_acl = [" > $INSTALL_PATH/etc/libvirt/qemu.conf
echo "    \"/dev/null\", \"/dev/full\", \"/dev/zero\"," >> $INSTALL_PATH/etc/libvirt/qemu.conf
echo "    \"/dev/random\", \"/dev/urandom\"," >> $INSTALL_PATH/etc/libvirt/qemu.conf
echo "    \"/dev/ptmx\", \"/dev/kvm\", \"/dev/kqemu\"," >> $INSTALL_PATH/etc/libvirt/qemu.conf
echo "    \"/dev/rtc\", \"/dev/hpet\", \"/dev/vfio/vfio\", \"/dev/net/tun\"" >> $INSTALL_PATH/etc/libvirt/qemu.conf
echo "]" >> $INSTALL_PATH/etc/libvirt/qemu.conf
echo "user = \"root\"" >> $INSTALL_PATH/etc/libvirt/qemu.conf
echo "group = \"root\"" >> $INSTALL_PATH/etc/libvirt/qemu.conf
echo "clear_emulator_capabilities = 0" >> $INSTALL_PATH/etc/libvirt/qemu.conf


# Remove autostart NAT network (not needed in the platform)
rm $INSTALL_PATH/etc/libvirt/qemu/networks/autostart/default.xml

# Remove source dir
rm -rf $SOURCE_DIR
