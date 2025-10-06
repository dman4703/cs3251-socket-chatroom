import socket
import threading
import sys
import argparse
from datetime import datetime, timedelta

# Global client tracking
clients = {}  # Active clients: username -> socket
pendingClients = {}  # Clients who have exited but may need final messages
pendingMessages = []  # Messages to send to next joining client
clientsLock = threading.Lock()

def sendLine(clientSocket, messageText):
    """
    Send a newline-terminated message to a client socket.
    Handles OSError gracefully when client is disconnected.
    """
    try:
        clientSocket.sendall(f"{messageText}\n".encode())
    except OSError:
        # A failed send indicates a disconnected client, which can be ignored
        pass
    # end try
# end sendLine

def broadcastLine(messageText, skipUser=None, includeSkip=False, includePending=False):
    """
    Broadcast a message to all connected clients with optional exclusions.
    
    Args:
        messageText: Message to broadcast
        skipUser: Username to potentially skip
        includeSkip: If True, include the skipUser in broadcast
        includePending: If True, also send to pending clients
    """
    recipients = []
    with clientsLock:
        # Add active clients to recipients
        for username, socketInfo in clients.items():
            if username == skipUser and not includeSkip:
                continue
            # end if
            recipients.append(socketInfo)
        # end for
        
        # Add pending clients if requested
        if includePending:
            for username, socketInfo in pendingClients.items():
                if username == skipUser and not includeSkip:
                    continue
                # end if
                recipients.append(socketInfo)
            # end for
        # end if
        
        # Store message for future clients if no active recipients exist
        if not recipients and not includePending and skipUser is not None:
            pendingMessages.append(messageText)
        # end if
    # end with
    
    for clientSocket in recipients:
        sendLine(clientSocket, messageText)
    # end for
# end broadcastLine

def formatTime(hoursOffset=0):
    """
    Return the current time string with an optional hour offset.
    
    Args:
        hoursOffset: Number of hours to offset from current time
    """
    timeValue = datetime.now() + timedelta(hours=hoursOffset)
    return timeValue.ctime()
# end formatTime

def removeClient(username, announceDeparture=False):
    """
    Remove a client from the registry and close the associated socket.
    
    Args:
        username: Username of client to remove
        announceDeparture: If True, broadcast departure message
    """
    clientSocket = None
    isPending = False
    
    with clientsLock:
        # Check if client is in active or pending lists
        if username in clients:
            clientSocket = clients.pop(username, None)
        elif username in pendingClients:
            clientSocket = pendingClients.pop(username, None)
            isPending = True
        # end if
    # end with
    
    if clientSocket is not None:
        try:
            clientSocket.close()
        except OSError:
            pass
        # end try
        
        # Announce departure if requested and not already pending
        if announceDeparture and not isPending:
            print(f"{username} left the chatroom")
            sys.stdout.flush()
            broadcastLine(f"{username} left the chatroom", skipUser=username, includePending=True)
        # end if
    # end if
# end removeClient

def checkAndCleanupPendingClients():
    """
    Check if any active clients remain. If not, close all pending clients.
    """
    with clientsLock:
        if len(clients) == 0 and len(pendingClients) > 0:
            # No active clients remain, close all pending clients
            pendingUsernames = list(pendingClients.keys())
            for username in pendingUsernames:
                clientSocket = pendingClients.pop(username, None)
                if clientSocket:
                    try:
                        clientSocket.close()
                    except OSError:
                        pass
                    # end try
                # end if
            # end for
        # end if
    # end with
# end checkAndCleanupPendingClients

