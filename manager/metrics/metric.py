#Base class for metrics
from abc import ABCMeta

class Metric():
    # Prevents instantiation of this class (abstract)
    __metaclass__ = ABCMeta

    # Only to obligate the implementation of this method
    def collect(self):
        raise NotImplementedError( "Should have implemented this" )
    
    # Exception to throw when there is problems collecting a metric
    class MetricException(Exception):
        def __init__(self, msg):
            self.msg = msg
        def __str__(self):
            return str(self.msg)
