import os
import sys
import yaml
import json
import requests


def main():
    url = "https://imagefactory.corp.adobe.com:8443/imagefactory/binary/details/?cloud_or_pkg_type=aws"
    data = requests.get(url)
    text = data.content

    image_info = json.loads(text)
    _ids = []
    for image in image_info:
        _id = image["imageId"]
        for key, value in _id.items():
            _ids.append(value)
    open("images.txt", "w").write("\n".join(_ids))

if __name__ == "__main__":
    main()

