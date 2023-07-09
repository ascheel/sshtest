import yaml
import os


def main():
    settings_file = os.path.join(os.path.expanduser('~'), 'de.yml')
    settings = yaml.safe_load(open("/etc/ea/ea.yml", "r").read())
    accounts = [_ for _ in settings["aws"]["accounts"]]
    print(" ".join(accounts), end="")


if __name__ =="__main__":
    main()

