import yaml


def main():
    data =  yaml.safe_load(open("/etc/ea/ea.yml", "r").read())
    print(" ".join([_ for _ in data["aws"]["accounts"]]))


if __name__ == "__main__":
    main()

