import socket
import threading
import sys
import argparse
from datetime import datetime, timedelta

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
    if 1 <= args.port <= 65535:
        sys.exit(1)
    # end if

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('127.0.0.1', args.port))
    server.listen()
    print(f"Server started on port {args.port}. Accepting connections")
    sys.stdout.flush()
    while True:
        connection, address = server.accept()

        connection.close()
    # end while
# end main

if __name__ == "__main__":
    main()
# end if