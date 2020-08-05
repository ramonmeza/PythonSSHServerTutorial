# PythonSSHServerTutorial
A tutorial on creating an SSH server using Python 3, as well as the Paramiko library. It also will cover how to Dockerize this app.

### Introduction

### Prerequisites
Applications:
* Python 3.8+
* Docker
* OpenSSH (client and server)

`pip` packages:
* paramiko

### Creating the Shell
Our shell will extend the cmd module's Cmd class. The Cmd class provides us a way to create our own custom shell. It provides a cmdloop() function that will wait for input and display output. This class also makes it trivial to add custom commands to our shell.

We start by importing the cmd module's Cmd class and extending from it in our shell class:

```py
from cmd import Cmd

class Shell(Cmd):
```

Next we set some properties of our Cmd class. These properties are included in the base Cmd class:

```py
intro='Custom SSH Shell'
use_rawinput=False
prompt='My Shell> '
```

| Property     | Description                                                                                                                                             |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| intro        | A one time message to be output when the shell is created.                                                                                              |
| use_rawinput | Instead of using input(), this will use stdout.write() and stdin.readline(), this means we can use any TextIO instead of just sys.stdin and sys.stdout. |
| prompt       | The prompt property can be overridden, allowing us to use a custom string to be displayed at the beginning of each line. This will not be included in any input that we get.                 |

Now we can create our init function, which will take 2 IO stream objects, one for stdin and one for stdout, and call the base Cmd constructor. 

```py
def __init__(self, stdin=None, stdout=None):
    super(Shell, self).__init__(completekey='tab', stdin=stdin, stdout=stdout)
```

We can now create a custom `print()` function, which will utilize the Cmd class's stdout property, instead of using the default `print()` which  uses sys.stdout. If we use `print()`, any output will go to our server's local screen and not the client when we hook up SSH later on.

```py
def print(self, value):
    # make sure stdout is set and not closed
    if self.stdout and not self.stdout.closed:
        self.stdout.write(value)
        self.stdout.flush()

def printline(self, value):
    self.print(value + '\r\n')
```

Lastly we create our command functions. These are functions that will execute when the corresponding command is executed in the shell. These functions must be formatted in the following way: `do_{COMMAND}(self, arg)`, where we replace `{COMMAND}` with the string that will need to be entered in the shell to execute the command. For our purposes, we will create `do_greet()` and `do_bye()`.

```py
def do_greet(self, arg):
    if arg:
        self.printline('Hey {0}! Nice to see you!'.format(arg))
    else:
        self.printline('Hello there!')

def do_bye(self, arg):
    self.printline('See you later!')
    return True
```

One important note is that even if we don't use the `arg` parameter, like we don't in `do_bye()`, it still needs to be included.

Now we can test our shell to make sure everything works. The following code is just a test and is not included in the repository.

```py
from Shell import Shell

if __name__ == '__main__':
    my_shell = Shell()
    my_shell.cmdloop()
```

When we run the code we should get something like this as output.
```
Custom SSH Shell
My Shell> greet
Hello there!
My Shell> greet ramon
Hey ramon! Nice to see you!
My Shell> bye ramon
See you later!
```

### Creating the Server Base Class
We can now move on to creating the server base class, which will contain functionality for opening a socket, listening on a separate thread, and accepting a connection, where then it will call an abstract method to complete the connection and setup the shell for the connected client. The reason we do this as a base class, and not as a single Server class, is so we can support different connection types, such as Telnet. 

First we need to import some modules and extend the ABC class in our own ServerBase class.

```py
from abc import ABC, abstractmethod
from sys import platform
import socket
import threading

class ServerBase(ABC):
```

Next, let's create the init function and initialize some properties for later use (description below code):

```py
def __init__(self):
    self._is_running = threading.Event()
    self._socket = None
    self.client_shell = None
    self._listen_thread = None
```

| Property       | Description                                                                                                                                                       |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| _is_running    | a multithreaded event, which is basically a thread-safe boolean                                                                                                   |
| _socket        | this socket will be used to listen to incoming connections                                                                                                        |
| client_shell   | this will contain the shell for the connected client. We don't yet initialize it, since we need to get the stdin and stdout objects after the connection is made. |
| _listen_thread | this will contain the thread that will listen for incoming connections and data.                                                                                  |

