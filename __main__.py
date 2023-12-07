"""A Kubernetes Python Pulumi program"""

import pulumi
import pulumi_kubernetes.core.v1 as core
import pulumi_kubernetes.meta.v1 as meta
import pulumi_random as random

from k8s_deployment import create_k8s_deployment
from proxmox_vm import create_proxmox_vm

config = pulumi.Config()
config_namespace = config.require("namespace")
config_tz = config.require("timezone")  # "Europe/Berlin"
config_base_path = config.require("hostbasepath")  # "/home/markus/k3s-demo-data"
config_sshpub = config.require("sshpubkey")
config_gate = config.require("netv4gate")


def deploy_k3s_vms():
    """
    Deploys K3s VMs.

    :return: None
    """
    user_pw = random.RandomPassword("k3s_user_pw", length=32)
    create_proxmox_vm(
        name="k3s-server",
        memory=2048,
        net_v4_gate=config_gate,
        user_pw=user_pw.result,
        user_ssh_pub=config_sshpub,
        net_v4_address="172.16.10.50/24"
    )


def deploy_k8s_services():
    ns = core.Namespace(config_namespace, metadata=meta.ObjectMetaArgs(
        name=config_namespace
    ))
    # MQTT server
    mqtt_deployment, mqtt_service, mqtt_ingress = create_k8s_deployment(
        name="mqtt-server",
        namespace=ns,
        container_image="cmccambridge/mosquitto-unraid:latest",
        env={
            "RUN_INSECURE_MQTT_SERVER": "1"
        },
        ports=[1883]
    )

    # iobroker
    iob_deployment, iob_service, iob_ingress = create_k8s_deployment(
        name="iobroker",
        namespace=ns,
        container_image="buanet/iobroker:latest",
        env={
            "TZ": config_tz
        },
        ports=[8081],
        volumes=[
            {"name": "data", "host_path": f"{config_base_path}/iobroker/data", "container_path": "/opt/iobroker"},
            {"name": "scripts", "host_path": f"{config_base_path}/iobroker/scripts",
             "container_path": "/opt/userscripts"},
        ],
        ingress_hostname="iobroker.local"
    )

    # NodeRed
    nr_deployment, nr_service, nr_ingress = create_k8s_deployment(
        name="nodered",
        namespace=ns,
        container_image="nodered/node-red:latest",
        env={
            "TZ": config_tz
        },
        ports=[1880],
        volumes=[
            {"name": "data", "host_path": f"{config_base_path}/nodered", "container_path": "/data"},
        ],
        ingress_hostname="nodered.local"

    )

    pulumi.export("port_mqtt", mqtt_service.spec.ports[0]["node_port"])


deploy_k3s_vms()
deploy_k8s_services()
