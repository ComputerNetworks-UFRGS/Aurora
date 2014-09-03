'''
Created on Dec 8, 2011

@author: araujo
'''

from models.virtual_machine import VirtualMachine
from models.host import Host
from models.image import Image
from models.template import Template
from django.contrib import admin

admin.site.register(VirtualMachine)
admin.site.register(Host)
admin.site.register(Image)
admin.site.register(Template)
