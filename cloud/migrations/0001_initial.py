# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=200)),
                ('description', models.TextField(null=True, blank=True)),
                ('state', models.CharField(default=b'enabled', max_length=10, db_index=True, choices=[('enabled', 'Enabled'), ('disabled', 'Disabled')])),
                ('relational_operation', models.CharField(default=b'eq', max_length=10, db_index=True, choices=[('eq', '(=) Equals'), ('gt', '(>) Greater Than'), ('eqgt', ' (>=) Equals or Greater Than'), ('lt', '(<) Less Than'), ('eqlt', '(<=) Equals or Less Than'), ('diff', '(!=) Different')])),
                ('value', models.CharField(unique=True, max_length=200)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('file_format', models.CharField(default=b'raw', max_length=10, db_index=True, choices=[('raw', 'Raw image (raw)'), ('cow', 'User Mode Linux (cow)'), ('qcow', 'QEMU v1 (qcow)'), ('qcow2', 'QEMU v2 (qcow2)'), ('vmdk', 'VMWare (vmdk)'), ('vpc', 'VirtualPC (vpc)'), ('iso', 'CDROM image (iso)')])),
                ('target_dev', models.CharField(default=b'virtio', max_length=10, db_index=True, choices=[('ide', 'IDE'), ('scsi', 'SCSI'), ('virtio', 'Virtio'), ('xen', 'Xen'), ('usb', 'USB'), ('sata', 'SATA')])),
                ('description', models.TextField(null=True, blank=True)),
                ('image_file', models.FileField(upload_to=b'images')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Interface',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('alias', models.CharField(max_length=20)),
                ('if_type', models.CharField(default=b'ethernet', max_length=10, db_index=True, choices=[('ethernet', 'Ethernet')])),
                ('uplink_speed', models.PositiveIntegerField()),
                ('downlink_speed', models.PositiveIntegerField()),
                ('duplex', models.CharField(default=b'full', max_length=10, db_index=True, choices=[('full', 'Full Duplex'), ('half', 'Half Duplex')])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Metric',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=200)),
                ('description', models.TextField(null=True, blank=True)),
                ('file', models.FileField(upload_to=b'metrics')),
                ('returns', models.CharField(default=b'number', max_length=10, db_index=True, choices=[('counter', 'Counter'), ('number', 'Number'), ('text', 'Text'), ('object', 'Object')])),
                ('state', models.CharField(default=b'enabled', max_length=10, db_index=True, choices=[('enabled', 'Enabled'), ('disabled', 'Disabled')])),
                ('scope', models.CharField(default=b'infra', max_length=10, db_index=True, choices=[('slice', 'Slice specific'), ('infra', 'Infrastructure')])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Monitoring',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'Generic Monitoring System', max_length=100)),
                ('hostname', models.CharField(default=b'www.example-monitoring.com', max_length=200)),
                ('path', models.CharField(default=b'/deploy', max_length=200)),
                ('username', models.CharField(default=b'', max_length=100)),
                ('password', models.CharField(default=b'', max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='OptimizesSlice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('priority', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Port',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('alias', models.CharField(max_length=20)),
                ('uplink_speed', models.PositiveIntegerField()),
                ('downlink_speed', models.PositiveIntegerField()),
                ('duplex', models.CharField(default=b'full', max_length=10, db_index=True, choices=[('full', 'Full Duplex'), ('half', 'Half Duplex')])),
                ('connected_interfaces', models.ManyToManyField(to='cloud.Interface', verbose_name=b'Connected interfaces')),
                ('connected_ports', models.ManyToManyField(to='cloud.Port', verbose_name=b'Connected ports')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=200)),
                ('description', models.TextField(null=True, blank=True)),
                ('file', models.FileField(upload_to=b'programs')),
                ('state', models.CharField(default=b'enabled', max_length=10, db_index=True, choices=[('enabled', 'Enabled'), ('disabled', 'Disabled')])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RemoteController',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ip', models.CharField(max_length=100)),
                ('port', models.CharField(max_length=6)),
                ('connection', models.CharField(default=b'tcp', max_length=10, db_index=True, choices=[('tcp', 'TCP'), ('udp', 'UDP'), ('ptcp', 'PTCP')])),
                ('controller_type', models.CharField(default=b'master', max_length=10, db_index=True, choices=[('master', 'Master'), ('slave', 'Slave')])),
            ],
        ),
        migrations.CreateModel(
            name='Slice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('state', models.CharField(default=b'created', max_length=10, db_index=True, choices=[('created', 'Created'), ('deploying', 'Deploying'), ('deployed', 'Deployed'), ('optimizing', 'Optimizing'), ('disabled', 'Disabled')])),
                ('owner', models.ForeignKey(verbose_name=b'Slice Owner', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Template',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('memory', models.PositiveIntegerField()),
                ('vcpu', models.PositiveIntegerField()),
                ('description', models.TextField(null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='VirtualDevice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='VirtualInterface',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('alias', models.CharField(max_length=20)),
                ('if_type', models.CharField(default=b'bridge', max_length=10, db_index=True, choices=[('bridge', 'Bridge'), ('network', 'NAT'), ('ethernet', 'Ethernet')])),
                ('mac_address', models.CharField(max_length=17, null=True, blank=True)),
                ('source', models.CharField(max_length=200, null=True, blank=True)),
                ('target', models.CharField(max_length=200, null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='VirtualLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('state', models.CharField(default=b'created', max_length=10, db_index=True, choices=[('created', 'Created'), ('waiting', 'Waiting'), ('establish', 'Established'), ('inactive', 'Inactive'), ('failed', 'Failed')])),
                ('path', models.TextField(null=True, blank=True)),
                ('belongs_to_slice', models.ForeignKey(blank=True, to='cloud.Slice', null=True)),
                ('if_end', models.ForeignKey(related_name='virtuallink_set_end', verbose_name=b'Link end', to='cloud.VirtualInterface')),
                ('if_start', models.ForeignKey(related_name='virtuallink_set_start', verbose_name=b'Link start', to='cloud.VirtualInterface')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='VirtualLinkQos',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('bandwidth_up_maximum', models.IntegerField()),
                ('bandwidth_up_committed', models.IntegerField()),
                ('bandwidth_down_maximum', models.IntegerField()),
                ('bandwidth_down_committed', models.IntegerField()),
                ('latency', models.IntegerField()),
                ('belongs_to_virtual_link', models.OneToOneField(to='cloud.VirtualLink')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='VirtualPort',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('alias', models.CharField(max_length=20)),
                ('if_type', models.CharField(default=b'bridge', max_length=10, db_index=True, choices=[('bridge', 'Bridge')])),
                ('mac_address', models.CharField(max_length=17, null=True, blank=True)),
                ('source', models.CharField(max_length=200, null=True, blank=True)),
                ('target', models.CharField(max_length=200, null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DeploymentProgram',
            fields=[
                ('program_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cloud.Program')),
            ],
            options={
                'abstract': False,
            },
            bases=('cloud.program',),
        ),
        migrations.CreateModel(
            name='Host',
            fields=[
                ('device_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cloud.Device')),
                ('driver', models.CharField(default=b'qemu', max_length=10, db_index=True, choices=[('remote', 'Default (remote)'), ('qemu', 'QEMU/KVM'), ('lxc', 'LXC'), ('xen', 'XEN'), ('vbox', 'VirtualBox'), ('vmware', 'VMWare')])),
                ('transport', models.CharField(default=b'tls', max_length=10, db_index=True, choices=[('tls', 'SSL/TLS'), ('ssh', 'SSH'), ('unix', 'Unix'), ('ext', 'External'), ('tcp', 'TCP (Unencrypted)'), ('local', 'Local Connection')])),
                ('username', models.CharField(max_length=100, null=True, blank=True)),
                ('password', models.CharField(max_length=100, null=True, blank=True)),
                ('hostname', models.CharField(default=b'localhost', max_length=200)),
                ('port', models.PositiveIntegerField(null=True, blank=True)),
                ('path', models.CharField(max_length=200, null=True, blank=True)),
                ('extraparameters', models.CharField(max_length=200, null=True, blank=True)),
                ('ovsdb', models.CharField(default=b'unix:/var/run/openvswitch/db.sock', max_length=200)),
            ],
            options={
                'abstract': False,
            },
            bases=('cloud.device',),
        ),
        migrations.CreateModel(
            name='OptimizationProgram',
            fields=[
                ('program_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cloud.Program')),
                ('scope', models.CharField(default=b'global', max_length=10, db_index=True, choices=[('slice', 'Slice specific'), ('global', 'Global')])),
            ],
            options={
                'abstract': False,
            },
            bases=('cloud.program',),
        ),
        migrations.CreateModel(
            name='Router',
            fields=[
                ('device_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cloud.Device')),
                ('hostname', models.CharField(max_length=200)),
                ('rt_type', models.CharField(default=b'router', max_length=10, db_index=True, choices=[('router', 'IP Router')])),
            ],
            options={
                'abstract': False,
            },
            bases=('cloud.device',),
        ),
        migrations.CreateModel(
            name='Switch',
            fields=[
                ('device_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cloud.Device')),
                ('hostname', models.CharField(max_length=200)),
                ('sw_type', models.CharField(default=b'ethernet', max_length=10, db_index=True, choices=[('ethernet', 'Ethernet Switch'), ('openflow', 'Openflow Switch')])),
            ],
            options={
                'abstract': False,
            },
            bases=('cloud.device',),
        ),
        migrations.CreateModel(
            name='VirtualMachine',
            fields=[
                ('virtualdevice_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cloud.VirtualDevice')),
                ('driver', models.CharField(default=b'remote', max_length=10, db_index=True, choices=[('remote', 'Default (remote)'), ('qemu', 'QEMU/KVM'), ('xen', 'XEN'), ('vbox', 'VirtualBox'), ('vmware', 'VMWare')])),
                ('memory', models.PositiveIntegerField()),
                ('vcpu', models.PositiveIntegerField()),
                ('feature_acpi', models.BooleanField(default=False)),
                ('feature_apic', models.BooleanField(default=False)),
                ('feature_pae', models.BooleanField(default=False)),
                ('clock', models.CharField(max_length=10)),
                ('disk_path', models.CharField(max_length=200, null=True, blank=True)),
                ('host', models.ForeignKey(verbose_name=b'Connected to', blank=True, to='cloud.Host', null=True)),
                ('image', models.ForeignKey(verbose_name=b'Base image', blank=True, to='cloud.Image', null=True)),
            ],
            bases=('cloud.virtualdevice',),
        ),
        migrations.CreateModel(
            name='VirtualRouter',
            fields=[
                ('virtualdevice_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cloud.VirtualDevice')),
                ('cp_routing_protocol', models.CharField(default=b'openflow', max_length=10, db_index=True, choices=[('openflow', 'OpenFlow'), ('bgp', 'BGP'), ('ospf', 'OSPF'), ('rip', 'RIP')])),
                ('cp_type', models.CharField(default=b'dynamic', max_length=10, db_index=True, choices=[('dynamic', 'Dynamic'), ('static', 'Static')])),
                ('dev_name', models.CharField(max_length=15, db_index=True)),
                ('host', models.ForeignKey(verbose_name=b'Connected to', blank=True, to='cloud.Host', null=True)),
            ],
            bases=('cloud.virtualdevice',),
        ),
        migrations.AddField(
            model_name='virtualinterface',
            name='attached_to',
            field=models.ForeignKey(verbose_name=b'Attached to', to='cloud.VirtualDevice'),
        ),
        migrations.AddField(
            model_name='virtualdevice',
            name='belongs_to_slice',
            field=models.ForeignKey(blank=True, to='cloud.Slice', null=True),
        ),
        migrations.AddField(
            model_name='remotecontroller',
            name='belongs_to_slice',
            field=models.ForeignKey(blank=True, to='cloud.Slice', null=True),
        ),
        migrations.AddField(
            model_name='optimizesslice',
            name='slice',
            field=models.ForeignKey(to='cloud.Slice'),
        ),
        migrations.AddField(
            model_name='event',
            name='belongs_to_slice',
            field=models.ForeignKey(blank=True, to='cloud.Slice', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='metric',
            field=models.ForeignKey(to='cloud.Metric'),
        ),
        migrations.AddField(
            model_name='virtualport',
            name='attached_to',
            field=models.ForeignKey(verbose_name=b'Attached to', to='cloud.VirtualRouter'),
        ),
        migrations.AddField(
            model_name='slice',
            name='deployed_with',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name=b'Deployed with program', to='cloud.DeploymentProgram', null=True),
        ),
        migrations.AddField(
            model_name='slice',
            name='optimized_by',
            field=models.ManyToManyField(to='cloud.OptimizationProgram', verbose_name=b'Optimized by', through='cloud.OptimizesSlice'),
        ),
        migrations.AddField(
            model_name='remotecontroller',
            name='controls_vrouter',
            field=models.ForeignKey(to='cloud.VirtualRouter'),
        ),
        migrations.AddField(
            model_name='port',
            name='switch',
            field=models.ForeignKey(verbose_name=b'Attached to', to='cloud.Switch'),
        ),
        migrations.AddField(
            model_name='optimizesslice',
            name='program',
            field=models.ForeignKey(to='cloud.OptimizationProgram'),
        ),
        migrations.AddField(
            model_name='interface',
            name='attached_to',
            field=models.ForeignKey(verbose_name=b'Attached to', to='cloud.Host'),
        ),
        migrations.AddField(
            model_name='event',
            name='program',
            field=models.ForeignKey(to='cloud.OptimizationProgram'),
        ),
    ]
