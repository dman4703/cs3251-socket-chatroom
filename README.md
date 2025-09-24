# Multi-Client Chatroom with Python Sockets

**Course:** CS3251 (Fall 2025)  
**Georgia Institute of Technology**

---

## Objective

* Understand the creation of sockets.
* Understand that application protocols are often simple plain-text messages with special meaning.
* Understand how to parse simple text commands.

---

## Introduction

In this assignment, you will create a chat room on a single computer where you and your (imaginary) friends can chat with each other. The following steps will be required to achieve this:

1. Create a **server** program that runs on a specific port passed via the command line.
2. Create a **client** program that can join this server.
3. The client needs a **display name** and a **passcode** to enter the chat room.

   * Assume all clients use the same passcode but a different display name.
   * The passcode is restricted to a **maximum of 5 alphanumeric characters**; anything over 5 is invalid.
   * The display name is a **maximum of 8 characters** long.
4. The job of the server is to accept connections from clients, get their display name and passcode (in plaintext), verify that the passcode is correct, and then allow clients into the chat room.
5. When any client sends a message, the display name is shown before the message, followed by a colon (`:`), and the message is delivered to **all other current clients**.
6. Clients can type any text message, or one of the following **shortcut codes** to display specific text:

   * type `:)` to display `[feeling happy]`
   * type `:(` → to display `[feeling sad]`
   * type `:mytime` to display the current time
   * type `:+1hr` to display the current time + 1 hour
     * **Time format** for `:mytime` and `:+1hr`: `Weekday Month Day Time Year` (e.g., `Mon Aug 13 08:23:14 2012`).
   * type `:Users` to display a list of all active users.
   * type `:Msg <username> <message>` to send a private message to a specific user.
   * type `:Exit` to close your connection and terminate the client.
   * Fun and not graded: `\` overrides the next word until a space or newline; e.g., `\:mytime` prints `:mytime` instead of the actual time.

---

## What will you learn?

* Basic socket programming to create a client–server application.
* How multiple clients connect to a single server.
* How to keep multiple persistent TCP connections alive.
* Text parsing to develop a custom application-layer protocol.

---

## Which programming language to use?

You are required to use **Python** for this assignment. Your code will be tested on an **Ubuntu 22.04** environment. You may set up a virtual machine (VM) to test your code locally, however you prefer.

Helpful setup guides:

* VirtualBox (Windows/Linux): [https://ubuntu.com/tutorials/how-to-run-ubuntu-desktop-on-a-virtual-machine-using-virtualbox#1-overview](https://ubuntu.com/tutorials/how-to-run-ubuntu-desktop-on-a-virtual-machine-using-virtualbox#1-overview)
* Multipass (macOS): [https://documentation.ubuntu.com/multipass/latest/tutorial](https://documentation.ubuntu.com/multipass/latest/tutorial)
* Argument parsing in Python (`argparse`): [https://docs.python.org/3/library/argparse.html](https://docs.python.org/3/library/argparse.html)

> You can find Python starter files with some instructions on **Canvas** under **Files → PA1.zip**.

---

## Instructions / Expected Outputs

The autograder expects a **very specific output** from your programs. Please make sure that you follow all conventions and **don’t add extra spaces/newlines** in your output. As a rule of thumb, there should be **no empty lines** in your program’s output, and spaces should be added **after a username**. For example: `<username>: message` instead of `<username>:message`.

There should also **not** be any output from your own program on your client (such as debugging prints).

### Connection Establishment and Password Checking — Single Client

> **Note:** The passcode will be restricted to a maximum of 5 letters.

You will create two programs: a **client** and a **server**. Each program takes the following CLI parameters:

* The **Client** takes the server IP address and listening port, the username, and the password (all clients use the same password).
* The **Server** takes its listening port and the password.

**If the password is correct**, the client should print `Connected to <host> on port <port>`.

**Otherwise**, it should receive the failur message `Incorrect passcode`.

Whenever a new client successfully joins the chatroom, **all other clients** should receive a message indicating the username of the new user that has just joined the chat room (see below).
```
Command: python3 server.py -start -port <port> -passcode <passcode>
Output: Server started on port <port>. Accepting connections
```
```
Command: python3 client.py -join -host <host> -port <port> -username <username> -passcode <passcode>
Output (on Server): <username> joined the chatroom
Output (on new Client): Connected to <host> on port <port>
```

**Resource**: [Sample code for providing command line arguments to a python application](https://docs.python.org/3/library/argparse.html)

### Connection Establishment and Password Checking — Multiple Clients

The server should handle multiple clients connecting to it. This means that by running the above client command again (with a different username), the server should behave similarly. The server should also inform the already-connected clients that a new client has joined.

```
Command: python3 client.py -join -host <host> -port <port> -username <username2> -passcode <passcode>
Output (on Server): <username2> joined the chatroom
Output (on new Client): Connected to <host> on port <port>
Output (on all other clients): <username2> joined the chatroom
```

* You **don’t** have to check for unique usernames (test cases will use unique names).
* A connected client should maintain a **persistent TCP connection** with the server thats terminated only when the user types `:Exit`.
* A client is removed **only** if it executes the `:Exit` command (i.e., don’t assume a client will be forcibly terminated).

### Chat Functionality

After successfully connecting to the server, clients should be able to type messages that get sent to the server when the user enters a newline. All text before the newline should be sent to the server, displayed on the server’s screen, and broadcasted and displayed on the screens of all other clients.

```
Command (on a connected client with username: <username>): Hello Room
Output (on Server): <username>: Hello Room
Output (on all other clients): <username>: Hello Room
```

> You don’t have to consider messages longer than **100 characters**. No need to test exceeding 100 characters or handle arbitrarily long inputs (these cases are not tested).

### Chat Shortcuts

As discussed earlier, clients should be able to send shortcuts that are translated to text. Emotion shortcuts ‘:)‘ and ‘:(‘ should be broadcast to the server and all other clients, excluding the original sender.

```
Command (on a connected client): :)
Output (on Server): <username>: [feeling happy]
Output (on all other clients): <username>: [feeling happy]
```

The time shortcuts (:mytime and :+1hr) should be broadcast to all connected clients, including the original sender.

```
Command (on a connected client): :mytime
Output (on Server): <username>: Wed Sep 24 12:31:44 2025
Output (on all clients, including sender): <username>: Wed Sep 24 12:31:44 2025
```

### Additional Chat Commands
Additional commands are available for listing users and sending private messages. `:Users` should specify the list of all actively connected clients, and display them in a comma-separated string with the prefix `Active Users:` (shown below)

```
Command (on a connected client, <username>): :Users
Output (on the same client <username>): Active Users: <username1>, <username2>, <username3>
Output (on Server): <username>: searched up active users
```

`:Msg <username> <message>` sends a private message to a specific user as shown below. We would not test sending messages to a non-existent user.

```
Command (on a connected client, <username>): :Msg <username2> CS3251 is awesome
Output (on a connected client, <username2>): [Message from <username>]: CS3251 is awesome
Output (on Server): <username>: send message to <username2>
```

### Leaving Chatroom

As discussed earlier, clients must be able to disconnect as well. To do this, the client should be able to type `:Exit` to disconnect. All other clients should see a message that this client left the chatroom.

```
Command (on a connected client): :Exit
Output (on Server): <username> left the chatroom
Output (on all other clients): <username> left the chatroom
```

---

## Grading Scheme

* Single server–client program sets up connection: **20 points**
* Single server, multiple clients able to connect: **20 points**
* Server receives from any client, sends to all: **20 points**
* Login and passcode implementation: **15 points**
* Text parsing for shortcut codes: **25 points** (see the shortcut list above)
* **Compilation errors are not acceptable.**

---

## Programming Do’s and Don’ts

* You should use `sys.stdout.flush()` after your print statements in Python to ensure that the message is printed on the terminal in a timely fashion.
* Your server should bind to **127.0.0.1** as the host. Use **IPv4** to bind to localhost. **Do not** attempt to bind to an IPv6 address.
* It is recommended to implement the `:Exit` functionality **first**. The autograder relies on this command to cleanly terminate client connections after each test. Failure to implement this correctly will likely cause most, if not all, subsequent test cases to fail.

---

## What to Submit?

Please implement all functionality in **`server.py`** and **`client.py`** (available on Canvas) and submit these files to **Gradescope**. There will be a minimal amount of starter code; the design is up to you. Ensure your code is well-structured and readable to facilitate grading.

---

## Further Questions?

Please use the **EdStem** [Programming Assignment 1 Megathread](https://edstem.org/us/courses/82073/discussion/7004574) for all doubts and questions related to PA1.
