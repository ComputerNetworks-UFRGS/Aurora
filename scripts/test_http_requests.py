import json, httplib, urllib

def try_get():
    headers = {"Content-type": "application/json"}
    conn = httplib.HTTPConnection("localhost", 8000)
    conn.request("GET", "/manager/link/state/1", "", headers)
    response = conn.getresponse()
    json_data = response.read()
    conn.close()
    print "Response: %s %s - Data: %s" % (response.status, response.reason, json_data)
    
def try_put():
    link_info = {
        'id': 1,
        'mac_start': '00:00:00:00:00:01',
        'mac_end': '00:00:00:00:00:02'
    }
    json_link = json.dumps(link_info)
    headers = {"Content-type": "application/json"}
    conn = httplib.HTTPConnection("localhost", 8000)
    conn.request("PUT", "/manager/link/create/1", json_link, headers)
    response = conn.getresponse()
    json_data = response.read()
    conn.close()
    print "Response: %s %s - Data: %s" % (response.status, response.reason, json_data)


def try_post():
    with file("vxdl_slice_10_vms_only.xml") as f:
        contents = f.read()
    params = urllib.urlencode({'name': 'TestPost', 'vxdl_file': contents})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    conn = httplib.HTTPSConnection("aurora.inf.ufrgs.br")
    conn.request("POST", "/Aurora/manager/slices/new_remote/", params, headers)
    response = conn.getresponse()
    print response.status, response.reason

    data = response.read()
    print data

    conn.close()

if __name__ == '__main__':
    #print "Testing GET"
    #try_get()
    print "Testing POST"
    try_post()
    #print "Testing PUT"
    #try_put()

