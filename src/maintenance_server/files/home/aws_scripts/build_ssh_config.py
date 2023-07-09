import os
import yaml


class SSH:
    def __init__(self):
        self.ansible_dir = "/home/scheel/git/ansible"
        self.base_file   = "/home/scheel/.ssh/config"
        self.output_file = "/home/scheel/.ssh/aws"

    def populate_servers(self):
        with open(self.output_file, "w") as f_out:
            # with open(self.base_file, "r") as f_in:
            #     for line in f_in:
            #         f_out.write(line)
            # f_out.write("\n")
            for _file in os.listdir(self.ansible_dir):
                if not _file.startswith("na-ea-"):
                    continue
                full = os.path.join(self.ansible_dir, _file)
                data = yaml.load(open(full, "r").read(), Loader=yaml.FullLoader)
                for category in data:
                    for server, meta in data[category]["hosts"].items():
                        _id      = server
                        _ip      = meta["ansible_host"]
                        _user    = meta["ansible_user"]
                        _options = meta.get("ansible_ssh_common_args")
                        _key     = meta["ansible_ssh_private_key_file"]
                        options_list = {}
                        if _options:
                            for _option in _options.split():
                                if _option.startswith("-o"):
                                    key   = _option[2:].split("=")[0]
                                    value = _option[2:].split("=")[1]
                                    options_list[key] = value

                        _host = [_id, _id.split("-")[1], _ip]
                        f_out.write(f"Host {_id} {_ip}\n")
                        f_out.write(f"\tHostname {_ip}\n")
                        f_out.write(f"\tUser {_user}\n")
                        f_out.write(f"\tIdentityFile {_key}\n")
                        for _key, _value in options_list.items():
                            f_out.write(f"\t{_key} {_value}\n")
                        f_out.write("\n")


def main():
    ssh = SSH()
    ssh.populate_servers()

if __name__ == "__main__":
    main()

