from __future__ import annotations

import os
import time


def record_metric(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    from google.cloud import monitoring_v3  # lazy import
    from google.protobuf import timestamp_pb2

    project_id = os.environ["GCP_PROJECT_ID"]
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    series = monitoring_v3.TimeSeries()
    series.metric.type = f"custom.googleapis.com/licitacerta/{name}"
    if labels:
        series.metric.labels.update(labels)

    series.resource.type = "global"
    series.resource.labels["project_id"] = project_id

    now = time.time()
    ts = timestamp_pb2.Timestamp(seconds=int(now), nanos=int((now % 1) * 1e9))
    point = monitoring_v3.Point(
        interval=monitoring_v3.TimeInterval(end_time=ts),
        value=monitoring_v3.TypedValue(double_value=value),
    )
    series.points.append(point)

    client.create_time_series(name=project_name, time_series=[series])
