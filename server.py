import socket
import threading
import sys
import argparse
from datetime import datetime, timedelta

clients = {}
clientsLock = threading.Lock()

def main():
    parser = argparse.ArgumentParser(description="CS3251 Chat Server")
    parser.add_argument('-start', action='store_true', help='Start the server')
    parser.add_argument('-port', type=int, required=True, help='Listening port')
    parser.add_argument('-passcode', type=str, required=True, help='Shared passcode')
    args = parser.parse_args()
    if not args.start:
        sys.exit(1)
    # end if
    if len(args.passcode) > 5:
        sys.exit(1)
    # end if
    if not args.passcode.isalnum():
        sys.exit(1)
    # end if
    if not (1 <= args.port <= 65535):
        sys.exit(1)
    # end if

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind(('127.0.0.1', args.port))
    serverSocket.listen()
    print(f"Server started on port {args.port}. Accepting connections")
    sys.stdout.flush()
    while True:
        connectionSocket, _ = serverSocket.accept()
        clientThread = threading.Thread(
            target=handleClient,
            args=(connectionSocket, args.port, args.passcode),
            daemon=True
        )
        clientThread.start()
    # end while
# end main

if __name__ == "__main__":
    main()
# end if

def sendLine(clientSocket, messageText):
    """Send a newline-terminated message to a client socket."""
    try:
        clientSocket.sendall(f"{messageText}\n".encode())
    except OSError:
        # A failed send indicates a disconnected client, which can be ignored.
        pass
    # end try
# end sendLine

def broadcastLine(messageText, skipUser=None, includeSkip=False):
    """Broadcast a message to all connected clients with optional exclusions."""
    recipients = []
    with clientsLock:
        for username, socketInfo in clients.items():
            if username == skipUser and not includeSkip:
                continue
            # end if
            recipients.append(socketInfo)
        # end for
    # end with
    for clientSocket in recipients:
        sendLine(clientSocket, messageText)
    # end for
# end broadcastLine

def formatTime(hoursOffset=0):
    """Return the current time string with an optional hour offset."""
    timeValue = datetime.now() + timedelta(hours=hoursOffset)
    return timeValue.ctime()
# end formatTime

def removeClient(username):
    """Remove a client from the registry and close the associated socket."""
    clientSocket = None
    with clientsLock:
        clientSocket = clients.pop(username, None)
    # end with
    if clientSocket is not None:
        try:
            clientSocket.close()
        except OSError:
            pass
        # end try
    # end if
# end removeClient

def handleClient(connectionSocket, serverPort, sharedPasscode):
    # Authenticate and service a single connected client.
    username = None
    try:
        with connectionSocket.makefile('r') as connectionFile:
            try:
                receivedPasscode = connectionFile.readline().rstrip('\n')
                if not receivedPasscode:
                    connectionSocket.close()
                    return
                # end if
                username = connectionFile.readline().rstrip('\n')
            except Exception:
                connectionSocket.close()
                return
            # end try

            if not receivedPasscode.isalnum() or receivedPasscode != sharedPasscode:
                sendLine(connectionSocket, "Incorrect passcode")
                connectionSocket.close()
                return
            # end if

            with clientsLock:
                clients[username] = connectionSocket
            # end with

            sendLine(connectionSocket, f"Connected to 127.0.0.1 on port {serverPort}")
            print(f"{username} joined the chatroom")
            sys.stdout.flush()
            broadcastLine(f"{username} joined the chatroom", skipUser=username)

            for rawLine in connectionFile:
                messageText = rawLine.rstrip('\n')
                if messageText == '':
                    continue
                # end if
                if messageText.startswith(':Msg '):
                    messageParts = messageText.split(' ', 2)
                    if len(messageParts) >= 3:
                        targetUser = messageParts[1]
                        privateMessage = messageParts[2]
                        with clientsLock:
                            targetSocket = clients.get(targetUser)
                        # end with
                        if targetSocket is not None:
                            sendLine(targetSocket, f"[Message from {username}]: {privateMessage}")
                            print(f"{username}: send message to {targetUser}")
                            sys.stdout.flush()
                        # end if
                    # end if
                    continue
                # end if

                match messageText:
                    case ':Exit':
                        print(f"{username} left the chatroom")
                        sys.stdout.flush()
                        broadcastLine(f"{username} left the chatroom", skipUser=username)
                        break
                    case ':)':
                        formattedMessage = f"{username}: [feeling happy]"
                        print(formattedMessage)
                        sys.stdout.flush()
                        broadcastLine(formattedMessage, skipUser=username)
                    case ':(':
                        formattedMessage = f"{username}: [feeling sad]"
                        print(formattedMessage)
                        sys.stdout.flush()
                        broadcastLine(formattedMessage, skipUser=username)
                    case ':mytime':
                        formattedMessage = f"{username}: {formatTime()}"
                        print(formattedMessage)
                        sys.stdout.flush()
                        broadcastLine(formattedMessage, skipUser=username, includeSkip=True)
                    case ':+1hr':
                        formattedMessage = f"{username}: {formatTime(hoursOffset=1)}"
                        print(formattedMessage)
                        sys.stdout.flush()
                        broadcastLine(formattedMessage, skipUser=username, includeSkip=True)
                    case ':Users':
                        with clientsLock:
                            activeUsers = list(clients.keys())
                        # end with
                        usersListing = ", ".join(activeUsers)
                        sendLine(connectionSocket, f"Active Users: {usersListing}")
                        print(f"{username}: searched up active users")
                        sys.stdout.flush()
                    case _:
                        # regular message is default case
                        formattedMessage = f"{username}: {messageText}"
                        print(formattedMessage)
                        sys.stdout.flush()
                        broadcastLine(formattedMessage, skipUser=username)
                # end match
            # end for
        # end with
    finally:
        if username is not None:
            removeClient(username)
        # end if
    # end try
# end handleClient