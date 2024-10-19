# PythonSSHServerTutorial

A tutorial on creating an SSH server using Python 3 and the `paramiko` package. It will also cover how to "dockerize" the application using Docker to allow it to be run on other platforms.

## Prerequisites

Applications:

- Python 3.8+
- venv
- Docker
- OpenSSH (client and server)

`pip` packages:

- paramiko

## Creating the Application

### Create a `venv`

A virtual environment allows you to separate dependencies used in your app from those globally installed on your local machine. It's probably a good idea to use a `venv` if you plan to redistribute your code.

```sh
python -m venv .env
```

You can activate your environment using the following command:

```sh
./.env/Scripts/activate
```

Once activated, any `python` or `pip` commands you make will be executed using `python` and `pip` executable within your `venv`.

Install the following:

```sh
pip install paramiko
```

### Creating the Shell

Our shell will extend the `cmd` module's `Cmd` class. The `Cmd` class provides us a way to create our own custom shell. It provides a `cmdloop()` function that will wait for input and display output. This class also makes it trivial to add custom commands to our shell.

We start by importing the `cmd` module's `Cmd` class and extending from it in our shell class:

```py
from cmd import Cmd

class Shell(Cmd):
```

Next we set some properties of our class. These properties are going to be overriden from the base `Cmd` class:

```py
intro='Custom SSH Shell'
use_rawinput=False
prompt='My Shell> '
```

| Property       | Description                                                                                                                                                          |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `intro`        | A one time message to be output when the `cmdloop()` function is called.                                                                                             |
| `use_rawinput` | Instead of using `input()`, this will use `stdout.write()` and `stdin.readline()`, which means we can use any `TextIO` instead of just `sys.stdin` and `sys.stdout`. |
| `prompt`       | allows us to use a custom string to be displayed at the beginning of each line. This will not be included in any input that we get.                                  |

Now we can create our `__init__()` function, which will take two I/O stream objects, one for `stdin` and one for `stdout`, and call the base `Cmd` constructor.

```py
def __init__(self, stdin=None, stdout=None):
    super(Shell, self).__init__(completekey='tab', stdin=stdin, stdout=stdout)
```

We can now create a custom `print()` function, which will utilize the `Cmd` class's `stdout` property, instead of using the default `print()` which uses `sys.stdout`. If we use `print()`, any output will go to our server's local screen and not the client when we hook up SSH later on.

```py
def print(self, value):
    # make sure stdout is set and not closed
    if self.stdout and not self.stdout.closed:
        self.stdout.write(value)
        self.stdout.flush()

def printline(self, value):
    self.print(value + '\r\n')
```

Now we can create our command functions. These are functions that will execute when the corresponding command is executed in the shell. These functions must be formatted in the following way: `do_{COMMAND}(self, arg)`, where we replace `{COMMAND}` with the string that will need to be entered in the shell to execute the command. For our purposes, we will create `do_greet()` and `do_bye()`. One important note is that even if we don't use the `arg` parameter, like we don't in `do_bye()`, it still needs to be included.

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

One final thing we can do, just to make things look a little nicer to the client, is override the `emptyline()` function, which will execute when the client enters an empty command.

```py
def emptyline(self):
    self.print('\r\n')
```

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

We can now move on to creating the server base class, which will contain functionality for opening a socket, listening on a separate thread, and accepting a connection, where then it will call an abstract method to complete the connection and setup the shell for the connected client. The reason we do this as a base class, and not as a single server class is so we can support different connection types, such as Telnet.

First we need to import some modules and extend the ABC class in our own `ServerBase` class.

```py
from abc import ABC, abstractmethod
from sys import platform
import socket
import threading

class ServerBase(ABC):
```

Next, let's create the `__init__()` function and initialize some properties for later use:

```py
def __init__(self):
    self._is_running = threading.Event()
    self._socket = None
    self.client_shell = None
    self._listen_thread = None
```

| Property         | Description                                                                                                                                                           |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_is_running`    | a multithreaded event, which is basically a thread-safe boolean                                                                                                       |
| `_socket`        | this socket will be used to listen to incoming connections                                                                                                            |
| `client_shell`   | this will contain the shell for the connected client. We don't yet initialize it, since we need to get the `stdin` and `stdout` objects after the connection is made. |
| `_listen_thread` | this will contain the thread that will listen for incoming connections and data.                                                                                      |

Next we create the `start()` and `stop()` functions. These are relatively simple, but here's a quick explanation of both. `start()` will create the socket and setup the socket options. It's important to note that the socket option `SO_REUSEPORT` is not available on Windows platforms, so we wrap it with a platform check. `start()` also creates the listen thread and starts it, which will run the `listen()` function that we will tackle next. `stop()` is even easier, as it simply joins the listen thread and closes the socket.

```py
def start(self, address='127.0.0.1', port=22, timeout=1):
    if not self._is_running.is_set():
        self._is_running.set()

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

        if platform == "linux" or platform == "linux2":
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)

        self._socket.settimeout(timeout)
        self._socket.bind((address, port))

        self._listen_thread = threading.Thread(target=self._listen)
        self._listen_thread.start()

