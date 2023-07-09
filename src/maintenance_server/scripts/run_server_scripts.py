import paramiko
import os
import sys


class SSH:
    def __init__(self, **kwargs):
        self.host      = kwargs["host"]
        self.port      = kwargs["port"]
        self.user      = kwargs["user"]
        self.keyname   = kwargs["key"]
        self.proxyhost = kwargs["proxyhost"]
        self.proxyport = kwargs["proxyport"]
        self.proxyuser = kwargs["proxyuser"]
        self.proxykey  = kwargs["proxykey"]
    
    def get_filesize(self, filename):
        return os.stat(filename).st_size

    def execute(self, client, command):
        _stdin, _stdout, _stderr = client.exec_command(command)
        _output = {
            "stdout": _stdout.read(),
            "stderr": _stderr.read()
        }
        return _output

    def transfer(self):
        proxyclient = paramiko.SSHClient()
        proxyclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        proxyclient.connect(self.proxyhost, username=self.proxyuser, key_filename=self.proxykey, port=self.proxyport)
        proxytransport = proxyclient.get_transport()

        destination = (self.host, self.port)
        local       = ("0.0.0.0", self.port)

        proxychannel = proxytransport.open_channel("direct-tcpip", destination, local, timeout=30)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Key: {self.keyname}")
        client.connect(self.host, username=self.user, port=self.port, key_filename=self.keyname, sock=proxychannel, allow_agent=False)

        # Do things and stuff

        self.execute(client, "mkdir bin")

        _sftp = client.open_sftp()
        
        files_to_upload = ["files/serverscript.sh", "files/serverscript.py"]
        for _file in files_to_upload:
            _target_filename = f"bin/{_file.split('/')[-1]}"
            print(f"Uploading: {_file} ({self.get_filesize(_file)} bytes) to {_target_filename}")
            _sftp.put(
                _file,
                _target_filename,
                confirm=True
            )

            self.execute(client, f"chmod 755 {_target_filename}")

        _sftp.close()
        # End of Do thing and stuff

        client.close()
        proxyclient.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        help="Host to connect to",
        required=True
    )
    parser.add_argument(
        "--port",
        help="Port",
        required=False,
        default=22,
        type=int
    )
    parser.add_argument(
        "--user",
        help="username",
        required=True
    )
    parser.add_argument(
        "--key",
        help="ssh key",
        required=True
    )
    parser.add_argument(
        "--proxyhost",
        help="proxy host",
        required=True
    )
    parser.add_argument(
        "--proxyport",
        help="proxy port",
        required=False,
        default=22,
        type=int
    )
    parser.add_argument(
        "--proxyuser",
        help="proxy user",
        required=True
    )
    parser.add_argument(
        "--proxykey",
        help="proxy key",
        required=True
    )
    args = parser.parse_args()

    ssh = SSH(
        host=args.host,
        port=args.port,
        user=args.user,
        key=args.key,
        proxyhost=args.proxyhost,
        proxyport=args.proxyport,
        proxyuser=args.proxyuser,
        proxykey=args.proxykey
    )
    ssh.transfer()


if __name__ == "__main__":
    main()


