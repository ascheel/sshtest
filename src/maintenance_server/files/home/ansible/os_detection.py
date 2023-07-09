#!/usr/bin/python

import platform

if "amzn1" in platform.release():
    _os = "Amazon Linux 1"
elif "amzn2" in platform.release():
    _os = "Amazon Linux 2"
elif "centos" in platform.dist() and "el7" in platform.release():
    _os = "CentOS 7"
elif "redhat" in platform.dist() and "el7" in platform.release():
    _os = "RHEL 7"
elif platform.dist()[0] == "Ubuntu":
    #_os = "Ubuntu " + platform.dist()[1]
    _os = "Ubuntu"
else:
    _os = "Unknown"
print(_os)
# print("Release: {}".format(platform.release()))
# print("Dist:    {}".format(platform.dist()))
# print("Name:    {}".format(os.name))
# print("System:  {}".format(platform.system()))


# >>> os.name
# 'posix'
# >>> import platform
# >>> platform.system()
# 'Linux'
# >>> platform.release()
# '4.9.43-17.39.amzn1.x86_64'
# >>> platform.dist()
# ('', '', '')



# >>> os.name
# 'posix'
# >>> platform.system()
# 'Linux'
# >>> platform.release()
# '3.10.0-957.12.2.el7.x86_64'
# >>> platform.dist()
# ('centos', '7.6.1810', 'Core')


# >>> os.name
# 'posix'
# >>> platform.system()
# 'Linux'
# >>> platform.release()
# '4.14.171-136.231.amzn2.x86_64'
# >>> platform.dist()
# ('', '', '')
