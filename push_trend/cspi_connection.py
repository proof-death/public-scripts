import base64
import calendar
import hashlib
import hmac
import requests
import time
import uuid

import sys
if sys.version_info.major == 3:
    from urllib.parse import urlencode, unquote
else:
    from urllib import urlencode, unquote


class CSPIConnection(object):
    def __init__(self, access_token, secret_key, hostname, port, timeout=60):
        self.access_token = access_token
        self.secret_key = secret_key
        self.hostname = hostname
        self.scheme = "https" if int(port) == 443 else "http"
        self.timeout = timeout
        self.connect()

    def connect(self):
        self.sess = requests.Session()

    def send_request(self, http_method, request_uri, body=None, retry=3):
        '''
        Send request to access CSPI
        '''
        retry_time = 0
        while retry_time < retry:
            headers = get_auth_headers(self.access_token, self.secret_key,
                                       http_method, request_uri, body)
            url = "%s://%s%s" % (self.scheme, self.hostname, request_uri)
            resp = self.sess.request(http_method, url, data=body, headers=headers)
            if resp.status_code == 200:
                break
            else:
                retry_time += 1
        return resp.status_code, resp.headers, resp.content

    def close(self):
        self.sess.close()


def get_auth_headers(access_token, secret_key, method, request_uri, body):
    '''
    Generate authentication herders
    '''
    posix_time = calendar.timegm(time.gmtime())

    headers = {}
    headers["content-type"] = "application/json"
    headers["x-access-token"] = access_token
    headers["x-signature"] = \
        gen_x_signature(secret_key, str(posix_time),
                        method, request_uri, body)
    headers["x-posix-time"] = str(posix_time)
    headers["x-traceid"] = str(uuid.uuid4())

    return headers


def gen_x_signature(secret_key, x_posix_time, request_method, request_uri,
                    body):
    '''
    Generate x-signature
    '''
    payload = x_posix_time + request_method.upper() + request_uri
    if body:
        payload += get_content_md5(body)
    hm = hmac.new(secret_key.encode("utf8"),
                  payload.encode("utf8"), hashlib.sha256)
    digest = hm.digest()
    digest = base64.b64encode(digest)
    return digest


def get_content_md5(content):
    '''
    Get hashed content
    '''
    m = hashlib.md5()
    m.update(content.encode("utf8"))
    digest = m.digest()
    digest = base64.b64encode(digest)
    return digest.decode('utf8')
