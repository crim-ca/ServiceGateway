#!/usr/bin/env python
# coding: utf-8

"""
Contains information on created VM and cloud mgmt interfaces
"""

import threading
import logging


class VM(object):
    """
    A class for storing created VM information. Used to populate Cluster
    classes 'vms' lists.

    Instance Variables

    The global VM states are:
       Starting - The VM is being created in the cloud
       Running  - The VM is running somewhere on the cloud (fully functional)
       Error    - The VM has been corrupted or is in the process of being
                  destroyed

    States are defined in each Cluster subclass, in which a VM_STATES
    dictionary maps specific cloud software state to these global states.
    """

    def __init__(self, name="", id_="", vmtype="", user="",
                 hostname="", ipaddress="", clusteraddr="", clusterport="",
                 cloudtype="", network="public", cpuarch="x86",
                 image="", memory=0, mementry=0,
                 cpucores=0, storage=0, keep_alive=0, spot_id="",
                 proxy_file=None, myproxy_creds_name=None, myproxy_server=None,
                 myproxy_server_port=None,
                 myproxy_renew_time="12", job_per_core=False):
        """
        Constructor

        name         - (str) The name of the vm (arbitrary)
        id_          - (str) The id_ tag for the VM. Whatever is used to access
                       the vm by cloud software (Nimbus: epr file. OpenNebula:
                       id_ number, etc.)
        vmtype       - (str) The condor VMType attribute for the VM
        user         - (str) The user who 'owns' this VM
        uservmtype   - (str) Aggregate type in form 'user:vmtype'
        hostname     - (str) The first part of hostname given to VM
        ipaddress    - (str) The IP Address of the VM
        condorname   - (str) The name of the VM as it's registered with Condor
        condoraddr   - (str) The Address of the VM as it's registered with
                       Condor
        clusteraddr  - (str) The address of the cluster hosting the VM
        clusterport  - (str) The port of the cluster hosting the VM
        cloudtype    - (str) The cloud type of the VM (Nimbus, OpenNebula, etc)
        network      - (str) The network association the VM uses
        cpuarch      - (str) The required CPU architecture of the VM
        image        - (str) The location of the image from which the VM was
                       created
        memory       - (int) The memory used by the VM
        mementry     - (int) The index of the entry in the host cluster's
                       memory list from which this VM is taking memory
        proxy_file   - the proxy that was used to authenticate this VM's
                       creation
        myproxy_creds_name - (str) The name of the credentials to retreive from
                              the myproxy server
        myproxy_server - (str) The hostname of the myproxy server to retreive
                          user creds from
        myproxy_server_port - (str) The port of the myproxy server to retreive
                              user creds from
        errorcount   - (int) Number of Polling Errors VM has had
        force_retire - (bool) Flag to prevent a retiring VM from being turned
                       back on
        """
        self.name = name
        self.id_ = id_
        self.vmtype = vmtype
        self.user = user
        self.uservmtype = ':'.join([user, vmtype])
        self.hostname = hostname
        self.alt_hostname = None
        self.ipaddress = ipaddress
        self.condorname = None
        self.condoraddr = None
        self.condormasteraddr = None
        self.clusteraddr = clusteraddr
        self.clusterport = clusterport
        self.cloudtype = cloudtype
        self.network = network
        self.image = image
        self.memory = memory
        self.mementry = mementry
        self.cpucores = cpucores
        self.storage = storage
        self.errorcount = 0
        self.errorconnect = None
        self.lastpoll = None
        self.last_state_change = None
        self.startup_time = None
        self.keep_alive = keep_alive
        self.idle_start = None
        self.spot_id = spot_id


class NoResourcesError(Exception):
    """
    Exception raised for errors where not enough resources are available

    Attributes:
        resource -- name of resource that is insufficient
    """
    def __init__(self, resource):
        self.resource = resource
        # TODO : Evaluate if we need to call super.__init__


