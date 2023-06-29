from abc import ABCMeta, abstractmethod


class SecretBackend(metaclass=ABCMeta):

    @abstractmethod
    def get_secret(self, path):
        pass

    def get(self, path):
        return self.deserialize_secret(self.get_secret(path))

    def deserialize_secret(self, secret):
        """
        Deserialize the secret from the backend. It's likely that most backends won't need this,
        but it's here for the ones that do.
        """
        return secret
