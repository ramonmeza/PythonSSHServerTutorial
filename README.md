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

```sh
Custom SSH Shell
My Shell> greet
Hello there!
My Shell> greet ramon
Hey ramon! Nice to see you!
My Shell> bye ramon
See you later!
```

### Creating the Server Base Class


### Creating the ServerInterface


### Creating the SSH Server


### Dockerize the App


### Conclusion
