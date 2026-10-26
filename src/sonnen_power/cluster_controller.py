import logging
import socket

from sonnen_power.wol import send_magic_packet

logger = logging.getLogger(__name__)


def _apps_api():
    # Imported lazily so tests and dry-run runs don't require the
    # kubernetes client to be installed.
    from kubernetes import client, config

    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.AppsV1Api()


class ClusterController:
    def __init__(
        self,
        execute_actions: bool,
        control_plane_mac_address: str | None,
        wol_broadcast_address: str,
        wol_port: int,
        cluster_api_host: str | None,
        cluster_api_port: int,
        folding_namespace: str = "folding",
        folding_deployment: str = "folding",
        folding_burn_replicas: int = 1,
    ) -> None:
        self.execute_actions = execute_actions
        self.control_plane_mac_address = control_plane_mac_address
        self.wol_broadcast_address = wol_broadcast_address
        self.wol_port = wol_port
        self.cluster_api_host = cluster_api_host
        self.cluster_api_port = cluster_api_port
        self.folding_namespace = folding_namespace
        self.folding_deployment = folding_deployment
        self.folding_burn_replicas = folding_burn_replicas

    def _scale_folding(self, replicas: int) -> None:
        body = {"spec": {"replicas": replicas}}
        _apps_api().patch_namespaced_deployment_scale(
            name=self.folding_deployment,
            namespace=self.folding_namespace,
            body=body,
        )

    def enable_folding(self) -> None:
        target = self.folding_burn_replicas
        if not self.execute_actions:
            logger.info("dry-run: would scale %s/%s to replicas=%d",
                        self.folding_namespace, self.folding_deployment, target)
            return
        logger.info("scaling %s/%s to replicas=%d",
                    self.folding_namespace, self.folding_deployment, target)
        self._scale_folding(target)

    def disable_folding(self) -> None:
        if not self.execute_actions:
            logger.info("dry-run: would scale %s/%s to replicas=0",
                        self.folding_namespace, self.folding_deployment)
            return
        logger.info("scaling %s/%s to replicas=0",
                    self.folding_namespace, self.folding_deployment)
        self._scale_folding(0)

    def power_on_workers(self) -> None:
        if not self.execute_actions:
            logger.info("dry-run: would power on worker nodes via IPMI")
            return
        logger.info("TODO: ipmitool chassis power on for each worker")

    def drain_and_power_off_workers(self) -> None:
        if not self.execute_actions:
            logger.info("dry-run: would cordon, drain, and power off worker nodes via IPMI")
            return
        logger.info("TODO: kubectl cordon/drain workers, then ipmitool chassis power off")

    def wake_control_plane(self) -> None:
        if not self.control_plane_mac_address:
            logger.warning("CONTROL_PLANE_MAC_ADDRESS is not configured")
            return
        if not self.execute_actions:
            logger.info("dry-run: would wake control plane with Wake-on-LAN")
            return
        send_magic_packet(self.control_plane_mac_address, self.wol_broadcast_address, self.wol_port)

    def check_cluster_reachable(self, timeout_seconds: float = 3.0) -> bool:
        if not self.cluster_api_host:
            logger.info("CLUSTER_API_HOST is not configured")
            return False
        try:
            with socket.create_connection((self.cluster_api_host, self.cluster_api_port), timeout=timeout_seconds):
                return True
        except OSError:
            return False
