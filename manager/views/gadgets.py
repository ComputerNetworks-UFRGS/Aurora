from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from manager.models.host import Host
from manager.models.switch import Switch
from manager.models.router import Router
from manager.models.virtual_machine import VirtualMachine
from manager.models.virtual_link import VirtualLink
from manager.models.virtual_router import VirtualRouter

# Generates a list of physical resources available 
@login_required
def resource_list(request):
    
    total_hosts = Host.objects.count()
    total_switches = Switch.objects.count()
    total_routers = Router.objects.count()
    
    resource_list = [
        {"label": "Hosts", "count": total_hosts},
        {"label": "Switches", "count": total_switches},
        {"label": "Routers", "count": total_routers},
    ]
    c = RequestContext(request, {
        'resource_list': resource_list,
    })
    return render_to_response('gadgets-resource-list.html', c)

# Generates a list of virtual resources available 
@login_required
def virtual_resource_list(request):
    
    total_vms = VirtualMachine.objects.count()
    total_vlinks = VirtualLink.objects.count()
    total_vvolumes = 0
    total_vrouters = VirtualRouter.objects.count()
    
    resource_list = [
        {"label": "Virtual Machines", "count": total_vms},
        {"label": "Virtual Links", "count": total_vlinks},
        {"label": "Virtual Volumes", "count": total_vvolumes},
        {"label": "Virtual Routers", "count": total_vrouters},
    ]
    c = RequestContext(request, {
        'resource_list': resource_list,
    })
    return render_to_response('gadgets-resource-list.html', c)

# Calculates aggregate memory usage 
@login_required
def aggregate_memory_usage(request):
    
    total_total = total_cached = total_buffers = total_free = 0
    hosts = Host.objects.all()
    for h in hosts:
        stats = h.get_memory_stats()
        total_total += stats["total"]
        total_cached += stats["cached"]
        total_buffers += stats["buffers"]
        total_free += stats["free"]
    
    memory_stats = {
        "total": total_total,
        "cached": total_cached,
        "buffers": total_buffers,
        "free": total_free,
    }
    c = RequestContext(request, {
        'memory_stats': memory_stats,
    })
    return render_to_response('gadgets-aggregate-memory-usage.html', c)

# Calculates aggregate cpu usage 
@login_required
def aggregate_cpu_usage(request):
    
    total_kernel = total_idle = total_user = total_iowait = 0
    hosts = Host.objects.all()
    for h in hosts:
        stats = h.get_cpu_stats()
        total_kernel += stats["kernel"]
        total_idle += stats["idle"]
        total_user += stats["user"]
        total_iowait += stats["iowait"]
    
    cpu_stats = {
        "kernel": total_kernel,
        "idle": total_idle,
        "user": total_user,
        "iowait": total_iowait
    }
    
    c = RequestContext(request, {
        'cpu_stats': cpu_stats,
    })
    return render_to_response('gadgets-aggregate-cpu-usage.html', c)

