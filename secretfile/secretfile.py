""" Python secretfile implementation """

import os
import re
from typing import Any, ClassVar, List, Mapping, MutableMapping, Optional

from secretfile.backends.meta import SecretBackend

_BACKEND: SecretBackend | None = None


def set_backend(backend: SecretBackend):
    global _BACKEND
    if _BACKEND is not None:
        raise Exception("Secretfile backend already set.")
    _BACKEND = backend


def ensure_backend():
    if _BACKEND is None:
        raise Exception("Secretfile backend not set.")


if 'VAULT_ADDR' in os.environ:
    # For convenience, if it's obvious that vault settings exist, then automatically set the backend to Vault.
    from secretfile.backends.vault import VaultBackend
    set_backend(VaultBackend())


class Secretfile:
    """An interface to fetch our creds using our Secretfile."""

    # Singleton secretfile object.
    secretfile: ClassVar[Optional["Secretfile"]] = None

    _cache: MutableMapping[str, str] = {}

    @classmethod
    def fetch(cls) -> "Secretfile":
        """Look up our global Secretfile. Use this method if you want to use the singleton object."""
        if cls.secretfile is None:
            # Do this so that the type-checker can see everything.
            cls.secretfile = Secretfile()
            return cls.secretfile
        else:
            return cls.secretfile

    @classmethod
    def get(cls, key: str, default=None):
        """Get a single key. Defaults to using environment variables, if possible.
        If keys do not exist in the environment, grabs them from vault (or the cache).
        """
        secretfile = cls.fetch()
        try:
            return secretfile[key]
        except KeyError:
            return default

    @classmethod
    def getmany(cls, *keys) -> Mapping[str, Any]:
        """Get many keys at once."""
        secretfile = cls.fetch()
        return secretfile._get_group(list(keys))

    @classmethod
    def items(cls):
        """Get all items in the secretfile."""
        secretfile = cls.fetch()
        # _secretfile is just the mapping of SECRET_NAME -> PATH:KEY
        # We need to actually resolve the paths to get the values.
        for key in secretfile._secretfile:
            yield key, secretfile[key]

    def __init__(self):
        self._secretfile: Mapping[str, str] = self.read_secretfile()

    def __getitem__(self, key):
        """Get a single key. Defaults to using environment variables, if possible.
        If keys do not exist in the environment, grabs them from vault (or the cache).
        """

        # I'm not sure I'm convinced that we should defer to the application's environment variables for secrets.
        var = os.environ.get(key)
        if var is None:
            # Check the local cache
            # NOTE: This is not safe for STS creds, because the result of our calls to vault will live in memory for
            # the life of this execution. Currently, all secrets we use are long-lived, so this doesn't affect us.
            var = self._cache.get(key)

            if var is None:
                # Not in the environment or cache, grab from vault
                path = self._secretfile[key]
                path = path.split(":")
                inner_key = None
                if len(path) == 1:
                    path = path[0]
                else:
                    path, inner_key = path

                ensure_backend()
                pathval = _BACKEND.get(path=path)
                if inner_key:
                    var = pathval[inner_key]
                else:
                    var = pathval

                self._cache[key] = var

        return var

    def _get_group(self, keys: List[str]) -> Mapping[str, Any]:
        """Get a group of related keys. These may be things like AWS access keys,
        which must be associated with each other, and therefore must come from
        the same vault read."""
        local_cache: MutableMapping[str, Any] = {}
        values = {}
        for key in keys:
            var = os.environ.get(key)
            # Generally, these should either ALL come from the environment, or NONE should.
            # For now, we don't enforce this, but chances are the user's call will fail.
            if not var:
                # If the variable is not in the environment, grab it from vault, and cache
                # the result of vault read locally
                path, field = self._secretfile[key].split(":")

                try:
                    pathval = local_cache[path]
                except KeyError:
                    pathval = _BACKEND.get(path)
                    local_cache[path] = pathval

                var = pathval[field]

            # Store the value we got, either from the environment or vault
            values[key] = var

        return values

    def _secretfile_path(self) -> str:
        """Get the path to our Secretfile."""
        path = os.environ.get("SECRETFILE_PATH")
        if path is None:
            return "Secretfile"
        else:
            return path

    def read_secretfile(self) -> Mapping[str, str]:
        """Reads in secretfile, generating a dictionary of key to secret path."""
        secretfile = {}
        path = self._secretfile_path()
        with open(path, "r") as fp:
            lines = fp.readlines()

            for line in lines:
                if line.startswith("#"):
                    pass
                else:
                    var, path = line.rstrip().split(" ")

                    # Replace anything that looks like an environment variable with a corresponding value.
                    secretfile[var] = _replace_env(var, path)

        return secretfile


def _replace_env(key: str, path: str) -> str:
    """
    Replace any environment variables in a string with their values. Raise an exception if they're not set in the current
    application's environment.
    """

    env_regex = r"\$([A-Za-z0-9_]+)"
    env_vars = re.findall(env_regex, path)

    for env_var in env_vars:
        if env_var not in os.environ:
            raise Exception(f"Environment variable {env_var} not set but required in path for {key}")
        path = path.replace(f"${env_var}", os.environ[env_var])

    return path