Next we create the `start()` and `stop()` functions. These are relatively simple, but here's a quick explanation of both. `start()` will create the socket and setup the socket options. It's important to note that the socket option `SO_REUSEPORT` is not available on Windows platforms, so we wrap it with a platform check. `start()` also creates the listen thread and starts it, which will run the `listen()` function that we will tackle next. `stop()` is even easier, as it simply joins the listen thread and closes the socket.

```py
def start(self, address='127.0.0.1', port=22, timeout=1):
    if not self._is_running.is_set():
        self._is_running.set()

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

        # reuse port is not avaible on windows
        if platform == "linux" or platform == "linux2":
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)

        self._socket.settimeout(timeout)
        self._socket.bind((address, port))

        self._listen_thread = threading.Thread(target=self.listen)
        self._listen_thread.start()

def stop(self):
    if self._is_running.is_set():
        self._is_running.clear()
        self._listen_thread.join()
        self._socket.close()
```

The listen function will constantly run if the server is running. We wait for a connection, if a connection is made, we will call our abstract `connection_function()` function, which will be implemented inside of our specific server class, described later on. Note that we wrap our code in this function in a `try, except`. This is because we expect our `self._socket.accept()` to break every timeout interval, which we set in `__init__()`.

```py
def _listen(self):
    while self._is_running.is_set():
        try:
            self._socket.listen()
            client, addr = self._socket.accept()
            self.connection_function(client)
        except socket.timeout:
            pass
```

Lastly, we create our abstract `connection_function()` function. This will let us create derived classes of `ServerBase` that specify their own way of dealing with the connection that is being made. For example, later on in our SSH server class, we will connect the SSH transports to the connected client socket within `connection_function()`. But for now, this is all it is:

```py
@abstractmethod
    def connection_function(self, client):
        pass
```

### Creating the ServerInterface
http://docs.paramiko.org/en/stable/api/server.html
https://github.com/paramiko/paramiko/blob/master/demos/demo_server.py

This is probably the worst part of this entire project. Finding information on creating an SSH server is few and far between, but I was able to kind of piece it together, at least to the point where it works. Preface aside, we are going to be implementing `ServerInterface` from the `paramiko` package. This interface allows us to set up the SSH authentication and gives us access to connecting clients' stdin and stdout streams. This is essential to getting our SSH shell working, since `paramiko` takes care of the low level SSH stuff, like transports. Let's get on with it.

First let's import `paramiko` and create our class which inherits from `ServerInterface`.

```py
import paramiko

class SshServerInterface(paramiko.ServerInterface):
```

Now we can override some methods that we need in order to get authentication working. These are methods you can read about in the `paramiko` documentation link provide at the top of this section. If you omit these methods you won't be able to get your SSH client to connect to the server, since by default some of these methods will return `False`.

```py
def check_channel_request(self, kind, chanid):
    if kind == "session":
        return paramiko.OPEN_SUCCEEDED
    return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
    return True

def check_channel_shell_request(self, channel):
    return True
```

I'll go over a little of what I know about these methods. First, we have to understand what a channel is. Channels provide a secure communication route between the client and the host over an unsecure network. Since we are creating an SSH server, we need to be able to create these channels to allow clients to connect to us. For this, we will need to override `check_channel_request()` to return `OPEN_SUCCEEDED` when the `kind` of channel requested is a `session`. Next we need to override `check_channel_pty_request()` to return `True`. This allows our client to interact with our shell. Finally we can override `check_channel_shell_request()` to return `True`, which allows us to provide the channel with a shell we can connect to it (done in the next section). 

With all of that out of the way, let's override the method that will allow us to use username and password authentication. If you want to use public SSH keys or gssapi authentication instead, you will need to override the corresponding methods found in the `paramiko` documentation link. You should also look at the `demo_server.py` link I provided at the top of this section, as well.

```py
def check_auth_password(self, username, password):
    if (username == "admin") and (password == "password"):
        return paramiko.AUTH_SUCCESSFUL
    return paramiko.AUTH_FAILED
```