def stop(self):
    if self._is_running.is_set():
        self._is_running.clear()
        self._listen_thread.join()
        self._socket.close()
```

The `listen()` function will constantly run if the server is running. We wait for a connection, if a connection is made, we will call our abstract `connection_function()` function, which will be implemented inside of our specific server class, described later on. Note that we wrap the code in this function in a `try, except` statement. This is because we expect `self._socket.accept()` to break if the server is stopped.

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

Lastly, we create our abstract `connection_function()` function. This will let us create derived classes of `ServerBase` that specify their own way of dealing with the connection that is being made. For example, later on in our SSH server class, we will connect the SSH `Transport` objects to the connected client socket within `connection_function()`. But for now, this is all it is:

```py
@abstractmethod
    def connection_function(self, client):
        pass
```

### Creating the ServerInterface

[`ServerInterface` Documentation](http://docs.paramiko.org/en/stable/api/server.html)
[demo_server.py from paramiko repository](https://github.com/paramiko/paramiko/blob/master/demos/demo_server.py)

This is probably the worst part of this entire project. Making sense of the information available on creating an SSH server is both daunting and exhausting, but I was able to kind of piece it together, at least to the point where it works. Preface aside, we are going to be implementing `ServerInterface` from the `paramiko` package. This interface allows us to set up the SSH authentication and gives us access to connecting clients' `stdin` and `stdout` streams. This is essential to getting our SSH shell working, since `paramiko` takes care of the low level SSH stuff, like `Transport` objects. Let's get on with it.

First let's import `paramiko` and create our class which inherits from `ServerInterface`.

```py
import paramiko

class SshServerInterface(paramiko.ServerInterface):
```

Now we can override the methods that we need in order to get authentication to work. These are methods you can read about in the `paramiko` documentation link provide at the top of this section. If you omit these methods you won't be able to get your SSH client to connect to the server, since by default some of these methods will return values which block the connection.

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

With all of that out of the way, let's override the method that will allow us to use username and password authentication. If you want to use public SSH keys or gssapi authentication instead, you will need to override the corresponding methods found in the `paramiko` documentation link. You should also look at the `demo_server.py` link I provided at the top of this section, which proved to be a valuable resource while creating this tutorial.

```py
def check_auth_password(self, username, password):
    if (username == "admin") and (password == "password"):
        return paramiko.AUTH_SUCCESSFUL
    return paramiko.AUTH_FAILED
```

It's as simple as that. However, storing usernames and passwords in plain text is a bad idea, but since this isn't a tutorial on application security, it will do. I urge you to come up with a better solution if you are using this publicly. You will want to create a database to store your usernames and hashed passwords, where then you will then be able to fetch, unhash and check their authenticity here.

This next section is optional, but will add a little flair to your SSH server. We will override the `get_banner()` method, which will display a message when a client first connects to our server but is not yet authenticated. This is different than our shell's `intro` property, since that happens when you get to the shell. The banner is displayed before that point, so if you define `get_banner()` here and `intro` in your shell, first your banner will show, after authentication your shell's `intro` will show. Note that `get_banner()` returns a tuple where the first element is banner string and the second element is the language in `rfc3066` style, such as `'en-US'`.

```py
def get_banner(self):
    return ('My SSH Server\r\n', 'en-US')
```

Okay, that wasn't as painful as I thought it would be, so let's get on to the real fun part of this.

### Creating the SSH Server

The `SshServer` class is where things start to get spicy. That said, the class is actually very simple since we are just implementing the `connection_function()` from the `ServerBase` class we created earlier. Let's start by importing some modules we've created, as well as `paramiko`, and create our server class which will inherit from `ServerBase`.

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

Finally, we have to override the `connection_function()` function. In here we will first create the `Transport` object and add our host key to it. Then we start our SSH server, which will use the `SshServerInterface` class that we created. Next we create the channel that will be used over the `Transport`. This channel provides stream I/Os that we can hook up to our client shell. We start the shell using the `cmdloop()` function, which blocks execution until we call `bye` from our client. Finally we close the channel.

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

### Running the SSH Server

Finally we can test all of our code up to this point. First we import our `SshServer` class we just created. Next we simply create our `SshServer`, passing it the location of our private RSA key and the corresponding password and start the server. If you need to create your SSH keys, I suggest either looking at `main.py` in this repository, or looking at either [this article](https://phoenixnap.com/kb/generate-ssh-key-windows-10), which explains how to do it on windows, or [this one](https://www.ssh.com/ssh/keygen/) which explains how to do it on Linux.

```py
from src.ssh_server import SshServer

