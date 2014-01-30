from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('manager.views',
    #Virtual Machines
    url(r'^virtual_machines/$', 'virtual_machines.index',
        name='manager-virtual-machines-index'),
    url(r'^virtual_machines/new/$', 'virtual_machines.new'),
    url(r'^virtual_machines/sync/$', 'virtual_machines.sync'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/$',
        'virtual_machines.detail'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/start/$',
        'virtual_machines.start'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/stop/$',
        'virtual_machines.stop'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/shutdown/$',
        'virtual_machines.shutdown'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/resume/$',
        'virtual_machines.resume'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/suspend/$',
        'virtual_machines.suspend'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/delete/$',
        'virtual_machines.delete'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/migrate/$',
        'virtual_machines.migrate'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/xml/$',
        'virtual_machines.xml'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/console/$',
        'virtual_machines.console'),
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/interfaces/$',
        'virtual_machines.interfaces'),  # Webservice
    url(r'^virtual_machines/(?P<virtual_machine_id>\d+)/' +
        'new_virtual_interface/$', 'virtual_machines.new_virtual_interface'),

    #Devices (only webservices)
    url(r'^devices/(?P<device_type>\w+)/$', 'devices.devices'),  # Webservice
    url(r'^devices/(?P<device_id>\d+)/interfaces/$',
        'devices.interfaces'),  # Webservice

    #Hosts
    url(r'^hosts/$', 'hosts.index', name='manager-hosts-index'),
    url(r'^hosts/new/$', 'hosts.new'),
    url(r'^hosts/(?P<host_id>\d+)/$', 'hosts.detail'),
    url(r'^hosts/(?P<host_id>\d+)/xml/$', 'hosts.xml'),
    url(r'^hosts/(?P<host_id>\d+)/delete/$', 'hosts.delete'),
    url(r'^hosts/(?P<host_id>\d+)/new_interface/$', 'hosts.new_interface'),
    url(r'^hosts/list_infrastructure/$', 'hosts.list_infrastructure'),

    #Switches
    url(r'^switches/$', 'switches.index', name='manager-switches-index'),
    url(r'^switches/new/$', 'switches.new'),
    url(r'^switches/(?P<switch_id>\d+)/$', 'switches.detail'),
    url(r'^switches/(?P<switch_id>\d+)/delete/$', 'switches.delete'),
    url(r'^switches/(?P<switch_id>\d+)/new_port/$', 'switches.new_port'),
    url(r'^switches/(?P<switch_id>\d+)/connect_device/(?P<port_id>\d+)/$',
        'switches.connect_device'),

    #Images
    url(r'^images/$', 'images.index', name='manager-images-index'),
    url(r'^images/new/$', 'images.new'),
    url(r'^images/(?P<image_id>\d+)/$', 'images.detail'),
    url(r'^images/(?P<image_id>\d+)/delete/$', 'images.delete'),

    #Templates
    url(r'^templates/$', 'templates.index', name='manager-templates-index'),
    url(r'^templates/new/$', 'templates.new'),
    url(r'^templates/(?P<template_id>\d+)/$', 'templates.detail'),
    url(r'^templates/(?P<template_id>\d+)/delete/$', 'templates.delete'),

    #Virtual Links
    url(r'^virtual_links/$', 'virtual_links.index',
        name='manager-virtual-links-index'),
    url(r'^virtual_links/new/$', 'virtual_links.new'),
    url(r'^virtual_links/sync/$', 'virtual_links.sync'),
    url(r'^virtual_links/(?P<virtual_link_id>\d+)/$', 'virtual_links.detail'),
    url(r'^virtual_links/(?P<virtual_link_id>\d+)/delete/$',
        'virtual_links.delete'),

    #Virtual Routers
    url(r'^virtual_routers/$', 'virtual_routers.index',
        name='manager-virtual-routers-index'),
    url(r'^virtual_routers/new/$', 'virtual_routers.new'),
    url(r'^virtual_routers/(?P<virtual_router_id>\d+)/$',
        'virtual_routers.detail'),
    url(r'^virtual_routers/(?P<virtual_router_id>\d+)/delete/$',
        'virtual_routers.delete'),
    url(r'^virtual_routers/(?P<virtual_router_id>\d+)/new_remote_controller/$',
        'virtual_routers.new_remote_controller'),
    url(r'^virtual_routers/(?P<virtual_router_id>\d+)/new_virtual_interface/$',
        'virtual_routers.new_virtual_interface'),
    url(r'^virtual_routers/(?P<virtual_router_id>\d+)/' +
        'connect_virtual_device/(?P<virtual_interface_id>\d+)/$',
        'virtual_routers.connect_virtual_device'),

    #Virtual Devices (only webservices)
    url(r'^virtual_devices/(?P<virtual_device_type>\w+)/$',
        'virtual_devices.virtual_devices'),  # Webservice
    url(r'^virtual_devices/(?P<virtual_device_id>\d+)/virtual_interfaces/$',
        'virtual_devices.virtual_interfaces'),  # Webservice

    #Slices
    url(r'^slices/$', 'slices.index', name='manager-slices-index'),
    url(r'^slices/new/$', 'slices.new'),
    url(r'^slices/new_remote/$', 'slices.new_remote'),
    url(r'^slices/delete_remote/(?P<slice_name>[-\w]+)/$',
        'slices.delete_remote'),
    url(r'^slices/(?P<slice_id>\d+)/$', 'slices.detail'),
    url(r'^slices/(?P<slice_id>\d+)/deploy/$', 'slices.deploy'),
    url(r'^slices/(?P<slice_id>\d+)/delete/$', 'slices.delete'),
    url(r'^slices/(?P<slice_id>\d+)/add_optimization_program/$',
        'slices.add_optimization_program'),
    url(r'^slices/(?P<slice_id>\d+)/remove_optimization_program/' +
        '(?P<optimizes_id>\d+)/$', 'slices.remove_optimization_program'),
    url(r'^slices/export_all_flexcms/$', 'slices.export_all_flexcms'),

    #Gadgets
    url(r'^gadgets/resource_list/$', 'gadgets.resource_list'),
    url(r'^gadgets/virtual_resource_list/$', 'gadgets.virtual_resource_list'),
    url(r'^gadgets/aggregate_memory_usage/$', 'gadgets.aggregate_memory_usage'),
    url(r'^gadgets/aggregate_cpu_usage/$', 'gadgets.aggregate_cpu_usage'),

    #Programs
    url(r'^deployment_programs/$', 'deployment_programs.index',
        name='manager-deployment-programs-index'),
    url(r'^deployment_programs/new/$', 'deployment_programs.new'),
    url(r'^deployment_programs/(?P<deployment_program_id>\d+)/$',
        'deployment_programs.detail'),
    url(r'^deployment_programs/(?P<deployment_program_id>\d+)/delete/$',
        'deployment_programs.delete'),
    url(r'^optimization_programs/$', 'optimization_programs.index',
        name='manager-optimization-programs-index'),
    url(r'^optimization_programs/new/$', 'optimization_programs.new'),
    url(r'^optimization_programs/(?P<optimization_program_id>\d+)/$',
        'optimization_programs.detail'),
    url(r'^optimization_programs/(?P<optimization_program_id>\d+)/delete/$',
        'optimization_programs.delete'),
    url(r'^optimization_programs/ws/(?P<program_name>\w+)/$',
        'optimization_programs.web_services'),
    url(r'^metrics/$', 'metrics.index', name='manager-metrics-index'),
    url(r'^metrics/new/$', 'metrics.new'),
    url(r'^metrics/(?P<metric_id>\d+)/$', 'metrics.detail'),
    url(r'^metrics/(?P<metric_id>\d+)/delete/$', 'metrics.delete'),
    url(r'^metrics/ws/(?P<metric_name>\w+)/$', 'metrics.web_services'),
    url(r'^events/$', 'events.index', name='manager-events-index'),
    url(r'^events/new/$', 'events.new'),
    url(r'^events/(?P<event_id>\d+)/$', 'events.detail'),
    url(r'^events/(?P<event_id>\d+)/delete/$', 'events.delete'),

    #Monitoring
    url(r'^monitoring/settings/$', 'monitoring.settings',
        name='manager-monitoring-settings'),

)
