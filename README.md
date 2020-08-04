# PythonSSHServerTutorial
A tutorial on creating an SSH server using Python 3, as well as the Paramiko library. It also will cover how to Dockerize this app.

### Introduction


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
    def connection_method(self, client):
        pass
```

### Creating the ServerInterface


### Creating the SSH Server


### Dockerize the App


### Conclusion
