import sys


def header(phrase):
    border = 5
    gap = 5

    phrase = " ".join(phrase)
    
    # Top line
    _length = len(phrase) + (gap * 2) + (border * 2)
    print("*" * _length)
    
    # 2nd Line
    _whitespace = (gap * 2) + len(phrase)
    print("*" * border + " " * _whitespace + "*" * border)

    # Phrase
    print("*" * border + " " * gap + phrase + " " * gap + "*" * border)

    # 4th Line
    _whitespace = (gap * 2) + len(phrase)
    print("*" * border, end="")
    print(" " * _whitespace, end="")
    print("*" * border)

    # Bottom Line
    print("*" * _length)

def _split_phrase(phrase, max_length):
    lines = []
    tmp = phrase

    a = 0
    while True:
        if not tmp:
            break
        line = " ".join(tmp[:a])
        preline = ""
        if a > 0:
            preline = " ".join(tmp[:a-1])

        if len(line) > max_length or a > len(tmp):
            lines.append(preline)
            tmp = tmp[a-1:]
            a = 0

        a += 1

        continue
        
    return lines

def header2(phrase):
    total_length = 50
    border       = 5
    gap          = 2

    max_text_length = total_length - ((border * 2) + (gap * 2))

    lines = _split_phrase(phrase, max_text_length)

    # Print top line
    print("*" * total_length)
    
    # Print second line
    _whitespace = (gap * 2) + max_text_length
    print("*" * border + " " * _whitespace + "*" * border)

    for line in lines:
        line_length = len(line)
        padding_left = (max_text_length - line_length) // 2
        padding_right = padding_left
        if padding_left != (max_text_length - line_length) / 2:
            padding_right += 1
        print("*" * border + " " * gap + " " * padding_left + line + " " * padding_right + " " * gap + "*" * border)

    print("*" * border + " " * _whitespace + "*" * border)

    print("*" * total_length)
        


def main():
    phrase = []
    for item in sys.argv[1:]:
        for word in item.split(" "):
            phrase.append(word)

    # header(phrase)
    header2(phrase)


if __name__ == "__main__":
    main()

