# Python 3.7
# Author: Bofei Wang
# Usage: python3 server.py server_port block_duration timeout
# coding: utf-8
# modified from the multi-threading sample code

import threading
import time
import json
import sys
import atexit
import signal
from socket import *
from typing import List, Dict
from UserManager import UserManager

# command line args
if len(sys.argv) != 4:
    print("Usage: python3 server.py server_port block_duration timeout")
    exit(0)
serverPort = int(sys.argv[1])
block_duration = int(sys.argv[2])
timeout = int(sys.argv[3])

# exclusive lock for multi threading
t_lock = threading.Condition()

# will store clients info in this list
clients = []

# all unsent messages: from_user, to_user, message
pending_messages: List[Dict] = []

# map username to connection socket
name_to_socket: Dict = dict()

# would communicate with clients after every second
UPDATE_INTERVAL = 1

# user manager manages all the user data
user_manager = UserManager(block_duration, timeout)


# catch the ctrl+c exit signal
def keyboard_interrupt_handler(signal, frame):
    print("\rServer is shutdown")
    exit(0)


# close the socket when exit
def on_close():
    serverSocket.close()


# helper function to send a message
def send_message(from_user: str, to_user: str, message: str, broadcast=False, login_broadcast=False,
                 logout_broadcast=False):
    if to_user not in name_to_socket:
        print('ERROR', to_user, 'not exist')
    else:
        to_user_socket = name_to_socket[to_user]
        action = 'receive_message'
        if broadcast:
            action = 'receive_broadcast'
        elif login_broadcast:
            action = 'login_broadcast'
        elif logout_broadcast:
            action = 'logout_broadcast'
        to_user_socket.send(json.dumps({
            'action': action,
            'from': from_user,
            'message': message
        }).encode())


# return a function as connection handler for a specific socket for multi threading
def connection_handler(connection_socket, client_address):
    def real_connection_handler():
        while True:
            data = connection_socket.recv(1024)
            if not data:
                # if data is empty, the socket is closed or is in the
                # process of closing. In this case, close this thread
                exit(0)

            # received data from the client, now we know who we are talking with
            data = data.decode()
            data = json.loads(data)
            action = data["action"]

            # get lock as we might me accessing some shared data structures
            with t_lock:
                # debugging code, uncomment to use
                # print(client_address, ':', data)

                # the data to reply to client
                server_message = dict()
                server_message["action"] = action

                # current user name
                curr_user = user_manager.get_username(client_address)

                # update the time out when user send anything to server
                user_manager.refresh_user_timeout(curr_user)

                if action == 'login':
                    # store client information (IP and Port No) in list
                    username = data["username"]
                    password = data["password"]
                    clients.append(client_address)
                    # auth the user and reply the status
                    status = user_manager.authenticate(username, password)
                    user_manager.set_address_username(client_address, username)
                    server_message["status"] = status
                    if status == 'SUCCESS':
                        # add the socket to the name-socket map
                        name_to_socket[username] = connection_socket
                        # broadcast new user login
                        for user in user_manager.all_users():
                            if user != username and user_manager.is_online(user):
                                send_message(username, user, '', login_broadcast=True)
                elif action == 'logout':
                    # check if client already subscribed or not
                    user_manager.set_offline(user_manager.get_username(client_address))
                    if client_address in clients:
                        clients.remove(client_address)
                        server_message["reply"] = "logged out"
                        # broadcast user logout
                        for user in user_manager.all_users():
                            if user != curr_user and user_manager.is_online(user):
                                send_message(curr_user, user, '', logout_broadcast=True)
                    else:
                        server_message["reply"] = "You are not logged in"
                elif action == 'message':
                    # user tries to send a message to other users
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
                            # user is online, send message to user
                            send_message(curr_user, username, message)
                        else:
                            # user is offline, add message to pending list
                            pending_messages.append({
                                'from_user': curr_user,
                                'to_user': username,
                                'message': message
                            })
                elif action == 'broadcast':
                    # broadcast the message to online unblocked users
                    # record the statistics
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
                    # remove the user who requested
                    online_users.remove(curr_user)
                    server_message['reply'] = list(online_users)
                elif action == 'whoelsesince':
                    users = user_manager.get_users_logged_in_since(int(data['since']))
                    if curr_user in users:
                        # remove the user who requested
                        users.remove(curr_user)
                    server_message['reply'] = list(users)
                else:
                    server_message["reply"] = "Unknown action"
                # send message to the client
                connection_socket.send(json.dumps(server_message).encode())
                # notify the thread waiting
                t_lock.notify()

    return real_connection_handler


# handles all incoming data and replies to those
def recv_handler():
    global t_lock
    global clients
    global serverSocket
    print('Server is up.')
    while True:
        # create a new connection for a new client
        connection_socket, client_address = serverSocket.accept()

        # create a new function handler for the client
        socket_handler = connection_handler(connection_socket, client_address)

        # create a new thread for the client socket
        socket_thread = threading.Thread(name=str(client_address), target=socket_handler)
        socket_thread.daemon = False
        socket_thread.start()


# handles all out going data that can not be handled by recev_dandler
def send_handler():
    global t_lock
    global clients
    global serverSocket
    while True:
        # get lock
        with t_lock:
            # check if any pending messages can be send to any users who is online
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

# register keyboard interrupt handler
signal.signal(signal.SIGINT, keyboard_interrupt_handler)

# register exist handler
atexit.register(on_close)

# this is the main thread
while True:
    time.sleep(0.1)

    # update any information of all user data
    user_manager.update()
