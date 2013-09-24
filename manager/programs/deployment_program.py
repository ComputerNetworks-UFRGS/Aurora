#Base class for deployment programs
from abc import ABCMeta

class DeploymentProgram():
    # Prevents instantiation of this class (abstract)
    __metaclass__ = ABCMeta
    
    # Only to obligate the implementation of this method
    def deploy(self):
        raise NotImplementedError( "Should have implemented this" )
    
    # Exception to throw when there is problems with the VXDL input file
    # (should roll back the whole slice creation)
    class DeploymentException(Exception):
        def __init__(self, msg):
            self.msg = msg
        def __str__(self):
            return repr(self.msg)
