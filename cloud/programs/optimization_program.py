#Base class for optimization programs
from abc import ABCMeta

class OptimizationProgram():
    # Prevents instantiation of this class (abstract)
    __metaclass__ = ABCMeta

    # Only to obligate the implementation of this method
    def optimize(self):
        raise NotImplementedError( "Should have implemented this" )
    
    # Only to obligate the implementation of this method
    def event_listener(self):
        raise NotImplementedError( "Should have implemented this" )

    # Exception to throw when there is problems optimizing a slice
    class OptimizationException(Exception):
        def __init__(self, msg):
            self.msg = msg
        def __str__(self):
            return repr(self.msg)
