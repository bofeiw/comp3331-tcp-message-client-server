from typing import Dict, Set
from time import time


class UserManager:
    # manage all credentials and status of all users

    def __init__(self, block_duration: int, time_out: int):
        self.__user_map: Dict[str, UserManager.__User] = dict()
        self.__address_to_username_map: Dict[str, str] = dict()
        self.__username_to_address_map: Dict[str, str] = dict()
        self.__block_duration: int = block_duration
        self.__time_out: int = time_out
        self.__read_credentials()

    def __read_credentials(self):
        try:
            with open("credentials.txt", "r") as credential_file:
                for credential in credential_file:
                    username, password = credential.strip().split()
                    self.__user_map[username] = UserManager.__User(username, password,
                                                                   self.__block_duration,
                                                                   self.__time_out)
        except:
            print("FATAL: error reading credentials.txt")
            exit(1)

    def authenticate(self, username_input: str, password_input: str):
        # authenticate user and update status
        # return updated status

        if username_input not in self.__user_map:
            # username unknown
            return "USERNAME_NOT_EXIST"

        # else, delegate authenticate to specific user class
        return self.__user_map[username_input].authenticate(password_input)

    def set_address_username(self, address: str, username: str):
        self.__address_to_username_map[address] = username
        self.__username_to_address_map[username] = address

    def get_username(self, address: str) -> str:
        if address in self.__address_to_username_map:
            return self.__address_to_username_map[address]
        else:
            return ""

    def get_address(self, username: str) -> str:
        if username in self.__username_to_address_map:
            return self.__username_to_address_map[username]
        else:
            return ""

    def set_offline(self, username):
        if username in self.__user_map:
            self.__user_map[username].set_offline()

    def update(self):
        for user_credential in self.__user_map.values():
            user_credential.update()

    def block(self, from_username: str, to_block_username: str):
        if from_username in self.__user_map:
            self.__user_map[from_username].block(to_block_username)

    def unblock(self, from_username: str, to_block_username: str):
        if from_username in self.__user_map:
            self.__user_map[from_username].unblock(to_block_username)

    def is_blocked_user(self, from_username: str, to_block_username: str):
        return from_username in self.__user_map and self.__user_map[from_username].is_blocked_user(to_block_username)

    def has_user(self, username):
        return username in self.__user_map

    def is_online(self, username):
        return username in self.__user_map and self.__user_map[username].is_online()

    def all_users(self) -> list:
        return list(self.__user_map.keys())

    def get_timed_out_users(self) -> set:
        timed_out_users = set()
        for user in self.__user_map:
            if self.__user_map[user].update_time_out():
                timed_out_users.add(user)
        return timed_out_users

    def get_online_users(self) -> set:
        online_users = set()
        for user in self.__user_map:
            if self.__user_map[user].is_online():
                online_users.add(user)
        return online_users

    def get_users_logged_in_since(self, since: int) -> set:
        users = set()
        for user in self.__user_map:
            if self.__user_map[user].last_log_in() > time() - since:
                users.add(user)
        return users

    def refresh_user_timeout(self, username):
        if username in self.__user_map:
            self.__user_map[username].refresh_user_timeout()

    class __User:
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
            self.__inactive_since: int = int(time())
            self.__blocked_users: Set[str] = set()
            self.__last_login: int = 0

        def block(self, username: str):
            self.__blocked_users.add(username)

        def unblock(self, username: str):
            if username in self.__blocked_users:
                self.__blocked_users.remove(username)

        def is_blocked_user(self, username: str):
            return username in self.__blocked_users

        def update(self):
            # unblock users if any
            if self.__blocked and self.__blocked_since + self.__block_duration < time():
                self.__blocked = False

        def set_offline(self):
            self.__online = False
            self.__consecutive_fails = 0
            self.__blocked_since = 0

        def is_online(self):
            return self.__online

        def update_time_out(self):
            # update time out status, return true if should lof out this user because of timeout
            if self.is_online() and self.__inactive_since + self.__timeout < time():
                self.set_offline()
                return True
            return False

        def refresh_user_timeout(self):
            self.__inactive_since = time()

        def last_log_in(self):
            return self.__last_login

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
            self.__last_login = int(time())
            self.refresh_user_timeout()
            return "SUCCESS"
