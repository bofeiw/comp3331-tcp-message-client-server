# Python 3.7
# Author: Bofei Wang
# Usage: python3 client.py server_IP server_port
# coding: utf-8
# modified from the multi-threading sample code

import json
import atexit
import threading
import time
import sys
import signal
import readline
from socket import *
from typing import Dict


# captures ctrl+c exit keyboard signal
def keyboard_interrupt_handler(signal, frame):
    exit(0)


# command line args
if len(sys.argv) != 3:
    print("invalid command line arguments")
    exit(0)
server_name = sys.argv[1]
server_port = int(sys.argv[2])

# would communicate with server after every second
UPDATE_INTERVAL = 1

# if set true, main thread will exit at next 0.1 second
to_exit = False

# if set true, a time out message will be displayed to the terminal
# and the program will exit
is_timeout = False

# connect to the server
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((server_name, server_port))

# get the thread
t_lock = threading.Condition()

# map of username to private tcp socket
private_socket_map: Dict = dict()

# private connection socket
private_recv_socket = socket(AF_INET, SOCK_STREAM)
private_recv_socket.bind(('localhost', 0))
private_recv_socket.listen(1)
private_recv_port = private_recv_socket.getsockname()[1]

# get the username and password and login
username = input("username: ")
# username may be overwritten
USERNAME = username
message = json.dumps({
    "action": "login",
    "username": username,
    "password": input("password: "),
    "private_port": private_recv_port
})


# logout handler
def logout():
    if is_timeout:
        print("\rYou are timed out.")
    else:
        print("\rYou are logged out.")
        clientSocket.send(json.dumps({
            "action": "logout"
        }).encode())
        clientSocket.close()


# print without breaking input thread
# https://stackoverflow.com/a/4653306/12208789 resolve line buffer issue
def safe_print(*args):
    sys.stdout.write('\r' + ' ' * (len(readline.get_line_buffer()) + 2) + '\r')
    print(*args)
    sys.stdout.write('> ' + readline.get_line_buffer())
    sys.stdout.flush()


# return a function as connection handler for a specific socket for multi threading
def private_connection_handler(connection_socket, client_address):
    def real_connection_handler():
        while True:
            data = connection_socket.recv(1024)
            if not data:
                # if data is empty, the socket is closed or is in the
                # process of closing. In this case, close this thread
                safe_print('Private connection stopped.')
                exit(0)

            # received data from the client, now we know who we are talking with
            data = data.decode()
            data = json.loads(data)
            from_user = data["from"]
            message = data["message"]

            safe_print('[PRIVATE]', from_user, ':', message)

    return real_connection_handler


# handles all incoming data and replies to those
def private_recv_handler():
    while True:
        # create a new connection for a new client
        connection_socket, client_address = private_recv_socket.accept()
        safe_print('Private connection started.')

        # create a new function handler for the client
        private_socket_handler = private_connection_handler(connection_socket, client_address)

        # create a new thread for the client socket
        private_socket_thread = threading.Thread(name=str(client_address), target=private_socket_handler)
        private_socket_thread.daemon = False
        private_socket_thread.start()


def private_connect(address: str, port: int, username: str):
    # connect with address directly in p2p mode
    new_private_socket = socket(AF_INET, SOCK_STREAM)
    new_private_socket.connect((address, port))
    private_socket_map[username] = new_private_socket
    safe_print('Private connection connected.')


def private_disconnect(username: str):
    # disconnect with user
    if username in private_socket_map and private_socket_map[username]:
        private_socket_map[username].close()
        safe_print('Closed.')
    else:
        safe_print('Not connected.')


def private_message(username: str, message: str):
    # send a private message to user
    if username in private_socket_map and private_socket_map[username]:
        private_socket_map[username].send(json.dumps({
            'from': USERNAME,
            'message': message
        }).encode())
    else:
        safe_print('Not connected.')


