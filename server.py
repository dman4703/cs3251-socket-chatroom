import argparse
import select
import socket
import sys
from datetime import datetime, timedelta

SERVER_HOST = "127.0.0.1"


def format_time(hours_offset: int = 0) -> str:
    """Return the current time string with an optional hour offset."""
    current_time = datetime.now() + timedelta(hours=hours_offset)
    return current_time.ctime()


def send_line(connection: socket.socket, message_text: str) -> None:
    """Send a newline-terminated message to a client socket."""
    try:
        connection.sendall(f"{message_text}\n".encode())
    except OSError:
        pass


def broadcast_line(
    active_clients: dict[str, socket.socket],
    pending_clients: dict[str, socket.socket],
    pending_messages: list[str],
    message_text: str,
    *,
    skip_user: str | None = None,
    include_skip: bool = False,
    include_pending: bool = False,
) -> None:
    """Broadcast a message to selected client connections."""
    recipients: list[socket.socket] = []
    for username, connection in active_clients.items():
        if username == skip_user and not include_skip:
            continue
        recipients.append(connection)
    if include_pending:
        for username, connection in pending_clients.items():
            if username == skip_user and not include_skip:
                continue
            recipients.append(connection)
    if not recipients and skip_user is not None and not include_skip:
        pending_messages.append(message_text)
    for connection in recipients:
        send_line(connection, message_text)


def close_connection(
    active_clients: dict[str, socket.socket],
    pending_clients: dict[str, socket.socket],
    pending_messages: list[str],
    client_states: dict[socket.socket, dict],
    connection: socket.socket,
    *,
    announce: bool = False,
    include_pending_recipients: bool = False,
) -> None:
    """Remove a connection from tracking structures and optionally announce."""
    state = client_states.pop(connection, None)
    username = None
    pending_exit = False
    if state is not None:
        username = state.get("username")
        pending_exit = state.get("pending_exit", False)
    if username:
        if active_clients.get(username) is connection:
            active_clients.pop(username, None)
        if pending_clients.get(username) is connection:
            pending_clients.pop(username, None)
        if announce and not pending_exit:
            print(f"{username} left the chatroom")
            sys.stdout.flush()
            broadcast_line(
                active_clients,
                pending_clients,
                pending_messages,
                f"{username} left the chatroom",
                skip_user=username,
                include_pending=include_pending_recipients,
            )
    try:
        connection.close()
    except OSError:
        pass


def finalize_pending_exits(
    active_clients: dict[str, socket.socket],
    pending_clients: dict[str, socket.socket],
    pending_messages: list[str],
    client_states: dict[socket.socket, dict],
) -> None:
    """Close all pending-exit connections once no active clients remain."""
    for connection in list(pending_clients.values()):
        close_connection(active_clients, pending_clients, pending_messages, client_states, connection)


def accept_connection(
    server_socket: socket.socket,
    client_states: dict[socket.socket, dict],
) -> socket.socket:
    connection, _ = server_socket.accept()
    connection.setblocking(False)
    client_states[connection] = {
        "buffer": "",
        "username": None,
        "authenticated": False,
        "expected": "passcode",
        "passcode": None,
        "pending_exit": False,
    }
    return connection


def process_command(
    active_clients: dict[str, socket.socket],
    pending_clients: dict[str, socket.socket],
    pending_messages: list[str],
    client_states: dict[socket.socket, dict],
    connection: socket.socket,
    message_text: str,
) -> None:
    """Handle a single authenticated command from a client."""
    state = client_states[connection]
    username = state["username"]

    if message_text.startswith(":Msg "):
        parts = message_text.split(" ", 2)
        if len(parts) >= 3:
            target_user, private_message = parts[1], parts[2]
            target_connection = active_clients.get(target_user) or pending_clients.get(target_user)
            if target_connection is not None:
                send_line(target_connection, f"[Message from {username}]: {private_message}")
                print(f"{username}: send message to {target_user}")
                sys.stdout.flush()
        return

    match message_text:
        case ":Exit":
            if not state.get("pending_exit"):
                state["pending_exit"] = True
                if username in active_clients:
                    pending_clients[username] = active_clients.pop(username)
                else:
                    pending_clients[username] = connection
                print(f"{username} left the chatroom")
                sys.stdout.flush()
            broadcast_line(
                active_clients,
                pending_clients,
                pending_messages,
                f"{username} left the chatroom",
                skip_user=username,
                include_pending=True,
            )
            if not active_clients:
                finalize_pending_exits(active_clients, pending_clients, pending_messages, client_states)
        case ":)":
            formatted = f"{username}: [feeling happy]"
            print(formatted)
            sys.stdout.flush()
            broadcast_line(active_clients, pending_clients, pending_messages, formatted, skip_user=username)
        case ":(":
            formatted = f"{username}: [feeling sad]"
            print(formatted)
            sys.stdout.flush()
            broadcast_line(active_clients, pending_clients, pending_messages, formatted, skip_user=username)
        case ":mytime":
            formatted = f"{username}: {format_time()}"
            print(formatted)
            sys.stdout.flush()
            broadcast_line(active_clients, pending_clients, pending_messages, formatted, skip_user=username, include_skip=True)
        case ":+1hr":
            formatted = f"{username}: {format_time(hours_offset=1)}"
            print(formatted)
            sys.stdout.flush()
            broadcast_line(
                active_clients,
                pending_clients,
                pending_messages,
                formatted,
                skip_user=username,
                include_skip=True,
                include_pending=True,
            )
        case ":Users":
            users_listing = ", ".join(active_clients.keys())
            send_line(connection, f"Active Users: {users_listing}")
            print(f"{username}: searched up active users")
            sys.stdout.flush()
        case _:
            formatted = f"{username}: {message_text}"
            print(formatted)
            sys.stdout.flush()
            broadcast_line(active_clients, pending_clients, pending_messages, formatted, skip_user=username)


