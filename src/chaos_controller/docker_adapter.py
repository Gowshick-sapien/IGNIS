import time
import logging
import docker

logger = logging.getLogger("docker_adapter")

class DockerAdapter:
    def __init__(self, docker_client=None):
        self._client = docker_client

    @property
    def client(self):
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def disconnect(self, container_name: str, network_name: str) -> dict:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            container = self.client.containers.get(container_name)
            network = self._find_network(network_name)
            if not network:
                return {
                    "success": False,
                    "details": f"Network matching name '{network_name}' not found",
                    "timestamp": timestamp
                }
            network.disconnect(container)
            logger.info(f"Disconnected container {container_name} from network {network.name}")
            return {
                "success": True,
                "details": f"Successfully disconnected container '{container_name}' from network '{network.name}'",
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"Error disconnecting container {container_name}: {e}")
            return {
                "success": False,
                "details": str(e),
                "timestamp": timestamp
            }

    def reconnect(self, container_name: str, network_name: str) -> dict:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            container = self.client.containers.get(container_name)
            network = self._find_network(network_name)
            if not network:
                return {
                    "success": False,
                    "details": f"Network matching name '{network_name}' not found",
                    "timestamp": timestamp
                }
            network.connect(container)
            logger.info(f"Reconnected container {container_name} to network {network.name}")
            return {
                "success": True,
                "details": f"Successfully reconnected container '{container_name}' to network '{network.name}'",
                "timestamp": timestamp
            }
        except Exception as e:
            err_str = str(e)
            if "endpoint already exists" in err_str or "already exists" in err_str:
                return {
                    "success": True,
                    "details": f"Container '{container_name}' is already connected to network '{network.name}'",
                    "timestamp": timestamp
                }
            logger.error(f"Error reconnecting container {container_name}: {e}")
            return {
                "success": False,
                "details": err_str,
                "timestamp": timestamp
            }

    def kill(self, container_name: str) -> dict:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            logger.info(f"Stopped container {container_name}")
            return {
                "success": True,
                "details": f"Successfully stopped container '{container_name}'",
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"Error stopping container {container_name}: {e}")
            return {
                "success": False,
                "details": str(e),
                "timestamp": timestamp
            }

    def restart(self, container_name: str) -> dict:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            container = self.client.containers.get(container_name)
            container.restart()
            logger.info(f"Restarted container {container_name}")
            return {
                "success": True,
                "details": f"Successfully restarted container '{container_name}'",
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"Error restarting container {container_name}: {e}")
            return {
                "success": False,
                "details": str(e),
                "timestamp": timestamp
            }

    def get_status(self, container_name: str) -> dict:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            container = self.client.containers.get(container_name)
            status = container.status
            return {
                "success": True,
                "details": f"Container status: '{status}'",
                "status": status,
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"Error getting status for container {container_name}: {e}")
            return {
                "success": False,
                "details": str(e),
                "timestamp": timestamp
            }

    def _find_network(self, network_name: str):
        networks = self.client.networks.list()
        for network in networks:
            if network.name == network_name or network.name.endswith(f"_{network_name}"):
                return network
        return None