class ICloud:
    """
    The ICloud interface is the framework for implementing support for
    a specific IaaS cloud implementation. In general, you'll need to
    override __init__ (be sure to call super's init), vm_create, vm_poll,
    and vm_destroy
    """

    def __init__(self, name="Dummy Cluster", host="localhost",
                 cloud_type="Dummy", memory=[], max_vm_mem=-1, networks=[],
                 vm_slots=0, cpu_cores=0, storage=0, hypervisor='xen',
                 boot_timeout=None, enabled=True, priority=0):
        self.name = name
        self.network_address = host
        self.cloud_type = cloud_type
        self.memory = memory
        self.max_mem = tuple(memory)
        self.max_vm_mem = max_vm_mem
        self.network_pools = networks
        self.vm_slots = vm_slots
        self.max_slots = vm_slots
        self.cpu_cores = cpu_cores
        self.storage_gb = storage
        self.max_storage_gb = storage
        self.vms = []  # List of running VMs
        self.enabled = enabled
        self.hypervisor = hypervisor
        self.connection_problem = False
        self.errorconnect = None
        self.priority = priority
        self.failed_image_set = set()
        self.__dict__ = {}
        self.vms_lock = None
        self.res_lock = None

        self.log = logging.getLogger(__name__)
        self.log.debug("New cluster {0} created".format(name))

    def __getstate__(self):
        """Override to work with pickle module."""
        state = self.__dict__.copy()
        del state['vms_lock']
        del state['res_lock']
        return state

    def __setstate__(self, state):
        """Override to work with pickle module."""
        self.__dict__ = state
        self.vms_lock = threading.RLock()
        self.res_lock = threading.RLock()

    def __repr__(self):
        return self.name

    def log_cluster(self):
        """Print cluster information to the log."""
        self.log.info("-" * 30 +
                      "Name:\t\t%s\n" % self.name +
                      "Address:\t%s\n" % self.network_address +
                      "Type:\t\t%s\n" % self.cloud_type +
                      "VM Slots:\t%s\n" % self.vm_slots +
                      "CPU Cores:\t%s\n" % self.cpu_cores +
                      "Storage:\t%s\n" % self.storage_gb +
                      "Memory:\t\t%s\n" % self.memory +
                      "Network Pools:\t%s\n" % ", ".join(self.network_pools) +
                      "-" * 30)

    def log_vms(self):
        """Print the cluster 'vms' list (via VM print)."""
        if len(self.vms) == 0:
            self.log.info("CLUSTER {0} has no running VMs...".
                          format(self.name))
        else:
            self.log.info("CLUSTER {0} running VMs:".format(self.name))
            for vm_ in self.vms:
                vm_.log_short("\t")

    # Support methods

    def num_vms(self):
        """Returns the number of VMs running on the cluster (in accordance
        to the vms[] list)
        """
        return len(self.vms)

    def slot_fill_ratio(self):
        """
        Return a ratio of how 'full' the cluster is based on used slots / total
        slots.
        """
        return (self.max_slots - self.vm_slots) / float(self.max_slots)

    def get_cluster_info_short(self):
        """Return a short form of cluster information."""
        output = "Cluster: %s \n" % self.name
        output += ("%-25s  %-15s  %-10s  %-10s %-10s %-10s %-10s\n" %
                   ("ADDRESS", "CLOUD TYPE", "VM SLOTS", "MEMORY", "STORAGE",
                    "PRIORITY", "ENABLED"))
        output += ("%-25s  %-15s  %-10s  %-10s %-10s %-10s %-10s\n" %
                   (self.network_address, self.cloud_type, self.vm_slots,
                    self.memory, self.storage_gb, self.priority, self.enabled))
        return output

    def get_cluster_vms_info(self):
        """Return information about running VMs on Cluster as a string."""
        if len(self.vms) == 0:
            return ""
        else:
            output = ""
            for vm_ in self.vms:
                output += "%s %-15s\n" % (vm_.get_vm_info()[:-1], self.name)
            return output

    def get_vm(self, vm_id):
        """Get VM object with id value."""
        for vm_ in self.vms:
            if vm_id == vm_.id_:
                return vm_
        return None

    # VM manipulation methods
    # !------------------------------------------------------------------------
    # NOTE: In implementing subclasses of Cluster, the following method
    #       prototypes should be used (standardize on these parameters)
    # !------------------------------------------------------------------------

    # Note: vm_id is the identifier for a VM, used to query or change an
    #       already created VM. vm_id will be a different entity based on the
    #       subclass's cloud software. EG: - Nimbus vm_ids are epr files -
    #       OpenNebula (and Eucalyptus?) vm_ids are names/numbers

    def vm_create(self, **args):
        """
        Create VM.
        """
        self.log.debug('This method should be defined by all subclasses '
                       'of Cluster\n')
        assert 0, 'Must define workspace_create'

    def vm_destroy(self, vm_, return_resources=True, reason=""):
        self.log.debug('This method should be defined by all subclasses of'
                       ' Cluster\n')
        assert 0, 'Must define workspace_destroy'

    def vm_poll(self, vm_):
        self.log.debug('This method should be defined by all subclasses of'
                       ' Cluster\n')
        assert 0, 'Must define workspace_poll'

    # # Private VM methods

    def find_mementry(self, memory):
        """
        Finds a memory entry in the Cluster's 'memory' list which supports the
        requested amount of memory for the VM.

        If multiple memory entries fit the request, returns the first suitable
        entry. Returns an exact fit if one exists.

        :param memory: The memory required for VM creation
        :returns: The index of the first fitting entry in the Cluster's
                  'memory' list. If no fitting memory entries are found,
                  returns -1 (error!)
        """
        # Check for exact fit
        if memory in self.memory:
            return self.memory.index(memory)

        # Scan for any fit
        for i in range(len(self.memory)):
            if self.memory[i] >= memory:
                return i

        # If no entries found, return error code.
        return -1

    def find_potential_mementry(self, memory):
        """
        Check if a cluster contains a memory entry with adequate space for
        given memory value.

        :returns: True if a valid memory entry is found, False otherwise.
        """
        potential_fit = False
        for i in range(len(self.max_mem)):
            if self.max_mem[i] >= memory:
                potential_fit = True
                break
        return potential_fit

    def resource_checkout(self, vm_):
        """
        Checks out resources taken by a VM in creation from the internal rep-
        resentation of the Cluster

        Parameters:
        vm_   - the VM object used to check out resources from the Cluster.

        Raises NoResourcesError if there are not enough available resources
        to check out.
        """
        # self.log.debug("Checking out resources for VM %s from Cluster %s"
        #                % (vm_.name, self.name))
        with self.res_lock:

            remaining_vm_slots = self.vm_slots - 1
            if remaining_vm_slots < 0:
                raise NoResourcesError("vm_slots")

            remaining_storage = self.storage_gb - vm_.storage
            if remaining_storage < 0:
                raise NoResourcesError("storage")

            remaining_memory = self.memory[vm_.mementry] - vm_.memory
            if remaining_memory < 0:
                raise NoResourcesError("memory")

            # Otherwise, we can check out these resources
            self.vm_slots = remaining_vm_slots
            self.storage_gb = remaining_storage
            self.memory[vm_.mementry] = remaining_memory

    def resource_return(self, vm_):
        """
        Returns the resources taken by the passed in VM to the Cluster's
        internal storage.

        Parameters: (as for checkout() )
        Notes: (as for checkout)
        """
        # self.log.debug("Returning resources used by VM %s to Cluster %s"
        #                % (vm_.name, self.name))
        with self.res_lock:
            self.vm_slots += 1
            self.storage_gb += vm_.storage
            # ISSUE: No way to know what mementry a VM is running on
            try:
                self.memory[vm_.mementry] += vm_.memory
            except:
                self.log.warning("Couldn't return memory because I don't know"
                                 " about that mem entry anymore...")


# utility parsing methods
def _attr_list_to_dict(attr_list):
    """
    _attr_list_to_dict -- parse a string like: host:ami, ..., host:ami into a
    dictionary of the form:
    {
        host: ami
        host: ami
    }

    if the string is in the form "ami" then parse to format
    {
        default: ami
    }

    raises ValueError if list can't be parsed
    """

    attr_dict = {}
    for host_attr in attr_list.split(","):
        host_attr = host_attr.split(":")
        if len(host_attr) == 1:
            attr_dict["default"] = host_attr[0].strip()
        elif len(host_attr) == 2:
            attr_dict[host_attr[0].strip()] = host_attr[1].strip()
        else:
            raise ValueError("Can't split '%s' into suitable host"
                             " attribute pair" % host_attr)

    return attr_dict
