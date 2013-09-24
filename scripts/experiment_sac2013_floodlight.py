# Run this script from the django shell:
#
# python manage.py shell
# from scripts.experiment_sac2013_floodlight import Experiment
# e = Experiment()
# e.run()

import time
import logging
import json, httplib

# Configure logging for the module name
logger = logging.getLogger("Aurora")

class StaticFlowPusher(object):

    def __init__(self, server):
        self.server = server

    def get(self, data):
        ret = self.rest_call({}, 'GET')
        return json.loads(ret[2])

    def set(self, data):
        ret = self.rest_call(data, 'POST')
        return ret[0] == 200

    def remove(self, data):
        ret = self.rest_call(data, 'DELETE')
        return ret[0] == 200

    def list(self, switch):
        ret = self.rest_call({}, 'GET', "/wm/staticflowentrypusher/list/" + switch + "/json")
        return json.loads(ret[2])

    def switch_desc(self):
        ret = self.rest_call({}, 'GET', "/wm/core/switch/all/desc/json")
        return json.loads(ret[2])

    def rest_call(self, data, action, path = None):

        if path == None:
            path = '/wm/staticflowentrypusher/json'

        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            }
        body = json.dumps(data)
        conn = httplib.HTTPConnection(self.server, 8080)
        conn.request(action, path, body, headers)
        response = conn.getresponse()
        ret = (response.status, response.reason, response.read())
        #print ret
        conn.close()
        return ret

class Experiment():
    iterations = 30

    def run(self):

        pusher = StaticFlowPusher('143.54.12.40')

        # List switches
        switches = pusher.switch_desc()

        # Get the first one
        for i in switches:
            sw = i
            break
        
        logger.info("##### EXPERIMENT STARTING #####")
        begin_time = time.time()

        print "Running experiment for %i times" % self.iterations

        insert_time = 0
        list_time = 0
        remove_time = 0
        for i in range(self.iterations):
            
            # Insert flow on switch
            # Variar o name
            # Criar todos macs diferente (src-mac)
            # curl -d '{"switch": "00:00:da:61:5c:79:1f:4e", "name":"flow-mod-1", "cookie":"0", "priority":"32768", "ingress-port":"2","active":"true", "actions":"output=1"}' http://julianolo.provinet.local:8080/wm/staticflowentrypusher/json
            print "Inserting flow %i on controller" % i
            flow_info = {
                "switch": sw,
                "name": "flow-mod-" + str(i), 
                "cookie": "0", 
                "priority": "32768", 
                "src-mac": "00:00:00:00:00:" + str(i).zfill(2),
                "active": "true", 
                "actions": "output=1"
            }
            t0 = time.time()
            p = pusher.set(flow_info)
            t1 = time.time()
            insert_time += t1 - t0
            
            if p:
                print "Flow %i installed in %s seconds" % (i, str(t1 - t0))

            # List flows
            # /wm/staticflowentrypusher/list/<switch>/json
            print "List flows on controller"
            t0 = time.time()
            flows = pusher.list(sw)
            t1 = time.time()
            list_time += t1 - t0
            print "%i flows found on controller in %s seconds" % (len(flows[sw]), str(t1 - t0))

        for i in range(self.iterations):
            # Delete flow
            # Pelo name
            # curl -X DELETE -d '{"name":"flow-mod-1"}' http://<controller_ip>:8080/wm/staticflowentrypusher/json
            print "Removing flow %i on controller" % i
            flow_info = {
                "switch": sw,
                "name": "flow-mod-" + str(i)
            }
            t0 = time.time()
            r = pusher.remove(flow_info)
            t1 = time.time()
            remove_time += t1 - t0
            if r:
                print "Flow %i removed in %s seconds" % (i, str(t1 - t0))

        experiment_time = time.time() - begin_time
        print "Insert time %s (avg. %s)" % (str(insert_time), str(insert_time/self.iterations))
        print "List time %s (avg. %s)" % (str(list_time), str(list_time/self.iterations))
        print "Remove time %s (avg. %s)" % (str(remove_time), str(remove_time/self.iterations))
        logger.info("##### EXPERIMENT ENDED IN %s SECONDS #####" % str(round(experiment_time, 2)))

