import pulumi
from pulumi_proxmoxve import vm
import pulumi_proxmoxve as proxmox
import os

proxmox_provider = proxmox.Provider(
    'proxmoxve',
    proxmox.ProviderArgs(
        endpoint=os.environ["PROXMOX_HOST"],
        username=os.environ["PROXMOX_USER"],
        password=os.environ["PROXMOX_PASS"],
    )
)


def create_proxmox_vm(name, net_v4_address, net_v4_gate, user_pw, user_ssh_pub, vcpu=2, memory=1024, disk=25):
    """
    :param name: The name of the virtual machine to be created.
    :param net_v4_address: The IPv4 address for the virtual machine's network interface.
    :param net_v4_gate: The IPv4 gateway for the virtual machine's network interface.
    :param user_pw: The password for the user account on the virtual machine.
    :param user_ssh_pub: The SSH public key for the user account on the virtual machine.
    :param vcpu: The number of virtual CPUs to allocate to the virtual machine. Default is 2.
    :param memory: The amount of memory (in MB) to allocate to the virtual machine. Default is 1024.
    :param disk: The size of the virtual machine's disk (in GB). Default is 25.
    :return: The newly created virtual machine object.

    """
    v = vm.VirtualMachine(
        opts=pulumi.ResourceOptions(
            provider=proxmox_provider
        ),
        resource_name=name,
        name=f'pulumi-{name}',
        node_name="pve",
        cpu=vm.VirtualMachineCpuArgs(cores=vcpu, sockets=1),
        memory=vm.VirtualMachineMemoryArgs(dedicated=memory),
        clone=vm.VirtualMachineCloneArgs(
            node_name="pve",
            vm_id=102,
            full=True
        ),
        network_devices=[
            vm.VirtualMachineNetworkDeviceArgs(
                bridge="vmbr0",
                model="virtio"
            )
        ],
        agent=vm.VirtualMachineAgentArgs(
            enabled=True,
            type="virtio"
        ),
        cdrom=vm.VirtualMachineCdromArgs(
            enabled=False
        ),
        disks=[
            vm.VirtualMachineDiskArgs(
                interface="scsi0",
                iothread=True,
                datastore_id="local-lvm",
                size=8  # Added 8gb disk
            )
        ],
        operating_system=vm.VirtualMachineOperatingSystemArgs(
            type="l26"
        ),
        initialization=vm.VirtualMachineInitializationArgs(
            type="nocloud",
            datastore_id="local-lvm",
            ip_configs=[
                vm.VirtualMachineInitializationIpConfigArgs(
                    ipv4=vm.VirtualMachineInitializationIpConfigIpv4Args(
                        address=net_v4_address,
                        gateway=net_v4_gate
                    )
                )
            ],
            user_account=vm.VirtualMachineInitializationUserAccountArgs(
                username="k3s-user",
                password=user_pw,
                keys=[user_ssh_pub]
            )
        )
    )
    return v
