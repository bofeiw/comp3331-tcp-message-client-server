from enum import Enum, auto
from typing import Dict
from time import time


class CredentialManager:
    # manage all credentials and status of all users

    def __init__(self, block_duration: int, time_out: int):
        self.__credential_map: Dict[str, CredentialManager.__UserCredential] = dict()
        self.__address_to_username_map: Dict[str, str] = dict()
        self.__block_duration: int = block_duration
        self.__time_out: int = time_out
        self.__read_credentials()

    def __read_credentials(self):
        try:
            with open("credentials.txt", "r") as credential_file:
                for credential in credential_file:
                    username, password = credential.strip().split()
                    self.__credential_map[username] = CredentialManager.__UserCredential(username, password,
                                                                                         self.__block_duration,
                                                                                         self.__time_out)
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

    def set_address_username(self, address: str, username: str):
        self.__address_to_username_map[address] = username

    def get_username(self, address: str) -> str:
        if address in self.__address_to_username_map:
            return self.__address_to_username_map[address]
        else:
            return ""

    def set_offline(self, username):
        if username in self.__credential_map:
            self.__credential_map[username].set_offline()

    def update(self):
        for user_credential in self.__credential_map.values():
            user_credential.update()

    class __UserCredential:
        # manage username, password, online status, number of consecutive fail trials,
        # blocked timestamp of a particular user

        def __init__(self, username: str, password: str, block_duration: int, timeout: int):
            self.__username: str = username
            self.__password: str = password
            self.__block_duration: int = block_duration
            self.__timeout: int = timeout
            self.__online: bool = False
            self.__blocked: bool = False
            self.__consecutive_fails: int = 0
            self.__blocked_since: int = 0
            self.__inactive_since: int = 0

        def update(self):
            # unblock users if any
            if self.__blocked and self.__blocked_since + self.__block_duration < time():
                self.__blocked = False

        def set_offline(self):
            self.__online = False
            self.__consecutive_fails = 0
            self.__blocked_since = 0

        def authenticate(self, password_input: str):
            # authenticate, return the status of the updated user

            if self.__online:
                # user is already logged in
                return "ALREADY_LOGGED_IN"

            if self.__blocked:
                # user is blocked
                return "BLOCKED"

            if self.__password != password_input:
                # incorrect password
                self.__consecutive_fails += 1
                if self.__consecutive_fails >= 3:
                    self.__blocked_since = time()
                    self.__blocked = True
                    return "INVALID_PASSWORD_BLOCKED"
                return "INVALID_PASSWORD"

            # is able to login. update status
            self.__online = True
            return "SUCCESS"
