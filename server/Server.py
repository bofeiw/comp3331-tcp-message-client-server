# Sample code for Multi-Threaded Server
# Python 3
# Usage: python3 UDPserver3.py
# coding: utf-8
from socket import *
import threading
import time
import datetime as dt
import json
from CredentialManager import CredentialManager
from UserManager import UserManager
import sys

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
# would communicate with clients after every second
UPDATE_INTERVAL = 1

# credential manager
credential_manager = CredentialManager(block_duration, timeout)
user_manager = UserManager(credential_manager)


def recv_handler():
    global t_lock
    global clients
    global clientSocket
    global serverSocket
    print('Server is ready for service')
    while True:
        message, client_address = serverSocket.recvfrom(2048)
        # received data from the client, now we know who we are talking with
        message = message.decode()
        message = json.loads(message)
        action = message["action"]

        # get lock as we might me accessing some shared data structures
        with t_lock:
            currtime = dt.datetime.now()
            date_time = currtime.strftime("%d/%m/%Y, %H:%M:%S")
            print('Received request from', client_address[0], 'listening at', client_address[1], ':', message,
                  'at time ', date_time)
            server_message = dict()
            server_message["type"] = "response"
            server_message["action"] = action
            if action == 'login':
                # store client information (IP and Port No) in list
                username = message["username"]
                password = message["password"]
                clients.append(client_address)
                status = credential_manager.authenticate(username, password)
                credential_manager.set_address_username(client_address, username)
                server_message["status"] = status
            elif action == 'logout':
                # check if client already subscribed or not
                credential_manager.set_offline(credential_manager.get_username(client_address))
                if client_address in clients:
                    clients.remove(client_address)
                    server_message["reply"] = "logged out"
                else:
                    server_message["reply"] = "You are not logged in"
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
            for i in clients:
                currtime = dt.datetime.now()
                date_time = currtime.strftime("%d/%m/%Y, %H:%M:%S")
                message = 'Current time is ' + date_time
                # clientSocket.sendto(message.encode(), i)
                # print('Sending time to', i[0], 'listening at', i[1], 'at time ', date_time)
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
    credential_manager.update()
