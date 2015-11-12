import commands
import logging
import os

from django.db import models
from django.conf import settings

from cloud.models.base_model import BaseModel

# Get an instance of a logger
logger = logging.getLogger(__name__)

IMG_FORMATS = (
        (u'raw', u'Raw image (raw)'),
        (u'cow', u'User Mode Linux (cow)'),
        (u'qcow', u'QEMU v1 (qcow)'),
        (u'qcow2', u'QEMU v2 (qcow2)'),
        (u'vmdk', u'VMWare (vmdk)'),
        (u'vpc', u'VirtualPC (vpc)'),
        (u'iso', u'CDROM image (iso)'),
)

IMG_TARGETS = (
        (u'ide', u'IDE'),
        (u'scsi', u'SCSI'),
        (u'virtio', u'Virtio'),
        (u'xen', u'Xen'),
        (u'usb', u'USB'),
        (u'sata', u'SATA'),
)


class Image(BaseModel):
    name = models.CharField(max_length=200)
    file_format = models.CharField(
        max_length=10,
        choices=IMG_FORMATS,
        default='raw',
        db_index=True
    )
    target_dev = models.CharField(
        max_length=10,
        choices=IMG_TARGETS,
        default='virtio',
        db_index=True
    )
    description = models.TextField(blank=True, null=True)
    image_file = models.FileField(upload_to='images')

    # Deploys the image to a host based on the virtual machine object it 
    # is associated with
    def deploy(self, virtual_machine):
        # Create a copy of the VM disk
        disk_path = settings.REMOTE_IMAGE_PATH + self.image_file.name + "." + str(virtual_machine.id)

        # First sync the local image remotelly to speedup future copies
        # BUG: rsync will fail in case the host is not in the known_hosts file (for ssh we use StrictHostKeychecking)
        rsync_path = self.image_file.path.replace(self.image_file.name, './'+self.image_file.name)
        rsync_cmd = 'rsync --update --relative ' + rsync_path + ' ' + \
                    'root@' + virtual_machine.host.hostname + ':' + settings.REMOTE_IMAGE_PATH
        out = commands.getstatusoutput(rsync_cmd)
        if out[0] != 0:
            logger.warning(rsync_cmd)
            raise self.ImageException(
                "Could not copy image: " + out[1]
            )

        # Then copy the image for the virtual machine 
        copy_cmd = 'ssh -o StrictHostKeyChecking=no root@' + virtual_machine.host.hostname + ' ' + \
                   '"cp -f ' + settings.REMOTE_IMAGE_PATH + self.image_file.name + ' ' + disk_path + '"'
        out = commands.getstatusoutput(copy_cmd)
        if out[0] != 0:
            logger.warning(copy_cmd)
            raise self.ImageException(
                "Could not copy image: " + out[1]
            )
        return disk_path

    # Current size on disk of this image
    def get_size(self):
        return self.image_file.file.size

    def __unicode__(self):
        return self.name

    class ImageException(BaseModel.ModelException):
        pass
