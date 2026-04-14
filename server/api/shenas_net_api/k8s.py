"""Kubernetes API helper for managing headless worker deployments."""

from __future__ import annotations

import logging
import os
import secrets

from kubernetes import client, config

log = logging.getLogger("shenas-net-api.k8s")

NAMESPACE = "shenas-workers"
IMAGE = os.environ.get(
    "WORKER_IMAGE",
    "us-east4-docker.pkg.dev/shenas-491609/shenas/shenas-headless:latest",
)


def _load_config() -> None:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def create_worker(worker_id: str, mesh_token: str) -> None:
    """Create a headless worker deployment in the shenas-workers namespace."""
    _load_config()
    core = client.CoreV1Api()
    apps = client.AppsV1Api()

    name = f"worker-{worker_id[:8]}"
    db_key = secrets.token_hex(32)

    # DB encryption key secret
    core.create_namespaced_secret(
        namespace=NAMESPACE,
        body=client.V1Secret(
            metadata=client.V1ObjectMeta(name=f"{name}-db-key", labels={"worker-id": worker_id}),
            string_data={"key": db_key},
        ),
    )

    # Mesh token secret
    core.create_namespaced_secret(
        namespace=NAMESPACE,
        body=client.V1Secret(
            metadata=client.V1ObjectMeta(name=f"{name}-mesh-token", labels={"worker-id": worker_id}),
            string_data={"token": mesh_token},
        ),
    )

    # Deployment
    apps.create_namespaced_deployment(
        namespace=NAMESPACE,
        body=client.V1Deployment(
            metadata=client.V1ObjectMeta(name=name, labels={"app": "shenas-worker", "worker-id": worker_id}),
            spec=client.V1DeploymentSpec(
                replicas=1,
                strategy=client.V1DeploymentStrategy(type="Recreate"),
                selector=client.V1LabelSelector(match_labels={"worker-id": worker_id}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": "shenas-worker", "worker-id": worker_id}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="shenas",
                                image=IMAGE,
                                args=["shenas", "--headless", "--no-tls", "--host", "0.0.0.0"],
                                ports=[client.V1ContainerPort(container_port=7280, name="api")],
                                env=[
                                    client.V1EnvVar(
                                        name="SHENAS_DB_KEY",
                                        value_from=client.V1EnvVarSource(
                                            secret_key_ref=client.V1SecretKeySelector(name=f"{name}-db-key", key="key")
                                        ),
                                    ),
                                    client.V1EnvVar(name="SHENAS_HEADLESS", value="1"),
                                    client.V1EnvVar(name="SHENAS_SYNC_INTERVAL", value="300"),
                                    client.V1EnvVar(name="SHENAS_NET_URL", value="https://shenas.net"),
                                    client.V1EnvVar(
                                        name="SHENAS_REMOTE_TOKEN",
                                        value_from=client.V1EnvVarSource(
                                            secret_key_ref=client.V1SecretKeySelector(name=f"{name}-mesh-token", key="token")
                                        ),
                                    ),
                                ],
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": "100m", "memory": "256Mi"},
                                    limits={"cpu": "1", "memory": "1Gi"},
                                ),
                                liveness_probe=client.V1Probe(
                                    http_get=client.V1HTTPGetAction(path="/api/graphql", port="api"),
                                    initial_delay_seconds=10,
                                    period_seconds=30,
                                ),
                            )
                        ],
                    ),
                ),
            ),
        ),
    )
    log.info("Created worker deployment %s", name)


def delete_worker(worker_id: str) -> None:
    """Delete a worker deployment and its secrets."""
    _load_config()
    core = client.CoreV1Api()
    apps = client.AppsV1Api()

    name = f"worker-{worker_id[:8]}"

    try:
        apps.delete_namespaced_deployment(name=name, namespace=NAMESPACE)
    except client.ApiException as e:
        if e.status != 404:
            raise
    for suffix in ("db-key", "mesh-token"):
        try:
            core.delete_namespaced_secret(name=f"{name}-{suffix}", namespace=NAMESPACE)
        except client.ApiException as e:
            if e.status != 404:
                raise
    log.info("Deleted worker %s", name)


def get_worker_status(worker_id: str) -> str:
    """Return the status of a worker's pod: Running, Pending, Failed, or Unknown."""
    _load_config()
    core = client.CoreV1Api()

    try:
        pods = core.list_namespaced_pod(
            namespace=NAMESPACE,
            label_selector=f"worker-id={worker_id}",
        )
        if not pods.items:
            return "NotFound"
        pod = pods.items[0]
        return pod.status.phase or "Unknown"
    except client.ApiException:
        return "Unknown"