# handles all incoming data and selectively display useful information to user
def recv_handler():
    global to_exit, is_timeout
    while True:
        login_result = clientSocket.recv(1024)
        data = json.loads(login_result.decode())
        if data['action'] == 'message':
            # reply to a user-initiated message
            if data['status'] == 'MESSAGE_SELF':
                safe_print("Cannot message yourself.")
            elif data['status'] == 'USER_NOT_EXIST':
                safe_print("User does not exist.")
            elif data['status'] == 'USER_BLOCKED':
                safe_print("That user blocked you.")
            elif data['status'] == 'SUCCESS':
                # message sent successfully
                pass
        elif data['action'] in ['receive_message', 'receive_broadcast']:
            # receiving a message
            safe_print(data["from"], ':', data['message'])
        elif data['action'] == 'block':
            # reply to a user-initiated block
            if data['status'] == 'MESSAGE_SELF':
                safe_print("Cannot block yourself.")
            elif data['status'] == 'USER_NOT_EXIST':
                safe_print("User does not exist.")
            else:
                safe_print("Block success.")
        elif data['action'] == 'unblock':
            # reply to a user-initiated unblock
            if data['status'] == 'MESSAGE_SELF':
                safe_print("Cannot unblock yourself.")
            elif data['status'] == 'USER_NOT_EXIST':
                safe_print("User does not exist.")
            else:
                safe_print("Unblock success.")
        elif data['action'] == 'broadcast':
            # reply to a user-initiated broadcast
            safe_print('broadcast success to', data['n_sent'], 'users.', data['n_blocked'],
                       'users blocked you so they can not see the message.')
        elif data['action'] == 'timeout':
            # client timed out by the server
            to_exit = True
            is_timeout = True
        elif data['action'] == 'whoelse':
            # reply to a user-initiated whoelse
            safe_print("Online users:")
            safe_print("\n".join(data['reply']))
        elif data['action'] == 'whoelsesince':
            # reply to a user-initiated whoelsesince
            safe_print("whoelsesince:")
            safe_print("\n".join(data['reply']))
        elif data['action'] == 'login_broadcast':
            # receive login braodcast
            safe_print(data['from'], 'is logged in.')
        elif data['action'] == 'logout_broadcast':
            # receive login braodcast
            safe_print(data['from'], 'is logged out.')
        elif data['action'] == 'startprivate':
            # receive login braodcast
            if data['reply'] == 'USER_NOT_EXIST':
                safe_print("startprivate: user does not exist.")
            elif data['reply'] == 'USER_SELF':
                safe_print("startprivate: cannot private yourself.")
            elif data['reply'] == 'USER_BLOCKED':
                safe_print("startprivate: that user blocked you.")
            elif data['reply'] == 'USER_OFFLINE':
                safe_print("startprivate: that user is offline.")
            elif data['reply'] == 'SUCCESS':
                address = data['address']
                port = int(data['port'])
                username = data['username']
                private_connect(address, port, username)
            else:
                safe_print("Unexpected reply.")
        else:
            # unexpected format
            safe_print(data)


# handles all outgoing data
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
            _, message = command.split(' ', 1)
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
        elif command.startswith("startprivate"):
            _, user = command.split()
            clientSocket.send(json.dumps({
                "action": "startprivate",
                "user": user
            }).encode())
        elif command.startswith("stopprivate"):
            _, user = command.split()
            private_disconnect(user)
        elif command.startswith("private"):
            _, user, message = command.split(' ', 2)
            private_message(user, message)


# start the interaction between client and server
def interact():
    global private_recv_socket
    recv_thread = threading.Thread(name="RecvHandler", target=recv_handler)
    recv_thread.daemon = True
    recv_thread.start()

    send_thread = threading.Thread(name="SendHandler", target=send_handler)
    send_thread.daemon = True
    send_thread.start()

    recv_thread = threading.Thread(name="PrivateRecvHandler", target=private_recv_handler)
    recv_thread.daemon = True
    recv_thread.start()

    while True:
        time.sleep(0.1)

        # when set true, exit the main thread
        if to_exit:
            exit(0)


# log in then start interaction if successfully authenticated
def log_in():
    global message
    clientSocket.send(message.encode())

    # wait for the reply from the server
    login_result = clientSocket.recv(1024)
    login_result = json.loads(login_result.decode())

    if login_result["action"] == 'login' and login_result["status"] == "SUCCESS":
        # successfully authenticated
        print("You are logged in")

        # register on logout cleanup
        atexit.register(logout)

        # start interaction
        interact()
    elif login_result["action"] == 'login' and login_result["status"] == "ALREADY_LOGGED_IN":
        print("You have already logged in.")
    elif login_result["action"] == 'login' and login_result["status"] == "INVALID_PASSWORD_BLOCKED":
        print("Invalid password. Your account has been blocked. Please try again later.")
    elif login_result["action"] == 'login' and login_result["status"] == "BLOCKED":
        print("Due to multiple consecutive fails to log in, you have been blocked.")
    elif login_result["action"] == 'login' and login_result["status"] == "INVALID_PASSWORD":
        # invalid password, try again
        message = json.dumps({
            "action": "login",
            "username": username,
            "password": input("Invalid password. Please try again:"),
            "private_port": private_recv_port
        })
        log_in()
    elif login_result["action"] == 'login' and login_result["status"] == "ALREADY_LOGGED_IN":
        print(login_result["status"])
    elif login_result["action"] == 'login' and login_result["status"] == "USERNAME_NOT_EXIST":
        print(login_result["status"])
    else:
        # things unexpected
        print("FATAL: unexpected message")
        exit(1)


# register keyboard interrupt handler
signal.signal(signal.SIGINT, keyboard_interrupt_handler)

if __name__ == "__main__":
    # start to authenticate user
    log_in()
