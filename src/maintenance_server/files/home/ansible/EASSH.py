import paramiko
import socket
import os
import sys
import traceback
import logging


def fix_key_path(path_in):
    if path_in.startswith("/"):
        return path_in
    if not "/" in path_in:
        # We're given a plain filename.  Is it valid?
        if os.path.isfile(path_in):
            # It's valid, give it back.
            return path_in
        else:
            # It's not valid.  Return it from .ssh directory.
            return os.path.join(os.path.expanduser("~"), ".ssh", path_in)


class EASSH:
    LOGFORMAT = "%(asctime)s - %(name)s - %(pathname)s:%(lineno)-4d - %(levelname)-8s - %(message)s"
    LOG = logging.getLogger('EASSH')

    @staticmethod
    def detect_os(client):
        root = os.path.split(os.path.abspath(__file__))[0]
        input_filename = os.path.join(root, "os_detection.py")
        output_filename = "/tmp/os_detection.py"

        _sftp = client.open_sftp()
        try:
            _sftp.put(input_filename, output_filename, confirm=True)
        except PermissionError as e:
            return "Error"
        except OSError as e:
            return "Error"
        _sftp.close()

        _stdin, _stdout, _stderr = client.exec_command("python /tmp/os_detection.py")
        _output = _stdout.read().decode()
        _output = _output.splitlines()
        return _output[0] if _output else "error"

    @staticmethod
    def try_login(host, user, key, port=22, **kwargs):
        """
        Try to log into an SSH server using the provided credentials.

        Args:
            host (string): Host to connect to
            user (string): User to connect with
            key (string): Private key to use (by name)
            port (int, optional): Port to connect on. Defaults to 22.
        Keyword Args:
            proxy_host (string): Host to proxy through
            proxy_user (string): User to connect to proxy with
            proxy_key (string): Private key to use to proxy with (by name)
            proxy_port (int): Port to proxy through. Defaults to 22.
            detect_os (boolean): Detect remote OS? Defaults to True.
        Return:
            (int): Error number:
                0: Success
                1: Timeout
                2: Permission Denied
                3: EOFError
                11: Proxy Timeout
                12: Proxy Permission Denied
                13: Proxy EOFError
                999: Unknown error
        """
        conn = {
            "host": host,
            "user": user,
            "key":  key,
            "port": port
        }
        proxy = {
            "host": kwargs.get("proxy_host"),
            "user": kwargs.get("proxy_user"),
            "key":  kwargs.get("proxy_key"),
            "port": kwargs.get("proxy_port", 22)
        }

        os_detection = kwargs.get("detect_os", True)

        if proxy["host"]:
            # print("Connecting with proxy")
            # print(proxy)
            # We were given proxy information
            if not proxy["user"] or not proxy["key"]:
                raise ValueError("proxy_host but no proxy_host or proxy_key provided.")

            if proxy["key"]:
                if not os.path.isfile(proxy["key"]):
                    proxy["key"] = os.path.join(os.path.expanduser("~"), ".ssh", os.path.split(proxy["key"])[1])

            proxyclient = paramiko.SSHClient()
            proxyclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            EASSH.LOG.debug("Connecting to proxy.")
            try:
                if not proxy["port"]:
                    proxy["port"] = 22
                # proxyclient.connect(proxy["host"], username=proxy["user"], key_filename=proxy["key"], port=proxy["port"], disabled_algorithms={'keys': ['rsa-sha2-256', 'rsa-sha2-512']})
                proxyclient.connect(proxy["host"], username=proxy["user"], key_filename=proxy["key"], port=proxy["port"])
            except TimeoutError as e:
                EASSH.LOG.debug("TimeoutError")
                return dict(
                    {
                        "returncode": 11,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            except paramiko.ssh_exception.AuthenticationException as e:
                EASSH.LOG.debug("AuthenticationException")
                return dict(
                    {
                        "returncode": 12,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            except paramiko.ssh_exception.SSHException as e:
                EASSH.LOG.debug("SSHException")
                return dict(
                    {
                        "returncode": 12,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            
            proxytransport = proxyclient.get_transport()
            destination_address = (conn["host"], conn["port"])
            local_address = ("0.0.0.0", conn["port"])

            EASSH.LOG.debug("Connecting over proxy transport connection.")
            try:
                proxychannel = proxytransport.open_channel("direct-tcpip", destination_address, local_address, timeout=15)
            except paramiko.ssh_exception.ChannelException as e:
                EASSH.LOG.debug(f"ChannelException ({e.code})")
                if e.code == 2:
                    EASSH.LOG.error(sys.exc_info())
                    return dict(
                        {
                            "returncode": 999,
                            "host":       host,
                            "user":       user,
                            "key":        key,
                            "port":       port
                        },
                        **kwargs
                    )

            except paramiko.ssh_exception.SSHException as e:
                # Likely a timeout.  SSHException is kinda generic.
                EASSH.LOG.debug("SSHException")
                return dict(
                    {
                        "returncode": 1,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )

            EASSH.LOG.debug("Creating SSH Client after proxy creation.")
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                if conn["key"]:
                    if not os.path.isfile(conn["key"]):
                        conn["key"] = os.path.join(os.path.expanduser("~"), ".ssh", os.path.split(conn["key"])[1])
                
                EASSH.LOG.debug("client.connect")
                # client.connect(conn["host"], username=conn["user"], port=conn["port"], key_filename=conn["key"], sock=proxychannel, allow_agent=False, disabled_algorithms={'keys': ['rsa-sha2-256', 'rsa-sha2-512']})
                client.connect(conn["host"], username=conn["user"], port=conn["port"], key_filename=conn["key"], sock=proxychannel, allow_agent=False)
                # Want to run applications on the remote side?  Do it here.
                _os = None
                if os_detection:
                    try:
                        _os = EASSH.detect_os(client)
                    except OSError as e:
                        print("Error detecting operating system.")
                        traceback.print_exception(*sys.exc_info())
                        _os = None
                # End
                client.close()
                proxyclient.close()
                return dict(
                    {
                        "returncode": 0,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port,
                        "os":         _os
                    },
                    **kwargs
                )
            except paramiko.ssh_exception.AuthenticationException as e:
                EASSH.LOG.debug("AuthenticationException")
                return dict(
                    {
                        "returncode": 2,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            # except paramiko.ssh_exception.SSHException as e:
            #     EASSH.LOG.debug("Getting SSHException, but on some hosts, this is an Authentication (publickey) failed.  So, returning '2'")
            #     return dict(
            #         {
            #             "returncode": 2,
            #             "host":       host,
            #             "user":       user,
            #             "key":        key,
            #             "port":       port
            #         }
            #     )
            except:
                # breakpoint()
                EASSH.LOG.debug('999')
                return dict(
                    {
                        "returncode": 999,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            client.close()
            proxyclient.close()
            EASSH.LOG.debug('999')
            return dict(
                {
                    "returncode": 999,
                    "host":       host,
                    "user":       user,
                    "key":        key,
                    "port":       port
                },
                **kwargs
            )
        else:
            EASSH.LOG.debug("Connecting without proxy.")
            # Direct connect, no proxy
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                EASSH.LOG.debug("Opening connection.")
                EASSH.LOG.debug(f"Conn: {conn}")
                # client.connect(conn["host"], port=conn["port"], username=conn["user"], key_filename=conn["key"], timeout=15, disabled_algorithms={'keys': ['rsa-sha2-256', 'rsa-sha2-512']})
                client.connect(conn["host"], port=conn["port"], username=conn["user"], key_filename=conn["key"], timeout=15)

                # Want to run applications on the remote side?  Do it here.
                if os_detection:
                    _os = EASSH.detect_os(client)
                # End

                client.close()
                return dict(
                    {
                        "returncode": 0,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port,
                        "os":         _os
                    },
                    **kwargs
                )
            except paramiko.ssh_exception.AuthenticationException as e:
                EASSH.LOG.debug("AuthenticationException")
                # Authentication failure
                return dict(
                    {
                        "returncode": 2,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            except socket.timeout as e:
                EASSH.LOG.debug("socket.timeout")
                return dict(
                    {
                        "returncode": 1,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            except TimeoutError as e:
                EASSH.LOG.debug("TimeoutError")
                return dict(
                    {
                        "returncode": 1,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            except EOFError as e:
                # An un-catchable EOFError typically happens because a server is rate-limiting a client.  Add a delay in between attempts.
                EASSH.LOG.debug("EOFError")
                return dict(
                    {
                        "returncode": 3,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            except paramiko.ssh_exception.SSHException as e:
                # traceback.print_exception(*sys.exc_info())
                EASSH.LOG.debug('999')
                return dict(
                    {
                        "returncode": 999,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            except:
                traceback.print_exception(*sys.exc_info())
                print("You shouldn't get here.  Paramiko probably pooped.  Or you hit Ctrl-C.")
                EASSH.LOG.debug('999')
                return dict(
                    {
                        "returncode": 999,
                        "host":       host,
                        "user":       user,
                        "key":        key,
                        "port":       port
                    },
                    **kwargs
                )
            EASSH.LOG.debug('999')
            return dict(
                {
                    "returncode": 999,
                    "host":       host,
                    "user":       user,
                    "key":        key,
                    "port":       port
                },
                **kwargs
            )


def main():
    proxy_host = "jump.dev.ea.adobe.net"
    proxy_user = "ea"
    proxy_port = 22
    proxy_key  = "/home/scheel/.ssh/id_rsa_ea"
    host = "10.43.48.26"
    user = "ec2-user"
    key = proxy_key
    results = EASSH.try_login(
        host,
        user,
        key,
        proxy_host=proxy_host,
        proxy_user=proxy_user,
        proxy_port=proxy_port,
        proxy_key=proxy_key
    )
    print("Results: {}".format(results))


if __name__ == "__main__":
    main()
