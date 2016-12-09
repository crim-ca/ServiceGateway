#!/usr/bin/env python
# coding:utf-8

"""
Implement elasticity for the Load Balancer.

This can be kept as a separate process because different hosting IaaS solutions
might need different approaches. For instance, on EC2, one might want to use
the AutoScaling / CloudWatch approach or EC2 elastic load balancing.

See : `Amazon autoscaling <https://aws.amazon.com/autoscaling/>`_
through the
`Boto library <http://boto.readthedocs.org/en/latest/autoscale_tut.html>`_

Some assumptions made in the current module:

 * There can only be one consumer per machine (IP address)

Also, see this `article
<http://fr.wikipedia.org/wiki/%C3%89lasticit%C3%A9_(cloud_computing)>`_ (in
French) for good insights on the generalities of elasticity.
"""

# -- Standard lib ------------------------------------------------------------
from collections import defaultdict
from time import time, sleep
from uuid import uuid4
import logging.config
import optparse
import logging
import shelve
import os

# -- 3rd party ---------------------------------------------------------------
import requests
import pyrabbit   # Wrapper for the RabbitMQ HTTP management API

# -- project - specific ------------------------------------------------------
from .exceptions import (InsufficientResources,
                         NoIdleWorkersError,
                         MinimumWorkersReached,
                         NoProfilesFoundError,
                         NoTearDownTargets,
                         IncompatibleBackendError)
from .cloudmanager.openstackcloud import OpenStackCloud
from .cloudmanager.openstackcloud import VMNotFound
from .cloudmanager.tools import norm_vm_name
from VestaRestPackage.app_objects import APP, CELERY_APP

# For provisionning : The prefered approach seems to be Ansible with
# appropriate playbooks. Although we may want to tie-in provisionning with
# spawning.
# Also, the cloudservers lib might be a good option on rackspace :
# https://pythonhosted.org/python-cloudservers/api.html

# -- Configuration shorthands ------------------------------------------------
THIS_DIR = os.path.abspath(os.path.dirname(__file__))
OPS_CONFIG = APP.config['OPS_CONFIG']  # OpenStack Access configuration.
# This is the number of jobs in a queue before spawning starts:
BACKORDER_THRESHOLD = APP.config['RUBBER_BACKORDER_THRESHOLD']
BROKER_ADMIN_UNAME = APP.config['BROKER_ADMIN_UNAME']
BROKER_ADMIN_PASS = APP.config['BROKER_ADMIN_PASS']
FL_API_URL = APP.config['FLOWER_API_URL']
MAX_VM_QTY = APP.config['RUBBER_MAX_VM_QTY']
EVAL_INTERVAL = APP.config['RUBBER_EVAL_INTERVAL']
MIN_IDLE_WORKERS = APP.config['RUBBER_MIN_IDLE_WORKERS']
VM_STORE_FN = os.path.join(os.path.expanduser('~'),
                           '.rubber',
                           'vm_object_store.dat')
SLACKER_TIME_THRESHOLD = APP.config['RUBBER_SLACKER_TIME_THRESHOLD']


def is_booting(vm_info):
    """
    Evaluate if a VM might still be in it's booting stage
    """
    uptime = time() - vm_info['time']
    return uptime < SLACKER_TIME_THRESHOLD


