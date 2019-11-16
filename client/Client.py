# Python 3
# Usage: python3 UDPClient3.py localhost 12000
# coding: utf-8
from socket import *
import sys
import json

# Server would be running on the same host as Client
serverName = "localhost"
serverPort = 13856

clientSocket = socket(AF_INET, SOCK_DGRAM)

message = json.dumps({
    "action": "login",
    "username": "a",
    "password": "a"
})

clientSocket.sendto(message.encode(), (serverName, serverPort))
# wait for the reply from the server
login_result, server_address = clientSocket.recvfrom(2048)
login_result = json.loads(login_result.decode())

if login_result["action"] == 'login' and login_result["status"] == "SUCCESS":
    print("You are logged in")
    # # Wait for 10 back to back messages from server
    # for i in range(10):
    #     login_result, server_address = clientSocket.recvfrom(2048)
    #     print(login_result.decode())
elif login_result["action"] == 'login' and login_result["status"] == "ALREADY_LOGGED_IN":
    print(login_result["status"])
elif login_result["action"] == 'login' and login_result["status"] == "BLOCKED":
    print(login_result["status"])
elif login_result["action"] == 'login' and login_result["status"] == "INVALID_PASSWORD":
    print(login_result["status"])
elif login_result["action"] == 'login' and login_result["status"] == "ALREADY_LOGGED_IN":
    print(login_result["status"])
elif login_result["action"] == 'login' and login_result["status"] == "ALREADY_LOGGED_IN":
    print(login_result["status"])
else:
    print(login_result["status"])
    print("FATAL: could not connect to server")
    exit(1)

# prepare to exit. Send Unsubscribe message to server
message = json.dumps({
    "action": "logout",
    "username": "a",
    "password": "a"
})
clientSocket.sendto(message.encode(), (serverName, serverPort))
clientSocket.close()
# Close the socket
