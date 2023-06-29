import os
from typing import Any

import hvac

from secretfile.backends.meta import SecretBackend
from secretfile.exceptions import BackendConfigurationError


class VaultBackend(SecretBackend):
    def __init__(self):
        if "VAULT_ADDR" not in os.environ:
            raise BackendConfigurationError("VAULT_ADDR is not set.")
        if "VAULT_TOKEN" not in os.environ:
            raise BackendConfigurationError("VAULT_TOKEN is not set.")

    def get_secret(self, path):
        return vault_get_path(path)



def vault_get_path(path: str) -> Any:
    """Get data at a given path from vault. User is expected to unpack correctly."""
    hvac_client = hvac.Client(
        url=os.environ["VAULT_ADDR"], token=os.environ["VAULT_TOKEN"]
    )
    response = hvac_client.read(path)
    if response and "data" in response:
        return response["data"]
    else:
        raise Exception(f"Could not access {path} in Vault: {response}")

