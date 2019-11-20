# Python 3
# Usage: python3 server.py server_port block_duration timeout
# coding: utf-8
# modified from the starter code

from socket import *
import threading
import time
import json
from UserManager import UserManager
import sys
from typing import List, Dict
import atexit
import signal

# command line args
if len(sys.argv) != 4:
    print("invalid command line arguments")
    exit(0)
serverPort = int(sys.argv[1])
block_duration = int(sys.argv[2])
timeout = int(sys.argv[3])

t_lock = threading.Condition()
# will store clients info in this list
clients = []
# all unsent messages: from_user, to_user, message
pending_messages: List[Dict] = []
name_to_socket: Dict = dict()
addr_to_socket: Dict = dict()
# would communicate with clients after every second
UPDATE_INTERVAL = 1

# credential manager
user_manager = UserManager(block_duration, timeout)


def keyboard_interrupt_handler(signal, frame):
    print("\rServer is shutdown")
    exit(0)


signal.signal(signal.SIGINT, keyboard_interrupt_handler)


def send_message(from_user: str, to_user: str, message: str, broadcast=False):
    if to_user not in name_to_socket:
        print('ERROR', to_user, 'not exist')
        return
    to_user_socket = name_to_socket[to_user]
    to_user_socket.send(json.dumps({
        'action': 'receive_broadcast' if broadcast else 'receive_message',
        'from': from_user,
        'message': message
    }).encode())


# return a function for multi threading
def connection_handler(connection_socket, client_address):
    def real_connection_handler():
        while True:
            data = connection_socket.recv(1024)
            if not data:
                exit(0)
            sys.stdout.flush()
            # received data from the client, now we know who we are talking with
            data = data.decode()
            data = json.loads(data)
            action = data["action"]

            # get lock as we might me accessing some shared data structures
            with t_lock:
                # debugging code, uncomment to use
                print(client_address, ':', data)
                server_message = dict()
                server_message["action"] = action
                curr_user = user_manager.get_username(client_address)
                user_manager.refresh_user_timeout(curr_user)
                if action == 'login':
                    # store client information (IP and Port No) in list
                    username = data["username"]
                    password = data["password"]
                    clients.append(client_address)
                    status = user_manager.authenticate(username, password)
                    user_manager.set_address_username(client_address, username)
                    server_message["status"] = status
                    if status == 'SUCCESS':
                        name_to_socket[username] = connection_socket
                        addr_to_socket[client_address] = connection_socket
                elif action == 'logout':
                    # check if client already subscribed or not
                    user_manager.set_offline(user_manager.get_username(client_address))
                    if client_address in clients:
                        clients.remove(client_address)
                        server_message["reply"] = "logged out"
                    else:
                        server_message["reply"] = "You are not logged in"
                elif action == 'message':
                    username = data['user']
                    message = data['message']
                    if curr_user == username:
                        server_message['status'] = 'MESSAGE_SELF'
                    elif not user_manager.has_user(username):
                        server_message['status'] = 'USER_NOT_EXIST'
                    elif user_manager.is_blocked_user(username, curr_user):
                        server_message['status'] = 'USER_BLOCKED'
                    else:
                        server_message['status'] = 'SUCCESS'
                        if user_manager.is_online(username):
                            # send message to user
                            send_message(curr_user, username, message)
                        else:
                            pending_messages.append({
                                'from_user': curr_user,
                                'to_user': username,
                                'message': message
                            })
                elif action == 'broadcast':
                    message = data['message']
                    n_sent = 0
                    n_blocked = 0
                    for user in user_manager.all_users():
                        if user_manager.is_blocked_user(user, curr_user):
                            n_blocked += 1
                        elif not user_manager.is_online(user):
                            pass
                        elif user == curr_user:
                            pass
                        else:
                            n_sent += 1
                            send_message(curr_user, user, message, broadcast=True)
                    server_message['n_sent'] = n_sent
                    server_message['n_blocked'] = n_blocked
                elif action == 'block':
                    user_to_block = data['user']
                    if curr_user == user_to_block:
                        server_message['status'] = 'MESSAGE_SELF'
                    elif not user_manager.has_user(user_to_block):
                        server_message['status'] = 'USER_NOT_EXIST'
                    else:
                        server_message['status'] = 'SUCCESS'
                        user_manager.block(curr_user, user_to_block)
                elif action == 'unblock':
                    user_to_unblock = data['user']
                    if curr_user == user_to_unblock:
                        server_message['status'] = 'MESSAGE_SELF'
                    elif not user_manager.has_user(user_to_unblock):
                        server_message['status'] = 'USER_NOT_EXIST'
                    else:
                        server_message['status'] = 'SUCCESS'
                        user_manager.unblock(curr_user, user_to_unblock)
                elif action == 'whoelse':
                    online_users = user_manager.get_online_users()
                    online_users.remove(curr_user)
                    server_message['reply'] = list(online_users)
                elif action == 'whoelsesince':
                    users = user_manager.get_users_logged_in_since(int(data['since']))
                    if curr_user in users:
                        users.remove(curr_user)
                    server_message['reply'] = list(users)
                else:
                    server_message["reply"] = "Unknown action"
                # send message to the client
                connection_socket.send(json.dumps(server_message).encode())
                # notify the thread waiting
                t_lock.notify()

    return real_connection_handler


def recv_handler():
    global t_lock
    global clients
    global serverSocket
    print('Server is ready for service')
    while True:
        connection_socket, client_address = serverSocket.accept()
        print(connection_socket, client_address)

        socket_handler = connection_handler(connection_socket, client_address)

        socket_thread = threading.Thread(name=str(client_address), target=socket_handler)
        socket_thread.daemon = False
        socket_thread.start()


def send_handler():
    global t_lock
    global clients
    global serverSocket
    # go through the list of the subscribed clients and send them the current time after every 1 second
    while True:
        # get lock
        with t_lock:
            for message in pending_messages:
                if user_manager.is_online(message['to_user']):
                    send_message(message['from_user'], message['to_user'], message['message'])
                    pending_messages.remove(message)
            # time out users
            for user in user_manager.get_timed_out_users():
                if user in name_to_socket:
                    name_to_socket[user].send(json.dumps({
                        'action': 'timeout'
                    }).encode())
            # notify other thread
            t_lock.notify()
        # sleep for UPDATE_INTERVAL
        time.sleep(UPDATE_INTERVAL)


# we will use two sockets, one for sending and one for receiving
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('localhost', serverPort))
serverSocket.listen(1)

recv_thread = threading.Thread(name="RecvHandler", target=recv_handler)
recv_thread.daemon = True
recv_thread.start()

send_thread = threading.Thread(name="SendHandler", target=send_handler)
send_thread.daemon = True
send_thread.start()


def on_close():
    serverSocket.close()


atexit.register(on_close)
# this is the main thread
while True:
    time.sleep(0.1)
    user_manager.update()
