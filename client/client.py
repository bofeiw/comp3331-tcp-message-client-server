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
from socket import *


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

# get the username and password and login
username = input("username: ")
message = json.dumps({
    "action": "login",
    "username": username,
    "password": input("password: ")
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


# handles all incoming data and selectively display useful information to user
def recv_handler():
    global to_exit, is_timeout
    while True:
        login_result = clientSocket.recv(1024)
        data = json.loads(login_result.decode())
        print('\r', end='')
        if data['action'] == 'message':
            # reply to a user-initiated message
            if data['status'] == 'MESSAGE_SELF':
                print("Cannot message yourself.")
            elif data['status'] == 'USER_NOT_EXIST':
                print("User does not exist.")
            elif data['status'] == 'USER_BLOCKED':
                print("That user blocked you.")
            elif data['status'] == 'SUCCESS':
                # message sent successfully
                pass
        elif data['action'] in ['receive_message', 'receive_broadcast']:
            # receiving a message
            print(data["from"], ':', data['message'])
        elif data['action'] == 'block':
            # reply to a user-initiated block
            if data['status'] == 'MESSAGE_SELF':
                print("Cannot block yourself.")
            elif data['status'] == 'USER_NOT_EXIST':
                print("User does not exist.")
            else:
                print("Block success.")
        elif data['action'] == 'unblock':
            # reply to a user-initiated unblock
            if data['status'] == 'MESSAGE_SELF':
                print("Cannot unblock yourself.")
            elif data['status'] == 'USER_NOT_EXIST':
                print("User does not exist.")
            else:
                print("Unblock success.")
        elif data['action'] == 'broadcast':
            # reply to a user-initiated broadcast
            print('broadcast success to', data['n_sent'], 'users.', data['n_blocked'],
                  'users blocked you so they can not see the message.')
        elif data['action'] == 'timeout':
            # client timed out by the server
            to_exit = True
            is_timeout = True
        elif data['action'] == 'whoelse':
            # reply to a user-initiated whoelse
            print("Online users:")
            print("\n".join(data['reply']))
        elif data['action'] == 'whoelsesince':
            # reply to a user-initiated whoelsesince
            print("whoelsesince:")
            print("\n".join(data['reply']))
        else:
            # unexpected format
            print(data)
        print('> ', end='')

        # flush the stdout
        sys.stdout.flush()


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


# start the interaction between client and server
def interact():
    recv_thread = threading.Thread(name="RecvHandler", target=recv_handler)
    recv_thread.daemon = True
    recv_thread.start()

    send_thread = threading.Thread(name="SendHandler", target=send_handler)
    send_thread.daemon = True
    send_thread.start()

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
            "password": input("Invalid password. Please try again:")
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
