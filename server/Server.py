# Sample code for Multi-Threaded Server
# Python 3
# Usage: python3 UDPserver3.py
# coding: utf-8
from socket import *
import threading
import time
import datetime as dt
import json
from UserManager import UserManager
import sys
from typing import List, Dict

# command line args
if len(sys.argv) != 4:
    print("invalid command line arguments")
    exit(0)
# server_port = int(sys.argv[1]) # TODO uncomment this
block_duration = int(sys.argv[2])
timeout = int(sys.argv[3])

# Server will run on this port
serverPort = 13856
t_lock = threading.Condition()
# will store clients info in this list
clients = []
# all unsent messages: from_user, to_user, message
pending_messages: List[Dict] = []
# would communicate with clients after every second
UPDATE_INTERVAL = 1

# credential manager
user_manager = UserManager(block_duration, timeout)


def send_message(from_user: str, to_user: str, message: str, broadcast=False):
    serverSocket.sendto(json.dumps({
        'action': 'receive_broadcast' if broadcast else 'receive_message',
        'from': from_user,
        'message': message
    }).encode(), user_manager.get_address(to_user))


def recv_handler():
    global t_lock
    global clients
    global clientSocket
    global serverSocket
    print('Server is ready for service')
    while True:
        data, client_address = serverSocket.recvfrom(2048)
        # received data from the client, now we know who we are talking with
        data = data.decode()
        data = json.loads(data)
        action = data["action"]

        # get lock as we might me accessing some shared data structures
        with t_lock:
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
            else:
                server_message["reply"] = "Unknown action"
            # send message to the client
            serverSocket.sendto(json.dumps(server_message).encode(), client_address)
            # notify the thread waiting
            t_lock.notify()


def send_handler():
    global t_lock
    global clients
    global clientSocket
    global serverSocket
    global timeout
    # go through the list of the subscribed clients and send them the current time after every 1 second
    while 1:
        # get lock
        with t_lock:
            for message in pending_messages:
                if user_manager.is_online(message['to_user']):
                    send_message(message['from_user'], message['to_user'], message['message'])
                    pending_messages.remove(message)
            # time out users
            for user in user_manager.get_timed_out_users():
                serverSocket.sendto(json.dumps({
                    'action': 'timeout'
                }).encode(), user_manager.get_address(user))
            # notify other thread
            t_lock.notify()
        # sleep for UPDATE_INTERVAL
        time.sleep(UPDATE_INTERVAL)


# we will use two sockets, one for sending and one for receiving
clientSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
serverSocket.bind(('localhost', serverPort))

recv_thread = threading.Thread(name="RecvHandler", target=recv_handler)
recv_thread.daemon = True
recv_thread.start()

send_thread = threading.Thread(name="SendHandler", target=send_handler)
send_thread.daemon = True
send_thread.start()
# this is the main thread
while True:
    time.sleep(0.1)
    user_manager.update()