def handleClient(connectionSocket, serverPort, sharedPasscode):
    """
    Authenticate and service a single connected client.
    Handles all client commands and manages client lifecycle.
    
    Args:
        connectionSocket: The client's socket connection
        serverPort: Port number the server is running on
        sharedPasscode: Required passcode for authentication
    """
    username = None
    isPendingExit = False
    
    try:
        with connectionSocket.makefile('r') as connectionFile:
            # Authentication phase
            try:
                receivedPasscode = connectionFile.readline().rstrip('\n')
                if not receivedPasscode:
                    connectionSocket.close()
                    return
                # end if
                username = connectionFile.readline().rstrip('\n')
                if not username:
                    connectionSocket.close()
                    return
                # end if
            except Exception:
                connectionSocket.close()
                return
            # end try

            # Validate passcode
            if not receivedPasscode.isalnum() or receivedPasscode != sharedPasscode:
                sendLine(connectionSocket, "Incorrect passcode")
                connectionSocket.close()
                return
            # end if
            
            # Validate username format
            if not username.isalnum() or len(username) > 8:
                connectionSocket.close()
                return
            # end if
            
            # Check for duplicate username
            with clientsLock:
                if username in clients or username in pendingClients:
                    # Username already taken
                    connectionSocket.close()
                    return
                # end if
                # Register the client
                clients[username] = connectionSocket
            # end with

            # Send successful connection message
            sendLine(connectionSocket, f"Connected to 127.0.0.1 on port {serverPort}")
            print(f"{username} joined the chatroom")
            sys.stdout.flush()
            
            # Broadcast join message to others
            broadcastLine(f"{username} joined the chatroom", skipUser=username)
            
            # Send any pending messages to the new client
            with clientsLock:
                if pendingMessages:
                    for message in pendingMessages:
                        sendLine(connectionSocket, message)
                    # end for
                    pendingMessages.clear()
                # end if
            # end with

            # Main message processing loop
            for rawLine in connectionFile:
                messageText = rawLine.rstrip('\n')
                if messageText == '':
                    continue
                # end if
                
                # Handle private messages
                if messageText.startswith(':Msg '):
                    messageParts = messageText.split(' ', 2)
                    if len(messageParts) >= 3:
                        targetUser = messageParts[1]
                        privateMessage = messageParts[2]
                        with clientsLock:
                            # Check both active and pending clients
                            targetSocket = clients.get(targetUser) or pendingClients.get(targetUser)
                        # end with
                        if targetSocket is not None:
                            sendLine(targetSocket, f"[Message from {username}]: {privateMessage}")
                            print(f"{username}: send message to {targetUser}")
                            sys.stdout.flush()
                        # end if
                    # end if
                    continue
                # end if

                # Handle other commands
                match messageText:
                    case ':Exit':
                        # Move client to pending state
                        with clientsLock:
                            if username in clients:
                                pendingClients[username] = clients.pop(username)
                                isPendingExit = True
                            # end if
                        # end with
                        
                        print(f"{username} left the chatroom")
                        sys.stdout.flush()
                        broadcastLine(f"{username} left the chatroom", skipUser=username, includePending=True)
                        
                        # Check if we need to cleanup pending clients
                        checkAndCleanupPendingClients()
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
                        # Send to all including pending clients
                        broadcastLine(formattedMessage, skipUser=username, includeSkip=True, includePending=True)
                        
                    case ':Users':
                        with clientsLock:
                            activeUsers = list(clients.keys())
                        # end with
                        usersListing = ", ".join(activeUsers)
                        sendLine(connectionSocket, f"Active Users: {usersListing}")
                        print(f"{username}: searched up active users")
                        sys.stdout.flush()
                        
                    case _:
                        # Regular message is default case
                        formattedMessage = f"{username}: {messageText}"
                        print(formattedMessage)
                        sys.stdout.flush()
                        broadcastLine(formattedMessage, skipUser=username)
                # end match
            # end for
        # end with
    except Exception as e:
        # Handle any unexpected errors
        pass
    finally:
        # Clean up the client connection
        if username is not None:
            # Remove from active or pending clients
            with clientsLock:
                if username in pendingClients:
                    pendingClients.pop(username, None)
                    isPendingExit = True
                # end if
            # end with
            
            # Announce unexpected departure if not a normal exit
            if not isPendingExit:
                removeClient(username, announceDeparture=True)
            else:
                removeClient(username, announceDeparture=False)
            # end if
            
            # Check if cleanup is needed
            checkAndCleanupPendingClients()
        # end if
    # end try
# end handleClient

def main():
    """
    Main server function that sets up the server socket and accepts client connections.
    """
    parser = argparse.ArgumentParser(description="CS3251 Chat Server")
    parser.add_argument('-start', action='store_true', help='Start the server')
    parser.add_argument('-port', type=int, required=True, help='Listening port')
    parser.add_argument('-passcode', type=str, required=True, help='Shared passcode')
    args = parser.parse_args()
    
    # Validate arguments
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

    # Create and configure server socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Enable socket reuse to avoid "Address already in use" errors
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind(('127.0.0.1', args.port))
    serverSocket.listen()
    
    print(f"Server started on port {args.port}. Accepting connections")
    sys.stdout.flush()
    
    try:
        while True:
            # Accept new client connections
            connectionSocket, _ = serverSocket.accept()
            # Create a new thread for each client
            clientThread = threading.Thread(
                target=handleClient,
                args=(connectionSocket, args.port, args.passcode),
                daemon=True
            )
            clientThread.start()
        # end while
    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        print("\nServer shutting down...")
        sys.stdout.flush()
    finally:
        serverSocket.close()
    # end try
# end main

if __name__ == "__main__":
    main()
# end if