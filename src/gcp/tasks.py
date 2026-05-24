from __future__ import annotations

import json
import os
from typing import Any


class CloudTasksClient:
    def __init__(self, client: Any, project: str, region: str) -> None:
        self._client = client
        self._base = f"projects/{project}/locations/{region}/queues"

    @classmethod
    def from_env(cls) -> CloudTasksClient:
        from google.cloud import tasks_v2  # lazy import

        return cls(
            tasks_v2.CloudTasksClient(),
            os.environ["GCP_PROJECT_ID"],
            os.environ.get("GCP_REGION", "southamerica-east1"),
        )

    def _queue_path(self, queue_name: str) -> str:
        return f"{self._base}/{queue_name}"

    def enqueue_hitl_notification(
        self,
        run_id: str,
        tenant_id: str,
        api_base_url: str,
        ttl_hours: int = 4,
    ) -> str:
        from google.cloud import tasks_v2  # lazy import
        from google.protobuf import duration_pb2

        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=f"{api_base_url}/internal/hitl/notify",
                headers={"Content-Type": "application/json"},
                body=json.dumps({"run_id": run_id, "tenant_id": tenant_id}).encode(),
            ),
            dispatch_deadline=duration_pb2.Duration(seconds=ttl_hours * 3600),
        )
        queue = os.environ.get("TASKS_QUEUE_HITL", "hitl-approvals")
        resp = self._client.create_task(
            request=tasks_v2.CreateTaskRequest(parent=self._queue_path(queue), task=task)
        )
        return resp.name

    def enqueue_worker(self, queue_name: str, payload: dict, url: str) -> str:
        from google.cloud import tasks_v2  # lazy import

        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=url,
                headers={"Content-Type": "application/json"},
                body=json.dumps(payload).encode(),
            )
        )
        resp = self._client.create_task(
            request=tasks_v2.CreateTaskRequest(parent=self._queue_path(queue_name), task=task)
        )
        return resp.name
