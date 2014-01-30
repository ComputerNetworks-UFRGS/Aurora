# Run this script from the django shell:
#
# python manage.py shell
# from scripts.experiment_im2013_loop4 import Experiment
# e = Experiment()
# e.run()

import time
import logging
from manager.models.slice import Slice
from django.contrib.auth.models import User
from manager.programs.deploy_balanced import DeployBalanced

# Configure logging for the module name
logger = logging.getLogger(__name__)

class Experiment():
    iterations = 30
    vxdl_file = "manager/templates/xml/vxdl_im_loop_4.xml"

    def run(self):
        
        logger.info("##### EXPERIMENT STARTING #####")
        begin_time = time.time()

        print "Running experiment for %i times" % self.iterations

        # Read VXDL
        f = open(self.vxdl_file, "r")
        vxdl = f.read()
        user = User.objects.all()[0] # Get any user, this really doesn't matter

        for i in range(self.iterations):
            
            print "Creating slice %i" % i

            s = Slice()
            s.owner = user
            s.name = "exp_loop4_" + str(i)
            try:
                s.save_from_vxdl(vxdl)
                print "Slice %s saved!" % s.name
            except Slice.VXDLException as e:
                print "Problems saving slice %s from VXDL!" % s.name

            try:
                program = DeployBalanced()
                # Will record deployment time
                t0 = time.time()
                if program.deploy(s):
                    deployment_time = time.time() - t0
                    s.state = "deployed"
                    s.save()
                    print "Slice %s successfully deployed in %s seconds!" % (s.name, str(round(deployment_time, 2)))
            except program.DeploymentException as e:
                print "Problems deploying slice %s: %s" % (s.name, str(e))

            print "Deleting slice %i" % i

            # List of VMs to delete 
            vms = s.virtualmachine_set.all()
            for vm in vms:
                try:
                    vm.undeploy()
                except vm.VirtualMachineException as e:
                    print "Problems undeploying a virtual machine: " + str(e)

            # List of Links to delete 
            links = s.virtuallink_set.all()
            for link in links:
                try:
                    link.unestablish()
                except link.VirtualLinkException as e:
                    print "Problems unestablishing a virtual link: " + str(e)

            s.delete()

        experiment_time = time.time() - begin_time
        logger.info("##### EXPERIMENT ENDED IN %s SECONDS #####" % str(round(experiment_time, 2)))