def main() -> None:
    parser = argparse.ArgumentParser(description="CS3251 Chat Server")
    parser.add_argument("-start", action="store_true", help="Start the server")
    parser.add_argument("-port", type=int, required=True, help="Listening port")
    parser.add_argument("-passcode", type=str, required=True, help="Shared passcode")
    args = parser.parse_args()

    if not args.start:
        sys.exit(1)
    if len(args.passcode) > 5:
        sys.exit(1)
    if not args.passcode.isalnum():
        sys.exit(1)
    if not (1 <= args.port <= 65535):
        sys.exit(1)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, args.port))
    server_socket.listen()
    server_socket.setblocking(False)

    active_clients: dict[str, socket.socket] = {}
    pending_clients: dict[str, socket.socket] = {}
    pending_messages: list[str] = []
    client_states: dict[socket.socket, dict] = {}

    print(f"Server started on port {args.port}. Accepting connections")
    sys.stdout.flush()

    try:
        while True:
            monitored = [server_socket] + list(client_states.keys())
            readable, _, exceptional = select.select(monitored, [], monitored, 1.0)

            for sock in readable:
                if sock is server_socket:
                    while True:
                        try:
                            accept_connection(server_socket, client_states)
                        except BlockingIOError:
                            break
                    continue

                state = client_states.get(sock)
                if state is None:
                    continue

                try:
                    data = sock.recv(4096)
                except OSError:
                    close_connection(active_clients, pending_clients, pending_messages, client_states, sock, announce=True, include_pending_recipients=True)
                    continue

                if not data:
                    close_connection(active_clients, pending_clients, pending_messages, client_states, sock, announce=True, include_pending_recipients=True)
                    continue

                state["buffer"] += data.decode()
                while "\n" in state["buffer"]:
                    line, remainder = state["buffer"].split("\n", 1)
                    state["buffer"] = remainder
                    message_text = line.rstrip("\r")

                    if not state["authenticated"]:
                        if state["expected"] == "passcode":
                            if not message_text:
                                close_connection(active_clients, pending_clients, pending_messages, client_states, sock)
                                break
                            state["passcode"] = message_text
                            state["expected"] = "username"
                            continue

                        if state["expected"] == "username":
                            username = message_text
                            passcode = state.get("passcode")
                            if passcode != args.passcode or not passcode or not username:
                                send_line(sock, "Incorrect passcode")
                                close_connection(active_clients, pending_clients, pending_messages, client_states, sock)
                                break
                            if not username.isalnum() or len(username) > 8:
                                close_connection(active_clients, pending_clients, pending_messages, client_states, sock)
                                break
                            if username in active_clients or username in pending_clients:
                                close_connection(active_clients, pending_clients, pending_messages, client_states, sock)
                                break

                            state["username"] = username
                            state["authenticated"] = True
                            state.pop("passcode", None)
                            state["expected"] = None

                            active_clients[username] = sock
                            send_line(sock, f"Connected to {SERVER_HOST} on port {args.port}")
                            print(f"{username} joined the chatroom")
                            sys.stdout.flush()
                            broadcast_line(
                                active_clients,
                                pending_clients,
                                pending_messages,
                                f"{username} joined the chatroom",
                                skip_user=username,
                            )
                            if pending_messages:
                                for stored_message in pending_messages:
                                    send_line(sock, stored_message)
                                pending_messages.clear()
                            continue

                    else:
                        if message_text == "":
                            continue
                        process_command(active_clients, pending_clients, pending_messages, client_states, sock, message_text)

            for sock in exceptional:
                if sock is server_socket:
                    continue
                close_connection(active_clients, pending_clients, pending_messages, client_states, sock, announce=True, include_pending_recipients=True)
    finally:
        for connection in list(client_states.keys()):
            close_connection(active_clients, pending_clients, pending_messages, client_states, connection)
        try:
            server_socket.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()

