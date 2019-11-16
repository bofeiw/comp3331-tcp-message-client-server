from CredentialManager import CredentialManager


class UserManager:
    def __init__(self, credential_manager: CredentialManager):
        self.__credential_manager = credential_manager
