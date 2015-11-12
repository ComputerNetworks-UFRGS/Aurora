# Create initial load for experiment

# Run this script from the django shell:
# python manage.py shell
# from scripts.create_load import create_load 
# create_load()

from django.contrib.auth.models import User
from cloud.models.slice import Slice
from cloud.programs.DeployRandom import DeployRandom
from cloud.models.deployment_program import DeploymentProgram

def create_load():
    deployments = 5
    files = [
        'cloud/templates/xml/vxdl_tese_netinf.xml',
        'cloud/templates/xml/vxdl_tese_loop_4.xml',
        'cloud/templates/xml/vxdl_tese_tree_7.xml',
        'cloud/templates/xml/vxdl_tese_tree_15.xml'
    ]
    # Slice name prefix
    names = [ 'NI', 'LP', 'T7', 'T15' ]

    for i in range(deployments):
        # Load VXDL from file
        index = 0
        for fname in files:
            f = open(fname, 'r')
            vxdl = f.read()
            f.close()

            s = Slice()
            s.name = names[index] + str(i+1).zfill(2)
            s.owner = User.objects.all()[0]
            s.save_from_vxdl(vxdl)

            print 'Slice saved: %s' % str(s)

            program = DeployRandom()
            if program.deploy(s):
                s.state = "deployed"
                s.deployed_with = DeploymentProgram.objects.get(name="DeployRandom")
                s.save()
                print 'Slice deployed: %s' % str(s)

            index += 1
