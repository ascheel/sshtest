"""
Class to allow easy access to the Monitoring Services Team API (MonAPI)
"""

import getpass
import httplib
import json
import os
import pwd
import time

import requests
import requests.exceptions


class MonApiClient(object):
    """
    Simplifies access to MonAPI
    """

    # Private constants
    _CACHE_CHILD_DIR = '.monapi'
    _LOGIN_ENDPOINT = '/auth'

    # Version Constants
    _CLIENT_TYPE = "python2.requests"
    _CLIENT_VERSION = "1.2.0"

    csrf_token = None
    default_payload_contents = {}
    domain = None
    full_uri = None
    local_username = getpass.getuser()
    password = None
    request_timeout = 120
    response_info = None
    session_cache_file = None
    session_id = None
    trusted_cert_file_path = ""
    username = None
    verify_ssl_chain = True

    def __init__(self, username=None, password=None, domain='moningestweb-or1-ext.adobe.net', uri='/monapi/v2', use_ssl=True):
        """
        Build the MonAPI Client object.  If no username and/or password are provided, a cached CSRF token and session ID
        must exist on the system.  If they do not, an exception will occur.
        :param username: The Digital Marketing username for connecting to MonAPI
        :param password: The Digital Marketing password for connecting to MonAPI
        :param domain: The domain endpoint for MonAPI.  Defaults to the production domain.
        :param uri: The base URI for MonAPI at the endpoint
        :param use_ssl: Set to False to use HTTP instead of HTTPS
        """

        protocol = 'https'
        if not use_ssl:
            protocol = 'http'

        if not uri.startswith("/"):
            uri = "/{0}".format(uri)

        self.domain = domain
        self.full_uri = "{0}://{1}{2}".format(protocol, domain, uri)
        self.username = username
        self.password = password

        local_username = getpass.getuser()
        if local_username is None:
            local_username = ''
        else:
            local_username = self.local_username.strip()

        cache_dir = self._get_cache_path(self.local_username)

        if cache_dir is not None:
            if username is None:
                self.session_cache_file = "{0}/sess_{1}.json".format(cache_dir, local_username)
            else:
                self.session_cache_file = "{0}/sess_{1}.json".format(cache_dir, username)

        self._read_cached_session(self.session_cache_file)

        self.default_payload_contents = {
            "_client_name": self._CLIENT_TYPE,
            "_client_version": self._CLIENT_VERSION,
            "_client_username": self.local_username
        }

    def send_request(self, endpoint, payload={}, method='get', filters={}):
        """
        Send a request to the API.  See the API documentation for endpoints, their required payloads, and their supported methods.
        :param endpoint: The endpoint to which the request should be sent (e.g. '/services/ack')
        :param payload: The content of the body, or in the event of using the "GET" method, the parameters for the URI
        :param method: The HTTP method that should be used
        :return: The response dictionary
        :rtype: dict
        """
        payload.update(self.default_payload_contents)

        self.response_info = {
            "data": {},
            "errors": [],
            "http_code": None
        }

        method = method.lower()
        if not endpoint.startswith("/"):
            endpoint = '/{0}'.format(endpoint)

        # Clear errors on each new request
        cookie = {'csrf_token': self.csrf_token, 'session': self.session_id}

        request_params = {
            "url": "{0}{1}".format(self.full_uri, endpoint),
            "verify": self.verify_ssl_chain,
            "timeout": self.request_timeout,
            "cert": self.trusted_cert_file_path,
            "cookies": cookie,
            "method": method
        }

        request_params.update({"params": filters})
        if method != 'get':
            request_params.update({"json": payload})

        response = requests.request(**request_params)

        self.response_info['http_code'] = response.status_code
        self.response_info['data'] = self._get_response_dict(response)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == httplib.UNAUTHORIZED and endpoint != self._LOGIN_ENDPOINT:
                auth_payload = {
                    "username": self.username,
                    "password": self.password
                }
                auth_response = requests.request(url="{0}{1}".format(self.full_uri, self._LOGIN_ENDPOINT), json=auth_payload, verify=self.verify_ssl_chain,
                                                 timeout=self.request_timeout, cert=self.trusted_cert_file_path, cookies={}, method='post')
                if self._write_cached_session(cookies=auth_response.cookies, headers=auth_response.headers):
                    return self.send_request(endpoint=endpoint, payload=payload, method=method)
                else:
                    self.response_info['errors'].append("Unable to successfully login to MonAPI.  Verify that a username/password were given.")
                    raise e
            else:
                self.response_info['errors'].append(e.message)
                raise e

        if endpoint == self._LOGIN_ENDPOINT:
            if not self._write_cached_session(cookies=response.cookies, headers=response.headers) or not self.response_info['response'].get('success', False):
                self.response_info['errors'].append("Unable to successfully login to MonAPI.  Verify that a username/password were given.")

        return self.response_info

    def get_response_dict(self):
        """
        Get the response dictionary from the last call to :method:`send_request`
        :return: The response dictionary
        :rtype: dict
        """
        return self.response_info

    def set_request_timeout(self, timeout):
        self.request_timeout = timeout

    def get_request_timeout(self):
        return self.request_timeout

    def _get_response_dict(self, response_obj):
        try:
            return response_obj.json()
        except Exception, e:
            return {}

    def _get_cache_path(self, local_username):
        uid = pwd.getpwnam(local_username).pw_uid
        if uid == 0:
            return None

        home_dir = os.path.expanduser("~")
        if not os.path.exists(home_dir):
            return None

        monapi_dir = "{0}/{1}".format(home_dir, self._CACHE_CHILD_DIR)
        if not os.path.exists(monapi_dir):
            try:
                os.makedirs(monapi_dir, mode=0700)
                if not os.path.exists(monapi_dir):
                    return None
            except OSError:
                return None

        return monapi_dir

    def _get_session_cache_file_contents(self, cache_file_path):
        if cache_file_path is None:
            return None

        if not os.path.isfile(cache_file_path):
            return None

        with open(cache_file_path, "r") as file_ptr:
            file_contents = file_ptr.read()

        if file_contents == '':
            return None

        try:
            session_file_info = json.loads(file_contents)
        except ValueError as e:
            return None

        if not isinstance(session_file_info, dict):
            return None

        return session_file_info

    def _read_cached_session(self, cache_file_path):
        session_file_info = self._get_session_cache_file_contents(cache_file_path)

        if session_file_info is None:
            return None

        if self.domain not in session_file_info:
            return None

        session_info = session_file_info.get(self.domain)
        if not isinstance(session_info, dict):
            return None

        if session_info.get('session', None) is None:
            return None

        if session_info.get('csrf_token', None) is None:
            return None

        token_expire_time = session_info['csrf_token'].split('##')[0]
        if token_expire_time <= time.time():
            return None

        self.csrf_token = session_info['csrf_token']
        self.session_id = session_info['session']

    def _write_cached_session(self, cookies, headers):
        self.csrf_token = None
        self.session_id = None

        try:
            self.csrf_token = cookies['csrf_token']
            self.session_id = cookies['session']
        except KeyError as e:
            return False

        if self.csrf_token is None:
            self.csrf_token = headers['X-CSRF-TOKEN']

        session_cache = self._get_session_cache_file_contents(self.session_cache_file)
        new_session_dict = {
            self.domain: {
                'csrf_token': self.csrf_token,
                'session': self.session_id
            }
        }

        if session_cache is not None:
            session_cache.update(new_session_dict)
        else:
            session_cache = new_session_dict

        with open(self.session_cache_file, 'w') as outfile:
            json.dump(session_cache, outfile)

        return True
