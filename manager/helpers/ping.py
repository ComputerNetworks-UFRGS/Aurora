import os
import time
import sys


if sys.platform.startswith("win32"):
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
    # Extra ping options on windows
    count_option = "-n"
    extra_options = ""
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time
    # Extra ping options on linux
    count_option = "-c"
    # -A: takes delay off
    # -q: makes it quiet
    extra_options = "-A -q"

class Ping(object):
    def __init__(self, destination, timeout=1000):
        self.destination = destination
        self.timeout = timeout

    def run(self, count=3):
        if count < 1:
            count = 3
        try:
            t0 = default_timer()
            code = os.system("ping "+ self.destination + " " + extra_options + " " + count_option + " " + str(count))
            if code != 0:
                raise Exception("Problems pinging: [Errno " + str(code) + "]")
            return (default_timer() - t0) / count
        except Exception as e:
            raise Exception("Problems pinging: " + str(e))
        