class Rubber(object):
    """
    Class implementing elasticity for the Load Balancer setup.

    Keeps track of VMs and if they are occupied.
    Keeps track of quantity of requests on the queue.
    Establishes a metric to determine how many new VMs should be started.

    This class should be aware of the resource limits of a given cloud space.
    That means we should know about the maximum number of VM instances our
    environment can handle (can also be dictated by economical issues).

    There is also a concept of profiles. Meaning that for a given cloud space,
    a number of VM classes can share the total resources in an egalitarian
    manner.

    The class reads the information produced by the Celery distributed task
    queue system from the configured backend.
    """
    def __init__(self, vm_store_fn):
        self.logger = logging.getLogger(__name__+'.Rubber')
        self.workers = None
        broker_info = requests.utils.urlparse(CELERY_APP.conf.BROKER_URL)
        if broker_info.scheme.lower() != 'amqp':
            raise IncompatibleBackendError("Can only work with a AMQP broker")

        broker_addr = broker_info.netloc.split(":")[0]
        broker_port = APP.config['BROKER_ADMIN_PORT']
        broker_loc = "{l}:{p}".format(l=broker_addr, p=broker_port)
        self.logger.info(u"Using broker address : {a}".format(a=broker_loc))
        self.manager = pyrabbit.api.Client(broker_loc,
                                           BROKER_ADMIN_UNAME,
                                           BROKER_ADMIN_PASS,
                                           timeout=5)

        self.logger.debug("Opening VM object store at : {s}".
                          format(s=vm_store_fn))
        self.vm_shelf = shelve.open(vm_store_fn)
        self.profiles = APP.config['WORKER_SERVICES']
        self.logger.info(u"Known profiles are : {p}".
                         format(p=self.profiles.keys()))
        self.queues = {}
        self.__get_queues()

        # Communism implemented here:
        nb_profiles = len(self.profiles)
        if not nb_profiles:
            raise NoProfilesFoundError("No use in running rubber on a system "
                                       "with no known service profiles.")
        max_vms_per_service, privileges = divmod(MAX_VM_QTY, nb_profiles)
        for profile in self.profiles:
            pr_ = self.profiles[profile]  # Shorthand on config structure.
            pr_['max_vms'] = max_vms_per_service
            if privileges > 0:
                pr_['max_vms'] += 1
                privileges -= 1
            self.logger.info(u"Queue «{q}» has a max count of {c}".
                             format(q=pr_['celery_queue_name'],
                                    c=pr_['max_vms']))

        self.min_wms_per_service = MIN_IDLE_WORKERS
        self.__refresh_worker_knowledge()

        self.my_cloud = OpenStackCloud(**OPS_CONFIG)

    def __del__(self):
        """
        Destructor
        """
        self.vm_shelf.close()

    def __get_queues(self):
        """
        Populate queue list.

        Currently uses the configuration items to populate the list.
        """
        for profile in self.profiles:
            self.logger.debug("Obtaining queue name from profile : {c}".
                              format(c=profile))
            queue = self.profiles[profile]['celery_queue_name']
            self.queues[queue] = {}

    def spawn(self, profile):
        """
        Spawn a VM and return it's IP address.

        :param profile: Identifier of the profile to be spawned.
        :type profile: string
        :raises: InsufficientResources
        """
        self.logger.info("Instructed to spawn {q} workers".format(q=1))
        pr_ = self.profiles[profile]  # Shorthand on config structure.
        queue_name = pr_['celery_queue_name']
        max_workers = pr_['max_vms']
        actual_worker_count = len(pr_['consumers'])
        if actual_worker_count + 1 > max_workers:
            raise InsufficientResources("Not enough resources to spawn a new"
                                        " virtual machine for {p}".
                                        format(p=profile))

        vm_name = norm_vm_name("{p}-{u}".format(p=queue_name[:10], u=uuid4()))
        self.logger.info("Requesting to spawn machine with name {n}".
                         format(n=vm_name))
        self.my_cloud.vm_create(vm_name, **pr_['os_args'])
        sci = {'time': time(), 'queue_name': queue_name}
        self.vm_shelf[vm_name] = sci

    def teardown(self, profile):
        """
        Shut down a virtual machine.

        :param profile: Name of the profile for which we want to take down a
                        worker.
        :raises: MinimumWorkersReached
        :raises: NoIdleWorkersError
        :raises: NoTearDownTargets
        """
        self.logger.info("Proceeding to find a worker of profile {p}"
                         " to tear down".format(p=profile))
        queue_name = self.profiles[profile]['celery_queue_name']
        idle_workers = set(self.get_idle_workers(queue_name))
        if not idle_workers:
            raise NoIdleWorkersError("No idle workers for {q} could"
                                     " be found".format(q=queue_name))

        actual_worker_count = len(self.queues[queue_name]['consumers'])
        self.logger.debug("Actual worker count {c} for profile {p}".
                          format(c=actual_worker_count, p=queue_name))
        if actual_worker_count - 1 < self.min_wms_per_service:
            raise MinimumWorkersReached("Taking down worker for"
                                        " {0} would bring below minimum"
                                        " employment level.".
                                        format(queue_name))

        cloud_workers = set(self.my_cloud.list_vm_names())
        my_workers = set(self.vm_shelf)
        idle_cloud_workers = list(cloud_workers.intersection(idle_workers,
                                                             my_workers))
        self.logger.debug("Idle cloud workers : {c} for profile {p}".
                          format(c=idle_cloud_workers, p=profile))

        if not idle_cloud_workers:
            raise NoTearDownTargets("No teardown access to idle workers for"
                                    " {p}".format(p=queue_name))

        target = idle_cloud_workers.pop()
        self.logger.info(u"Shutting down virtual machine : {0}".
                         format(target))
        self.my_cloud.vm_delete(target)
        self.logger.debug(u"Removing {t} from VM object store".
                          format(t=target))
        del self.vm_shelf[target]

    def __refresh_worker_knowledge(self):
        """
        Refresh knowledge on worker queue registry.

        Does not deal with queue length. Only which workers are available for
        given services and on what queue they are listening.
        """
        self.logger.info(u"Refreshing knowledge on all worker queues")
        # TODO : This should be replaced by a call to celery.control.inspect
        #        instead of a call to flower who's API changes through
        #        versions.
        all_wrkrs = requests.get('{u}/workers'.format(u=FL_API_URL)).json()
        # Active workers only
        workers = dict([(k, v) for k, v in all_wrkrs.items() if v['status']])
        self.workers = workers

        queue_consumers = defaultdict(list)
        for worker in workers:
            self.logger.debug("Inspecting worker {w}".format(w=worker))
            for queue_name in workers[worker]['queues']:
                queue_consumers[queue_name].append(worker)

        for queue_name in self.queues:
            consumers = queue_consumers[queue_name]
            self.logger.info(u'We have knowledge of {0} consumers for {1}'.
                             format(len(consumers), queue_name))
            self.queues[queue_name]['consumers'] = consumers

    def get_queue_length(self, queue_name):
        """
        Gets the number of pending messages in a given AMQP queue.

        :param queue_name: Name of the queue for which we want to get the
                           number of pending messages.
        :returns: Number of pending messages in the queue.
        """
        self.logger.debug(u'Checking length of queue {0}'.format(queue_name))
        length = self.manager.get_queue_depth('/', name=queue_name)
        self.logger.info(u"Queue «{0}» has length of {1}".
                         format(queue_name, length))
        return length

    def get_active_workers(self, queue_name):
        """
        Get workers which are apparently working.

        :param queue_name: Name of the profile defining a worker class.
        :returns: A list of all active workers.
        """
        active_workers = [k.split('@')[-1] for k, v in self.workers.items() if
                          v['running_tasks'] and queue_name in v['queues']]
        self.logger.debug("Active workers for {p} are : {i}".
                          format(i=active_workers, p=queue_name))
        return active_workers

    def get_idle_workers(self, queue_name):
        """
        Get workers which are apparently not working.

        :param queue_name: Name of the profile defining a worker class.
        :returns: A list of all idle workers.
        """
        idle_workers = [k.split('@')[-1] for k, v in self.workers.items()
                        if not v['running_tasks'] and
                        queue_name in v['queues']]
        self.logger.debug("Idle workers for {p} are : {i}".
                          format(i=idle_workers, p=queue_name))
        return idle_workers

    def evaluate_needs(self, profile):
        """
        Checks the state of the queue, the number of registered workers, and
        establishes if we need more workers or otherwise if we can discard some
        workers which are idle.

        The bulk of the elasticity logic is contained in this function.
        Then again, this function is idealistic in it's demands, it does not
        know of the limits of the system.

        Ideally this could be a control loop with feedback but for the moment
        the implementation is very simple.

        :param profile: Name of the profile defining a worker class.
        :type profile: string
        :returns: Delta of projected VM needs for a given profile. A positive
                  value indicates that we need that number of new machines, a
                  negative value indicates that we can discard that number of
                  active machines. A value of zero means that no change to the
                  number of workers seems required.
        """
        self.logger.info("Evaluating needs for {p}".format(p=profile))
        worker_needs = 0  # Base assumption.

        queue_name = self.profiles[profile]['celery_queue_name']
        pending_jobs = self.get_queue_length(queue_name)
        idle_workers = self.get_idle_workers(queue_name)

        if pending_jobs > BACKORDER_THRESHOLD:
            profile_params = self.profiles[profile]['rubber_params']
            spawn_r = profile_params.get('spawn_ratio', 0.2)

            # Check if we have any spawning workers and how many
            booting = [v for v in self.vm_shelf if is_booting(v) and
                       v['queue_name'] == queue_name]
            self.logger.info("Still waiting for {n} machines to boot for {p}".
                             format(n=len(booting), p=profile))

            # Linear scaling, keep track of booting machines.
            worker_needs = int(pending_jobs * spawn_r) - len(booting)
            if worker_needs < 0:
                worker_needs = 0
        elif not pending_jobs:
            worker_needs = pending_jobs-len(idle_workers)  # Should be negative

        self.logger.info(u"Estimated needs are {n} workers for {p}".
                         format(n=worker_needs, p=profile))
        return worker_needs

    def check_slackers(self):
        """
        Check for registered machines on cloud which do not register on worker
        queue.

        Terminate any machine which has been slacking for more than a given
        time threshold defined by SLACKER_TIME_THRESHOLD.
        """
        self.logger.info("Looking for slackers")
        for vm_ in self.vm_shelf:
            if vm_ not in self.workers:
                # We have a potential slacker.
                if not is_booting(self.vm_shelf[vm_]):
                    self.logger.info("Found a slacker machine : {v}, "
                                     "terminating".format(v=vm_))
                    # Off with his head !!!
                    try:
                        self.my_cloud.vm_delete(vm_)
                    except VMNotFound as exc:
                        self.logger.warning("Could not terminate VM: {e}. "
                                            "Removing from index.".
                                            format(e=str(exc)))
                        del self.vm_shelf[vm_]

    def launch(self, evaluation_interval=EVAL_INTERVAL):
        """
        This function launches a periodic check of the conditions for spawning
        or tearing down machines.

        This function is blocking. It can be called to use an instance of this
        class as an application.

        :param evaluation_interval: Interval at which the state of the cloud
                                    will be evaluated. Defaults to
                                    EVAL_INTERVAL.
        """
        self.logger.info(u"Starting periodic checking of needs")
        while True:

            self.logger.info("Next pass in {t} seconds".
                             format(t=evaluation_interval))
            sleep(evaluation_interval)
            self.__refresh_worker_knowledge()

            self.check_slackers()

            for profile in self.profiles:
                needed_workers = self.evaluate_needs(profile)
                if needed_workers > 0:
                    self.logger.info(u'We need to spawn {0} workers'.
                                     format(needed_workers))
                    for iteration in range(needed_workers):
                        try:
                            self.spawn(profile)
                        except InsufficientResources as exc:
                            self.logger.warning(u"Could not spawn new "
                                                u"resources : {0}".
                                                format(repr(exc)))
                elif needed_workers < 0:
                    surplus = abs(needed_workers) - self.min_wms_per_service
                    self.logger.info(u'We could release {0} workers'.
                                     format(surplus))
                    for iteration in range(surplus):
                        try:
                            self.teardown(profile)
                        except MinimumWorkersReached as exc:
                            self.logger.info(u'Cannot terminate worker '
                                             u': {0}'.format(repr(exc)))
                        except (NoIdleWorkersError, NoTearDownTargets) as exc:
                            self.logger.warning(u'Cannot terminate worker '
                                                u': {0}'.format(repr(exc)))


def main():
    """
    Script entry point
    """
    parser = optparse.OptionParser()

    log_conf_fn = os.path.join(THIS_DIR, 'logging.ini')
    parser.add_option("-l",
                      action='store',
                      default=log_conf_fn,
                      dest='logging_conf_fn',
                      help='Set logging configuration filename')
    parser.add_option("-s",
                      action='store',
                      default=VM_STORE_FN,
                      dest='vm_store_fn',
                      help='Set VM store filename')

    options = parser.parse_args()[0]

    logging.config.fileConfig(options.logging_conf_fn)

    logger = logging.getLogger(__name__)
    rubber_conf_dir = os.path.join(os.path.expanduser('~'), '.rubber')
    if not os.path.exists(rubber_conf_dir):
        logger.info(u"Creating rubber configuration directory {r}".
                    format(r=rubber_conf_dir))
        os.makedirs(rubber_conf_dir)
    elastic = Rubber(options.vm_store_fn)
    elastic.launch()

if __name__ == '__main__':
    main()
