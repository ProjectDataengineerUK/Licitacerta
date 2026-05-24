from __future__ import annotations

import json
import os
from typing import Any


class PubSubPublisher:
    def __init__(self, client: Any, project_id: str) -> None:
        self._client = client
        self._project_id = project_id

    @classmethod
    def from_env(cls) -> PubSubPublisher:
        from google.cloud import pubsub_v1  # lazy import

        return cls(pubsub_v1.PublisherClient(), os.environ["GCP_PROJECT_ID"])

    def publish_event(self, topic: str, data: dict) -> str:
        topic_path = self._client.topic_path(self._project_id, topic)
        future = self._client.publish(topic_path, json.dumps(data, ensure_ascii=False).encode())
        return future.result()
