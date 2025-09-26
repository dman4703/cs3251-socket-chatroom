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

# end main

if __name__ == "__main__":
    main()
# end if