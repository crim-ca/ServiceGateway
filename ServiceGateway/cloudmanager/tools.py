"""
Collection of utility functions for OpenStack management.
"""

MAX_VM_NAME_LEN = 54


class VMNameTooLong(Exception):
    """
    Error indicating that a given VM name is too long.
    """
    pass


def norm_vm_name(vm_name):
    """
    Normalize Virtual Machine name
    """
    name = vm_name.replace("_", '-').lower()
    if len(name) > MAX_VM_NAME_LEN:
        raise VMNameTooLong(name)
    return name
