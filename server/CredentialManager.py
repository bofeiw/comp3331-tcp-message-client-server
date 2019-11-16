from enum import Enum, auto
from typing import Dict


class CredentialManager:
    # manage all credentials and status of all users

    def __init__(self):
        self.__credential_map: Dict[str, CredentialManager.__UserCredential] = dict()
        self.__read_credentials()

    def __read_credentials(self):
        try:
            with open("credentials.txt", "r") as credential_file:
                for credential in credential_file:
                    username, password = credential.strip().split()
                    self.__credential_map[username] = CredentialManager.__UserCredential(username, password)
        except:
            print("FATAL: error reading credentials.txt")
            exit(1)

    def authenticate(self, username_input: str, password_input: str):
        # authenticate user and update status
        # return updated status

        if username_input not in self.__credential_map:
            # username unknown
            return "USERNAME_NOT_EXIST"

        # else, delegate authenticate to specific user class
        return self.__credential_map[username_input].authenticate(password_input)

    class __UserCredential:
        # manage username, password, online status, number of consecutive fail trials,
        # blocked timestamp of a particular user

        def __init__(self, username: str, password: str):
            self.__username: str = username
            self.__password: str = password
            self.__online: bool = False
            self.__blocked: bool = False
            self.__consecutive_fails: int = 0
            self.__blocked_since: int = 0

        def set_offline(self):
            self.__online = False
            self.__consecutive_fails = 0
            self.__blocked_since = 0

        def authenticate(self, password_input: str):
            # authenticate, return the status of the updated user

            if self.__password != password_input:
                # incorrect password
                return "INVALID_PASSWORD"

            if self.__blocked:
                # user is blocked
                return "BLOCKED"

            if self.__online:
                # user is already logged in
                return "ALREADY_LOGGED_IN"

            # is able to login. update status
            self.__online = True
            return "SUCCESS"

