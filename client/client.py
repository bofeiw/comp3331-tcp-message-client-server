# Python 3
# Usage: python3 client.py server_IP server_port
# coding: utf-8
from socket import *
import json
import atexit
import threading
import time
import sys
import signal


def keyboard_interrupt_handler(signal, frame):
    exit(0)


signal.signal(signal.SIGINT, keyboard_interrupt_handler)

# command line args
if len(sys.argv) != 3:
    print("invalid command line arguments")
    exit(0)
server_name = sys.argv[1]
server_port = int(sys.argv[2])

# would communicate with server after every second
UPDATE_INTERVAL = 1
to_exit = False
is_timeout = False

clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((server_name, server_port))

t_lock = threading.Condition()

username = input("username: ")
message = json.dumps({
    "action": "login",
    "username": username,
    "password": input("password: ")
})


def logout():
    if is_timeout:
        print("\rYou are timed out.")
    else:
        print("\rYou are logged out.")
        clientSocket.send(json.dumps({
            "action": "logout"
        }).encode())
        clientSocket.close()


def recv_handler():
    global to_exit, is_timeout
    while True:
        login_result = clientSocket.recv(1024)
        data = json.loads(login_result.decode())
        print('\r', end='')
        if data['action'] == 'message':
            if data['status'] == 'MESSAGE_SELF':
                print("Cannot message yourself.")
            elif data['status'] == 'USER_NOT_EXIST':
                print("User does not exist.")
            elif data['status'] == 'USER_BLOCKED':
                print("That user blocked you.")
            elif data['status'] == 'SUCCESS':
                pass
        elif data['action'] in ['receive_message', 'receive_broadcast']:
            print(data["from"], ':', data['message'])
        elif data['action'] == 'block':
            if data['status'] == 'MESSAGE_SELF':
                print("Cannot block yourself.")
            elif data['status'] == 'USER_NOT_EXIST':
                print("User does not exist.")
            else:
                print("Block success.")
        elif data['action'] == 'unblock':
            if data['status'] == 'MESSAGE_SELF':
                print("Cannot unblock yourself.")
            elif data['status'] == 'USER_NOT_EXIST':
                print("User does not exist.")
            else:
                print("Unblock success.")
        elif data['action'] == 'broadcast':
            print('broadcast success to', data['n_sent'], 'users.', data['n_blocked'],
                  'users blocked you so they can not see the message.')
        elif data['action'] == 'timeout':
            to_exit = True
            is_timeout = True
        elif data['action'] == 'whoelse':
            print("Online users:")
            print("\n".join(data['reply']))
        elif data['action'] == 'whoelsesince':
            print("whoelsesince:")
            print("\n".join(data['reply']))
        else:
            print(data)
        print('> ', end='')
        sys.stdout.flush()


def send_handler():
    global to_exit
    while True:
        # handle input and send to server
        command = input("> ").strip()
        if command.startswith("logout"):
            to_exit = True
        elif command.startswith("message"):
            _, user, message = command.split(' ', 2)
            clientSocket.send(json.dumps({
                "action": "message",
                "message": message,
                "user": user
            }).encode())
        elif command.startswith("broadcast"):
            _, message = command.split()
            clientSocket.send(json.dumps({
                "action": "broadcast",
                "message": message,
            }).encode())
        elif command.startswith("block"):
            _, user = command.split()
            clientSocket.send(json.dumps({
                "action": "block",
                "user": user,
            }).encode())
        elif command.startswith("unblock"):
            _, user = command.split()
            clientSocket.send(json.dumps({
                "action": "unblock",
                "user": user,
            }).encode())
        elif command.startswith("whoelsesince"):
            _, since = command.split()
            clientSocket.send(json.dumps({
                "action": "whoelsesince",
                "since": since
            }).encode())
        elif command.startswith("whoelse"):
            clientSocket.send(json.dumps({
                "action": "whoelse"
            }).encode())


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
    clientSocket.send(message.encode())
    # wait for the reply from the server
    login_result = clientSocket.recv(1024)
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
