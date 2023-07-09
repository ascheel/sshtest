import sys
import os
import yaml


class IDM:
    def __init__(self):
        settings_file = os.path.join(os.path.expanduser('~'), 'de-yml')
        self.settings      = yaml.load(open(settings_file, 'r').read())

    def output(self):
        for profile, values in self.settings['aws']['accounts']:
            if profile == sys.argv[1]:
                simple = values['ldap']['ssh_std']
                sudo   = values['ldap']['ssh_sudo']
                print(f'export IDM_LDAP_SIMPLE={simple}')
                print(f'export IDM_LDAP_SUDO={sudo}')
                sys.exit()


def main():
    idm = IDM()
    idm.output()


if __name__ == "__main__":
    main()
