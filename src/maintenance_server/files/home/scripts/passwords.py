import random
import argparse
import string


class Passwords:
    CONFUSING_LETTERS = 'iIl1|!O0S5$t+(){}[]uvVW/\\\'\":;-_,`'

    def __init__(self, **kwargs):
        self.args = kwargs.get('args')
        self.lowercase         = self.args.lowercase
        self.uppercase         = self.args.uppercase
        self.digits            = self.args.digits
        self.symbols           = self.args.symbols
        self.remove_confusing  = self.args.remove_confusing
        self.remove_vowels     = self.args.remove_vowels
        self.number            = self.args.number
        self.users             = self.args.users
        self.adobe             = self.args.adobe
        self.length            = self.args.length
        
        if not self.users and not self.number:
            self.number = 1

        if not self.lowercase and not self.uppercase and not self.digits and not self.symbols:
            # Set defaults if no options chosen.
            self.lowercase = True
            self.uppercase = True
            self.digits    = True
            self.symbols   = True
        
        self.options = ''
        if self.adobe:
            self.lowercase        = True
            self.uppercase        = True
            self.digits           = True
            self.symbols          = False
            self.remove_confusing = False
            self.remove_vowels    = False
            self.length           = 30
            
        if self.lowercase:
            self.options += string.ascii_lowercase
        if self.uppercase:
            self.options += string.ascii_uppercase
        if self.digits:
            self.options += string.digits
        if self.symbols:
            self.options += string.punctuation

        if self.remove_confusing:
            self.strip(Passwords.CONFUSING_LETTERS)
        if self.remove_vowels:
            self.strip('aeiouAEIOU')

    def gotit(self, password, letters):
        for _letter in letters:
            if _letter in password:
                return True
        return False

    def get_password(self):
        while True:
            password = ''.join(random.choices(self.options, k=self.length))
            if self.lowercase:
                if not self.gotit(password, string.ascii_lowercase):
                    continue
            if self.uppercase:
                if not self.gotit(password, string.ascii_uppercase):
                    continue
            if self.digits:
                if not self.gotit(password, string.digits):
                    continue
            if self.symbols:
                if not self.gotit(password, string.punctuation):
                    continue
            return password

    def max_username_length(self):
        _max = 0
        for user in self.users:
            if len(user) > _max:
                _max = len(user)
        return _max

    def generate(self):
        if self.number:
            for number in range(self.number):
                print(self.get_password())
        if self.users:
            for user in self.users:
                print(f"{user:{self.max_username_length()}}  {self.get_password()}")
        
    def strip(self, to_strip):
        for _letter in to_strip:
            self.options = self.options.replace(_letter, '')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-l',
        '--lowercase',
        help="Allow lowercase letters.",
        action="store_true"
    )
    parser.add_argument(
        '-u',
        '--uppercase',
        help="Allow uppercase letters.",
        action="store_true"
    )
    parser.add_argument(
        "-d",
        "--digits",
        help="Allow digits.",
        action="store_true"
    )
    parser.add_argument(
        "-s",
        "--symbols",
        help="Allow symbols.",
        action="store_true"
    )
    parser.add_argument(
        "-r",
        "--remove-confusing",
        help=f"Removes all potentially confusing letters/numbers/symbols: {Passwords.CONFUSING_LETTERS}",
        action="store_true"
    )
    parser.add_argument(
        "-v",
        "--remove-vowels",
        help="Removes all vowels.  Prevents accidental creation of potentially offensive passwords.",
        action="store_true"
    )
    parser.add_argument(
        "users",
        help="Add a list of usernames to create passwords for.  This creates a list of user=<password> output.",
        nargs='*'
    )
    parser.add_argument(
        "-n",
        "--number",
        help="Create N passwords.  Not compatible with 'users' option.",
        type=int
    )
    parser.add_argument(
        "-L",
        "--length",
        help="Length of password(s) to generate.",
        type=int,
        default=10
    )
    parser.add_argument(
        "--adobe",
        help="Generate passwords for Adobe.  Custom for Data Engineering.",
        action="store_true"
    )
    args = parser.parse_args()

    passwords = Passwords(args=args)
    passwords.generate()


if __name__ == "__main__":
    main()
