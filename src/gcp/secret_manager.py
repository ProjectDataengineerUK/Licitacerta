from __future__ import annotations

import os


def resolve_secrets(names: dict[str, str]) -> dict[str, str]:
    """
    Resolve Secret Manager references at startup.

    names: mapping of env_var_name → secret resource name
      e.g. {"ANTHROPIC_API_KEY": "projects/P/secrets/anthropic-api-key/versions/latest"}

    For each entry:
    - If the env var is already set, leaves it untouched.
    - Otherwise fetches the secret value from Secret Manager and sets the env var.
    """
    from google.cloud import secretmanager  # lazy import

    client = secretmanager.SecretManagerServiceClient()
    resolved: dict[str, str] = {}
    for env_name, resource in names.items():
        if os.environ.get(env_name):
            resolved[env_name] = os.environ[env_name]
            continue
        response = client.access_secret_version(request={"name": resource})
        value = response.payload.data.decode("utf-8").strip()
        os.environ[env_name] = value
        resolved[env_name] = value
    return resolved
