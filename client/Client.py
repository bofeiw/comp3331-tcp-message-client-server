# Python 3
# Usage: python3 UDPClient3.py localhost 12000
# coding: utf-8
from socket import *
import json
import atexit
import threading
import time
import sys

# Server would be running on the same host as Client
serverName = "localhost"
serverPort = 13856

# would communicate with server after every second
UPDATE_INTERVAL = 1
timeout = False
to_exit = False

clientSocket = socket(AF_INET, SOCK_DGRAM)
t_lock = threading.Condition()

username = input("username: ")
message = json.dumps({
    "action": "login",
    "username": username,
    "password": input("password: ")
})


def logout():
    print("\rYou are logged out.")
    clientSocket.sendto(json.dumps({
        "action": "logout"
    }).encode(), (serverName, serverPort))
    clientSocket.close()


def recv_handler():
    while True:
        print("receiving")
        login_result, server_address = clientSocket.recvfrom(2048)
        print(login_result.decode())


def send_handler():
    global to_exit
    while True:
        # handle input and send to server
        command = input("> ").strip()
        if command.startswith("logout"):
            to_exit = True


def interact():
    recv_thread = threading.Thread(name="RecvHandler", target=recv_handler)
    recv_thread.daemon = True
    recv_thread.start()

    send_thread = threading.Thread(name="SendHandler", target=send_handler)
    send_thread.daemon = True
    send_thread.start()
    # this is the main thread
    while True:
        time.sleep(0.1)
        if to_exit:
            exit(0)


def log_in():
    global message
    clientSocket.sendto(message.encode(), (serverName, serverPort))
    # wait for the reply from the server
    login_result, server_address = clientSocket.recvfrom(2048)
    login_result = json.loads(login_result.decode())
    if login_result["action"] == 'login' and login_result["status"] == "SUCCESS":
        print("You are logged in")
        atexit.register(logout)
        interact()
    elif login_result["action"] == 'login' and login_result["status"] == "ALREADY_LOGGED_IN":
        print("You have already logged in.")
    elif login_result["action"] == 'login' and login_result["status"] == "INVALID_PASSWORD_BLOCKED":
        print("Invalid password. Your account has been blocked. Please try again later.")
    elif login_result["action"] == 'login' and login_result["status"] == "BLOCKED":
        print("Due to multiple consecutive fails to log in, you have been blocked.")
    elif login_result["action"] == 'login' and login_result["status"] == "INVALID_PASSWORD":
        message = json.dumps({
            "action": "login",
            "username": username,
            "password": input("Invalid password. Please try again:")
        })
        log_in()
    elif login_result["action"] == 'login' and login_result["status"] == "ALREADY_LOGGED_IN":
        print(login_result["status"])
    elif login_result["action"] == 'login' and login_result["status"] == "USERNAME_NOT_EXIST":
        print(login_result["status"])
    else:
        print(login_result["status"])
        print("FATAL: could not connect to server")
        exit(1)


if __name__ == "__main__":
    log_in()
