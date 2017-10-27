#!/usr/bin/env python
# coding: utf-8

# -- Standard library --------------------------------------------------------
import logging

# -- Third party -------------------------------------------------------------
import novaclient.v1_1.client as nvclient
#import novaclient.client as nvclient
import novaclient.exceptions

# -- Project - specific ------------------------------------------------------
from . import cloud_init_util
from . import cloud_tools


class VMNotFound(Exception):
    """
    Indicates that a given VM name could not be found.
    """
    pass


class OpenStackCloud(cloud_tools.ICloud):
    def __init__(self, name="Dummy Cluster", cloud_type="Dummy",
                 memory=[], max_vm_mem=-1, networks=[], vm_slots=0,
                 cpu_cores=0, storage=0, security_group=None,
                 username=None, password=None, tenant_name=None,
                 auth_url=None, hypervisor='xen', key_name=None,
                 boot_timeout=None, secure_connection="",
                 regions=[], vm_domain_name="", reverse_dns_lookup=False,
                 placement_zone=None, enabled=True, priority=0):

        # Call super class's init
        '''
        cloud_tools.ICloud.__init__(self, name=name, host=auth_url,
                                    cloud_type=cloud_type,
                                    memory=memory, max_vm_mem=max_vm_mem,
                                    networks=networks,
                                    vm_slots=vm_slots, cpu_cores=cpu_cores,
                                    storage=storage, hypervisor=hypervisor,
                                    boot_timeout=boot_timeout, enabled=enabled,
                                    priority=priority)
        '''
        super(self.__class__ ,self).__init__(name=name, host=auth_url,
                                    cloud_type=cloud_type,
                                    memory=memory, max_vm_mem=max_vm_mem,
                                    networks=networks,
                                    vm_slots=vm_slots, cpu_cores=cpu_cores,
                                    storage=storage, hypervisor=hypervisor,
                                    boot_timeout=boot_timeout, enabled=enabled,
                                    priority=priority)

        self.log = logging.getLogger("cloudmanager")

        if not security_group:
            security_group = ["default"]

        self.security_groups = security_group
        self.username = username if username else ""
        self.password = password if password else ""
        self.tenant_name = tenant_name if tenant_name else ""
        self.auth_url = auth_url if auth_url else ""
        self.key_name = key_name if key_name else ""
        self.secure_connection = secure_connection in ['True', 'true', 'TRUE']
        self.total_cpu_cores = -1
        self.regions = regions
        self.vm_domain_name = (vm_domain_name if vm_domain_name is not None
                               else "")
        self.reverse_dns_lookup = reverse_dns_lookup
        self.placement_zone = placement_zone
        self.flavor_set = set()

    def vm_create(self, vm_name, vm_type=None, vm_networkassoc=None,
                  image=None, vm_mem=None, vm_cores=None, vm_storage=None,
                  customization=None,
                  vm_keepalive=0, instance_type="", job_per_core=False,
                  securitygroup=[], key_name="", pre_customization=None,
                  use_cloud_init=False, extra_userdata=[]):
        """
        Create a VM on OpenStack.
        """
        use_cloud_init = False
        nova = self._get_creds_nova()
        if len(securitygroup) != 0:
            sec_group = []
            for group in securitygroup:
                if group in self.security_groups:
                    sec_group.append(group)
            if len(sec_group) == 0:
                self.log.debug("No defined security groups for job - trying"
                               " default value from cloud_resources.conf")
                sec_group = self.security_groups
        else:
            sec_group = self.security_groups
        self.log.debug("Using security group: {s}".format(s=sec_group))
        if key_name and len(key_name) > 0:
            if not nova.keypairs.findall(name=key_name):
                key_name = ""
        else:
            key_name = self.key_name if self.key_name else ""
        if customization:
            build_write_files = cloud_init_util.build_write_files_cloud_init
            user_data = build_write_files(customization)
        else:
            user_data = ""
        if pre_customization:
            if not use_cloud_init:
                for item in pre_customization:
                    user_data = '\n'.join([item, user_data])
            else:
                inject_custom = cloud_init_util.inject_customizations
                user_data = inject_custom(pre_customization, user_data)
        elif use_cloud_init:
            user_data = cloud_init_util.inject_customizations([], user_data)[0]
        if len(extra_userdata) > 0:
            # need to use the multi-mime type functions
            mk_mime_msg = cloud_init_util.build_multi_mime_message
            user_data = mk_mime_msg([(user_data,
                                      'cloud-config',
                                      'cloud_conf.yaml')],
                                    extra_userdata)

        try:
            imageobj = nova.images.find(name=image)
        except Exception as exc:
            self.log.warning("Exception occurred while trying to fetch image"
                             " via name: {s}".format(s=exc))
            self.log.exception(exc)
            try:
                imageobj = nova.images.get(image)
                self.log.debug("Got image via uuid: {s}".format(s=image))
            except Exception as exc:
                self.log.exception("Unable to fetch image via uuid: {s}".
                                   format(s=exc))
                self.failed_image_set.add(image)
                return

        i_type = instance_type
        try:
            flavor = nova.flavors.find(name=i_type)
        except Exception as exc:
            self.log.warning("Exception occurred while trying to get flavor"
                             " by name: {s} - will attempt to use name value "
                             "as a uuid.".format(s=exc))
            try:
                flavor = nova.flavors.get(i_type)
                self.log.debug("Got flavor via uuid: {s}".format(s=i_type))
            except Exception as exc:
                self.log.error("Exception occurred trying to get flavor by"
                               " uuid: {s}".format(s=exc))
                return
        self.flavor_set.add(flavor)
        # find the network id to use if more than one network
        if vm_networkassoc:
            network = self._find_network(vm_networkassoc)
            if network:
                netid = [{'net-id': network.id}]
            else:
                self.log.debug("Unable to find network named: {s} on {n}".
                               format(s=vm_networkassoc, n=self.name))
                netid = []
        elif self.network_pools and len(self.network_pools) > 0:
            network = self._find_network(self.network_pools[0])
            if network:
                netid = [{'net-id': network.id}]
            else:
                self.log.debug("Unable to find network named: {s} on {n}".
                               format(s=self.network_pools[0], n=self.name))
                netid = []
        else:
            netid = []
        # Need to get the rotating hostname from the google code to use for
        # here.
        name = vm_name
        instance = None



        if name:
            try:
                instance = nova.servers.create(name=name,
                                               image=imageobj,
                                               flavor=flavor,
                                               key_name=key_name,
                                               nics=netid,
                                               userdata=user_data,
                                               security_groups=sec_group)
                self.log.debug("Instance : {i}".format(i=instance))
            except novaclient.exceptions.OverLimit as exc:
                self.log.error("Quota Exceeded on {s}: {m}".
                               format(s=self.name, m=exc.message))
            except Exception as exc:
                self.log.error("Unhandled exception while creating vm on {n}:"
                               " {e}".format(n=self.name, e=exc))
                self.log.exception(exc)

    def list_vm_names(self):
        """
        Get list of all VMs.

        :returns: Name of VMs.
        """
        self.log.info('Obtaining list of all VMs on cloud')
        nova = self._get_creds_nova()
        vm_list = nova.servers.list()
        vm_names = [vm.name for vm in vm_list]
        self.log.debug("VM names : {n}".format(n=vm_names))
        return vm_names

    def vm_stop(self, name):
        """
        Stop a VM
        """
        nova = self._get_creds_nova()
        vm_ = nova.servers.find(name=name)
        self.log.info('Stopping VM : {v}'.format(v=vm_))
        vm_.stop()

    def vm_status(self, name):
        """
        Get the status of a VM
        """
        nova = self._get_creds_nova()
        vm_ = nova.servers.find(name=name)
        self.log.info('VM has status : {s}'.format(vm_.status))
        return vm_.status

    def _get_creds_nova(self):
        """
        Get an auth token to Nova.
        """

        try:
            client = nvclient.Client(username=self.username,
                                     api_key=self.password,
                                     auth_url=self.auth_url,
                                     project_id=self.tenant_name)
        except Exception as exc:
            self.log.error("Unable to create connection to {s}: Reason:"
                           " {e}".format(s=self.name, e=exc))
        return client

    def _find_network(self, name):
        nova = self._get_creds_nova()
        network = None
        try:
            networks = nova.networks.list()
            for net in networks:
                if net.label == name:
                    network = net
        except Exception as exc:
            self.log.error("Unable to list networks on {n} Exception:"
                           " {e}".format(n=self.name, e=exc))
        return network

    def vm_delete(self, name):
        """
        Terminate a VM
        """
        nova = self._get_creds_nova()
        try:
            vm_ = nova.servers.find(name=name)
        except novaclient.exceptions.NotFound as exc:
            raise VMNotFound(exc)
        self.log.info('Deleting VM : {v}'.format(v=vm_))
        vm_.delete()
