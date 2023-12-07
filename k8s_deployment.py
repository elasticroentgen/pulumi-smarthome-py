from pulumi import ResourceOptions
from pulumi_kubernetes.apps import v1 as apps
from pulumi_kubernetes.core import v1 as core
from pulumi_kubernetes.meta import v1 as meta
from pulumi_kubernetes.networking import v1 as net


def create_k8s_deployment(name, namespace, container_image, env=None, ports=None, volumes=None,ingress_hostname=None):
    """
    :param name: The name of the Kubernetes deployment
    :param namespace: The namespace in which to create the deployment
    :param container_image: The container image to use for the deployment
    :param env: Additional environment variables for the container (default: None)
    :param ports: List of container ports to expose (default: None)
    :param volumes: List of volumes to mount in the container (default: None)
    :param ingress_hostname: The hostname for the ingress (default: None)
    :return: The deployment, service, and ingress (if ingress_hostname is provided) objects
    """
    app_labels = {"app": name}

    # process env
    envArgs = None
    if env is not None:
        envArgs = []
        for k, v in env.items():
            envArgs.append(core.EnvVarArgs(name=k, value=v))

    # Ports
    pod_port_args = None
    svc_port_args = None
    if ports is not None:
        pod_port_args = []
        svc_port_args = []

        for p in ports:
            pod_port_args.append(core.ContainerPortArgs(container_port=p))
            svc_port_args.append(core.ServicePortArgs(port=p, target_port=p))

    # Volumes
    vol_mount_args = None
    vol_args = None
    if volumes is not None:
        vol_mount_args = []
        vol_args = []
        for v in volumes:
            vol_mount_args.append(core.VolumeMountArgs(
                name=v["name"],
                mount_path=v["container_path"]
            ))
            vol_args.append(core.VolumeArgs(
                name=v["name"],
                host_path=core.HostPathVolumeSourceArgs(
                    path=v["host_path"]
                )
            ))

    d = apps.Deployment(
        f'{name}-deploy',
        opts=ResourceOptions(
            depends_on=[namespace]
        ),
        metadata=meta.ObjectMetaArgs(
            namespace=namespace.metadata["name"],
            name=name
        ),
        spec=apps.DeploymentSpecArgs(
            selector=meta.LabelSelectorArgs(match_labels=app_labels),
            replicas=1,
            template=core.PodTemplateSpecArgs(
                metadata=meta.ObjectMetaArgs(labels=app_labels),
                spec=core.PodSpecArgs(
                    containers=[
                        core.ContainerArgs(
                            name=name,
                            image=container_image,
                            env=envArgs,
                            ports=pod_port_args,
                            volume_mounts=vol_mount_args
                        )
                    ],
                    volumes=vol_args
                )
            ),
        ))

    i = None
    if ingress_hostname is not None:
        # Build a service with an ingress
        s = core.Service(
            f'{name}-svc',
            opts=ResourceOptions(depends_on=[d]),
            metadata=meta.ObjectMetaArgs(
                namespace=namespace,
                labels=app_labels,
                name=name
            ),
            spec=core.ServiceSpecArgs(
                type="ClusterIP",
                selector=app_labels,
                ports=svc_port_args,
            )
        )

        i = net.Ingress(
            f'{name}-ingress',
            metadata=meta.ObjectMetaArgs(
                namespace=namespace.metadata["name"],
                name=name,
                labels = app_labels,
        ),
            spec = net.IngressSpecArgs(
                rules=[
                    net.IngressRuleArgs(
                        host=ingress_hostname,
                        http=net.HTTPIngressRuleValueArgs(
                            paths=[
                                net.HTTPIngressPathArgs(
                                    path="/",
                                    path_type="Prefix",
                                    backend=net.IngressBackendArgs(
                                        service=net.IngressServiceBackendArgs(
                                            name=s.metadata["name"],
                                            port=net.ServiceBackendPortArgs(
                                                number=s.spec.ports[0]["port"]
                                            )
                                        )

                                    )

                                )
                            ]
                        )

                    )
                ]
            )
        )
    else:
        # Build a node port service
        s = core.Service(
            f'{name}-svc',
            opts=ResourceOptions(depends_on=[d]),
            metadata=meta.ObjectMetaArgs(
                namespace=namespace,
                labels=app_labels,
                name=name
            ),
            spec=core.ServiceSpecArgs(
                type="NodePort",
                selector=app_labels,
                ports=svc_port_args,
            )
        )
    return d, s, i
