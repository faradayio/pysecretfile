from secretfile.backends.meta import SecretBackend


class MemoryBackend(SecretBackend):
    def __init__(self, secrets: dict[str, str]):
        self._secrets = secrets

    def get_secret(self, path):
        return self._secrets[path]
