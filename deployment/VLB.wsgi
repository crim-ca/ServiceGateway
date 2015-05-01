import os
import sys

#The first dirname return the current directory,
#the second one will return the parent dir,
#which is the one we want in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from VestaLoadBalancer.simple_rest import APP as application
