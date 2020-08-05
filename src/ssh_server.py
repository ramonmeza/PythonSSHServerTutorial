import paramiko

from src.server_base import ServerBase
from src.ssh_server_interface import SshServerInterface
from src.shell import Shell

class SshServer(ServerBase):

    def __init__(self, host_key_file, host_key_file_password=None):
        super(SshServer, self).__init__()

        self._host_key = paramiko.RSAKey.from_private_key_file(host_key_file, host_key_file_password)

    def connection_function(self, client):
        try:
            # create the SSH transport object
            session = paramiko.Transport(client)
            session.add_server_key(self._host_key)

            # create the server
            server = SshServerInterface()

            # start the SSH server
            try:
                session.start_server(server=server)
            except paramiko.SSHException:
                return

            # create the channel and get the stdio
            channel = session.accept()
            stdio = channel.makefile('rwU')

            # create the client shell and start it
            # cmdloop() will block execution of this thread.
            self.client_shell = Shell(stdio, stdio)
            self.client_shell.cmdloop()

            # After execution continues, we can close the session
            # since the only way execution will continue from
            # cmdloop() is if we explicitly return True from it,
            # which we do with the bye command.
            session.close()
        except:
            pass