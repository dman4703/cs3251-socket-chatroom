import socket
import threading
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Chat Client")
    parser.add_argument('-join', action='store_true', help='Join the chat server')
    parser.add_argument('-host', type=str, required=True, help='Server IPv4 address')
    parser.add_argument('-port', type=int, required=True, help='Server port')
    parser.add_argument('-username', type=str, required=True, help='Display name, max 8 chars')
    parser.add_argument('-passcode', type=str, required=True, help='Passcode, max 5 chars')
    args = parser.parse_args()
    if not args.join:
        sys.exit(1)
    # end if
    if len(args.username) > 8:
        sys.exit(1)
    # end if
    if len(args.passcode) > 5:
        sys.exit(1)
    # end if
    if not args.passcode.isalnum():
        sys.exit(1)
    # end if

    # Connect to server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as clientSocket:
        clientSocket.connect((args.host, args.port))
        handshakeMessage = f"{args.passcode}\n{args.username}\n"
        clientSocket.sendall(handshakeMessage.encode())

        # Read connect 
        with clientSocket.makefile('r') as serverFile:
            serverGreeting = serverFile.readline().rstrip('\n')
            if serverGreeting == "Incorrect passcode":
                print(serverGreeting)
                sys.stdout.flush()
                return
            else:
                print(serverGreeting)
                sys.stdout.flush()
            # end if

            receiverThread = threading.Thread(target=receiveMessages, args=(serverFile,), daemon=True)
            receiverThread.start()

            # Read user input and send to server
            for rawLine in sys.stdin:
                messageText = rawLine.rstrip('\n')
                clientSocket.sendall(f"{messageText}\n".encode())
                if messageText == ':Exit':
                    break
                # end if
            # end for
        # end with
    # end with
# end main

if __name__ == "__main__":
    main()
# end if

def receiveMessages(serverFile):
    # Continuously read messages from the server and display them
    for rawLine in serverFile:
        messageText = rawLine.rstrip('\n')
        if messageText == '':
            continue
        # end if
        print(messageText)
        sys.stdout.flush()
    # end for
# end receiveMessages