if __name__ == '__main__':
    server = SshServer('C:/Users/ramon/.ssh/id_rsa')
    server.start()
```

We now run the code using the command `python3 main.py`. We can open up a new Terminal/PowerShell/CMD window and try to connect to our SSH server using the following command: `ssh admin@127.0.0.1 -p 22`. This command will try to connect to an SSH server running on 127.0.0.1:22 as the username `admin`. If you use a different username, change it here. Once you run this command, you should see the banner text you set in our `SshServerInterface` class earlier, as well as a prompt to enter our password. For this example, we can type in `password` and we are given access to an instance of our custom shell! Exciting!

You've noticed there are some issues. Yeah, I know. It's not perfect, but hopefully this will get people started for creating their own custom shells and custom SSH servers. If you know how to fix any of the issues, like how the spacing is all out of whack, please create a pull request so we can fix these issues and provide the correct information to everyone.

## Dockerize the App

Cool, so our SSH server works. Now we want to use this somewhere else. Docker is the answer. Let's learn how we can dockerize our app and get it running everywhere (that has Docker installed)!

### `requirements.txt`

`requirements.txt` is a file created for us by `pip`. It includes all of the packages that are installed within our environment. If you used `venv` to create your environment, this will result is a small file with just the packages we've used. Run the following command to generate your `requirements.txt` file once you're ready to Dockerize your application:

```sh
pip freeze > requirements.txt
```

### Application Modifications

We need to ensure our private key is generated within our Docker container and that we use this file within our container as our private key within our app. This is as simple as changing the path to our private key in `main.py` to `~/.ssh/id_rsa`.

### `Dockerfile`

`Dockerfile` is where you define environment your container will run within. Technically, your `Dockerfile` is used to create an "image", which will then be used to create a "container" which runs your application. You can think of the container as an instance of the image.

When you break down a `Dockerfile`, you typically will see a `FROM` tag at the top, specifying the base image your image will utilize. In our case, we use `ubuntu`. You can also see within the file are `RUN` commands, which do exactly what they say and run a given command within the build stage of your `Dockerfile`. To reiterate, our `Dockerfile` is our method of defining our environment. You can sort of think of this as setting up a new PC and the commands you'd use to install what you need to get your app running. There's a TON of Docker images to base your `Dockerfile` off of, and it can save you a lot of work if you find a base image that does what you need for your specific case.

For our app, we simply use Ubuntu, install updates, Python and pip, copy our files into our container, install our pip requirements, expose our desired ports and finally run our application.

An important note to remember about Docker and writing `Dockerfile` is to keep commands which won't change up top. Generally speaking, installations should be higher in your `Dockerfile` and copying/compiling your application files should be toward the bottom. This allows Docker to cache your images so you don't have to constantly wait for Docker to build and install prerequisites every time you change your source code.

### Building and Running the `Dockerfile`

Now that you've defined the `Dockerfile`, you can build a corresponding image we will eventually use for our container. Run the following command:

```sh
docker build . --tag python_ssh_server
```

The `build` command takes the path to the directory containing your `Dockerfile` and a tag which we use to easily reference our image in our next command:

```sh
docker run --rm -e SSH_PORT=2222 -p 2223:2222 --name my_ssh_app_container python_ssh_server:latest
```

The `run` command allows use to specify the name of our container and the image we wish to instantiate from. I also include `--rm`, which removes the container once execution is completed. We also need to specify the ports we wish to expose from our container using `-p`. The syntax for `-p` is `-p [local_port]:[container_port]`, where `container_port` is the port your application uses, and `local_port` is the port which will be mapped to the container. When `local_port` is set to 2223, we connect to our SSH server using `ssh 0.0.0.0 -p 2223` from our local machine.

Read more about these flags in the Docker documentation if you wish.

### Connecting to your Containerized SSH Server

Now that the Docker container is running, you simply SSH in like you would any other SSH server:

```sh
ssh admin@0.0.0.0 -p 2223
```

Here the server address is `0.0.0.0` (default for Docker containers). We also specify our port using `-p`, where the port matches what we mapped in the container. Once you run this command, you should be connected to your SSH server, running from within a Docker container!

### Conclusion

We did it! We created a custom SSH shell using Python, which can run anywhere Docker is installed. If you have questions, please raise an issue and I'll do my best to answer your question to the best of my ability and within a _"timely"_ (it may take a long time) manner.

Thanks for sticking around and learning with me.
