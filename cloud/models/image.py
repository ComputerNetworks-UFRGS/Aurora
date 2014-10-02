import commands
import logging
from django.db import models
import os
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
        disk_path = "/" + self.image_file.name + "." + str(virtual_machine.id)

        # First sync the local image remotelly to speedup future copies
        rsync_path = self.image_file.path.replace(self.image_file.name, './'+self.image_file.name)
        out = commands.getstatusoutput(
            'rsync --update --relative ' + rsync_path + ' ' +
            'root@' + virtual_machine.host.hostname + ':/'
        )
        if out[0] != 0:
            raise self.ImageException(
                "Could not copy image: " + out[1]
            )

        # Then copy the image for the virtual machine 
        out = commands.getstatusoutput(
            'ssh root@' + virtual_machine.host.hostname + ' ' + 
            '"cp -f /' + self.image_file.name + ' ' + disk_path + '"'
        )
        if out[0] != 0:
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