It's as simple as that. Typically, storing usernames and passwords in plain text is a bad idea, but since this isn't a tutorial on application security, it will do, but I urge you to come up with a better solution if you are using this publicly. You will want to create a database that you store your username and hashed passwords, where you will then be able to fetch, unhash and check their authenticity here.

This next section is optional, but will add a little flair to your SSH server. We will override the `get_banner()` method, which will display a message when a client first connects to our server but is not yet authenticated. This is different than our shell's `intro` property, since that happens when you get to the shell. The banner is displayed before that point, so if you define `get_banner()` here and `intro` in your shell, first your banner will show, after authentication your shell's `intro` will show.

```py
def get_banner(self):
    return ('My SSH Server\r\n', 'en-US')
```

Okay, that wasn't as painful as I thought it would be, so let's get on to the real fun part of this.

### Creating the SSH Server
The SSH server class is where things start to get spicy. That said, the class is actually very simple, since we are just implementing the `connection_function()` from the `ServerBase` class we created earlier. Lets start by importing some modules we created, as well as `paramiko`, and create our server class which will inherit from `ServerBase`.

```py
import paramiko

from src.server_base import ServerBase
from src.ssh_server_interface import SshServerInterface
from src.shell import Shell

class SshServer(ServerBase):
```

Next we need to add a property to our class which will hold the host's private RSA key. We do this in the `__init__()` function and use `paramiko`'s `RSAKey.from_private_key_file()` function.

```py
def __init__(self, host_key_file, host_key_file_password=None):
    super(SshServer, self).__init__()
    self._host_key = paramiko.RSAKey.from_private_key_file(host_key_file, host_key_file_password)
```

Finally, we have to override the `connection_function()`. In here we will first create the `Transport` object and add our host key to it. Then we start our SSH server, which will use the `SshServerInterface` class that we created. Next we create the channel that will be used over the `Transport`. This channel provides stream I/Os that we can hook up to our client shell. We start the shell using the `cmdloop()` function, which blocks execution until we call `bye` from our client. Finally we close the channel.

```py
def connection_function(self, client):
    try:
        session = paramiko.Transport(client)
        session.add_server_key(self._host_key)

        server = SshServerInterface()
        try:
            session.start_server(server=server)
        except paramiko.SSHException:
            return

        channel = session.accept()
        stdio = channel.makefile('rwU')

        self.client_shell = Shell(stdio, stdio)
        self.client_shell.cmdloop()

        session.close()
    except:
        pass
```

# Ruuning the SSH Server
Finally we can test all of our code up to this point. First we import our `SshServer` class we just created. Next we simply create our `SshServer`, passing it the location of our private RSA key and the corresponding password and start the server. If you need to create your SSH keys, I suggest either looking at `main.py` in this repository, or looking at this article, which explains how to do it on windows (https://phoenixnap.com/kb/generate-ssh-key-windows-10) or this one which explains how to do it on Linux (https://www.ssh.com/ssh/keygen/). 

```py
from src.ssh_server import SshServer

if __name__ == '__main__':
    server = SshServer('C:/Users/ramon/.ssh/id_rsa')
    server.start()
```

We now run the code using the command `python3 main.py`. We can open up a new Terminal/PowerShell/CMD window and try to connect to our SSH server using the following command: `ssh admin@127.0.0.1 -p 22`. This command will try to connect to an SSH server running on 127.0.0.1:22 as the username `admin`. If you use a different username, change it here. Once you run this command, you should see the `banner` you set in our `SshServerInterface` class earlier, as well as a prompt to enter our password. For our example, we type in `password` and we are given access to an instance of our custom shell! Exciting! 

You've noticed there are some issues. Yeah, I know. It's not perfect, but hopefully this will get people started for creating their own custom shells and custom SSH servers. If you know how to fix any of the issues, like how the spacing is all out of wack, please create a pull request so we can fix these issues and provide information for everyone.

### Dockerize the App
Cool, so our SSH server works. Now we want to use this somewhere else. Docker is the answer. Let's learn how we can dockerize our app and get it running everywhere (that has Docker installed)!

### Conclusion
