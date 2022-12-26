# -*- coding: UTF-8 -*-
import base64
import calendar
import copy
import datetime
import io
import json
import os
#import pytz
import sys
import time
import urllib

from array import array
python_ver = sys.version_info.major
if python_ver == 3:
    from configparser import ConfigParser
    from urllib.parse import urlencode
else:
    from ConfigParser import ConfigParser
    from urllib import urlencode

from cspi_connection import CSPIConnection

QUERY_TIME_RANGE = 15 * 60
BUFFER_TIME = 60
CONFIG = 'logfeeder.ini'
LATEST_QUERY_TIME_FILE = '.latest_query_time'
CUSTOMER_CACHE = 'customer_cache.json'
CUSTOMER_PAGE_LIMIT = 100
LOG_PAGE_LIMIT = 100


class LogFeeder(object):

    def __init__(self):
        self.parser = ConfigParser()
        self.parser.readfp(io.open(CONFIG, 'r', encoding='utf-8-sig'))
        self.ACCESS_TOKEN = self.parser.get('cspi', 'ACCESS_TOKEN')
        self.SECRET_KEY = self.parser.get('cspi', 'SECRET_KEY')
        self.SERVER_HOSTNAME = self.parser.get('cspi', 'SERVER_HOSTNAME')
        self.SERVER_PORT = self.parser.get('cspi', 'SERVER_PORT')
        self.QUERY_LOG_URI = "/SMPI/service/wfbss/customer/api/1.0/logfeeder/query_syslog"
        self.LOG_EXISTENCE_URI = "/SMPI/service/wfbss/customer/api/1.0/log_existence"
        self.LIST_CUSTOMER_URI = "/SMPI/v2.7/service/wfbss/api/customers"
        self.GET_CUSTOMER_BY_CID_URI = "/SMPI/v2.7/service/wfbss/api/customers?cids=%s"
        self.query_time_range = QUERY_TIME_RANGE
        self.log_types = self.parser.get('logfeeder', 'log_types').split(',')
        if not self.log_types[-1]:
            # pop up empty string
            self.log_types.pop()
        self.storage_path = self.parser.get('logfeeder', 'storage_path')
        if self.parser.has_option('logfeeder', 'specific_customers'):
            self.specific_customers = self.parser.get('logfeeder', 'specific_customers').split(';')
            if not self.specific_customers[-1]:
                # pop up empty string
                self.specific_customers.pop()

        if self.parser.has_option('logfeeder', 'create_folder_using_cid'):
            self.create_folder_using_cid = self.parser.getboolean('logfeeder', 'create_folder_using_cid')
        else:
            self.create_folder_using_cid = False


        self.now = int(time.time())
        self._get_latest_query()
        self.end_time = int()
        self.next_start_time = int()
        self.done = False
        if self.parser.has_option('logfeeder', 'append_customer_name'):
            self.append_customer_name = self.parser.getboolean('logfeeder', 'append_customer_name')
        else:
            self.append_customer_name = False

    def finish(self):
        self.done = True

    def _calculate_start(self):
        return self.now - BUFFER_TIME - self.query_time_range

    def _get_latest_query(self):
        if os.path.exists(LATEST_QUERY_TIME_FILE):
            with open(LATEST_QUERY_TIME_FILE, 'r') as op:
                data = op.readline().strip()
                self.latest_query = int(data if data else self._calculate_start())
        else:
            self.latest_query = self._calculate_start()

    def __del__(self):
        if self.next_start_time and self.done:
            with open(LATEST_QUERY_TIME_FILE, 'w') as op:
                op.write(str(self.next_start_time))

    def _run(self, method, uri, body=None):
        conn = CSPIConnection(self.ACCESS_TOKEN, self.SECRET_KEY, self.SERVER_HOSTNAME, self.SERVER_PORT)
        try:
            res_status, headers, res_data = conn.send_request(method, uri, body=body)
            if res_status != 200:
                print("Response status: \n%r" % res_status)
                print("Response data: \n%r" % res_data)
        finally:
            conn.close()
        try:
            res_dict = json.loads(res_data)
        except ValueError as e:
            res_dict = {}
        return res_status, res_dict

    def _is_less_than_query_interval(self, minimum_start_time):
        return True if self.latest_query <= minimum_start_time else False

    def check_query_time_range(self):
        start_time = int()
        end_time = int()
        # because some startup latency, we add 3 to make it not too strict.
        minimum_start_time = self.now - self.query_time_range - BUFFER_TIME + 3
        if not self.latest_query or self._is_less_than_query_interval(minimum_start_time):
            start_time = self.latest_query
            self.next_start_time = self.now - BUFFER_TIME
            # Try not to overlap time range
            end_time = self.end_time = self.next_start_time - 1
        else:
            after = (self.latest_query + self.query_time_range) - self.now + BUFFER_TIME
            print("You query log too often please wait after %d seconds" % after)

        return start_time and end_time

    def _write_to_file(self, logs, log_type, customer_info={}):
        if not logs:
            print("There is no log in interval.")
            return
        filename = "worryfree.log" #% (log_type, self.latest_query, self.end_time)
        sub_path = []
        if self.create_folder_using_cid:
            sub_path = [customer_info['cid'] + '/']
        elif customer_info:
            display_cus = customer_info['name']
            sub_path = [display_cus + '/']
        path = os.path.join(self.storage_path, *sub_path)
        dir_name = os.path.dirname(path)
        local_file = os.path.join(dir_name, filename)

        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print("create directory: %s" % (dir_name if python_ver == 3 else dir_name.encode('utf8')))

        print("start writing: %s" % (local_file if python_ver == 3 else local_file.encode('utf8')))
        with io.open(local_file, 'w', encoding='utf8') as f:
            for log in logs:
                if customer_info and self.append_customer_name:
                    log = log[:-1] + u' Customer Name="{customer_name}"]'.format(
                        customer_name=customer_info['name']
                    )
                # Bug in Device Control logs, there is \r in the serial id, we need to remove it to avoid new line.
                f.write(log.replace('\r', '') + '\n')
        return local_file

    def query_logs_realtime(self, log_type, customer_info={}):
        """
        response from API:
            {
                u'cid': u'37625F66-082E-4744-A72B-7D3E6080BF94',
                u'params': {
                    u'did': 387242,
                    u'label_mode_enabled': 0,
                    u'user_mode_enabled': 1,
                    u'params': {
                        u'order_by': [{u'name': u'recvtime'}],
                        u'record_range': {u'records_per_page': 25, u'total_records': 205, u'page_id': 1, u'total_pages': 9},
                        u'log_type': 203,
                        u'time_range': {u'range_to': 1606202526, u'range_from': 1606166527}
                    }
                },
                u'result': [...]
            }
        """
        err = False
        if self.log_types and log_type not in self.log_types:
            print("%s is not in your monitoring list." % log_type)
            return err
        params = {
            'event_type': log_type,
            'range_from': self.latest_query,
            'range_to': self.end_time,
            'limit': LOG_PAGE_LIMIT
        }
        if customer_info:
            params.update({
                'cid': customer_info['cid'],
                'eid': customer_info['eid'],
            })
        uri = self.QUERY_LOG_URI + '?' + urlencode(params)

        result = []
        sub_status, sub_data = self._run("GET", uri)

        if sub_status == 200:
            result.extend(sub_data['result'])
            page_id = sub_data['params']['params']['record_range']['page_id']
            total_pages = sub_data['params']['params']['record_range']['total_pages']
            total_records = sub_data['params']['params']['record_range']['total_records']
            print('There are total %d logs(total pages: %d)' % (total_records, total_pages))
            print('%d/%d' % (page_id, total_pages))
            while total_pages > page_id:
                params['page'] = page_id + 1
                uri = self.QUERY_LOG_URI + '?' + urlencode(params)
                sub_status, sub_data = self._run("GET", uri)
                result.extend(sub_data['result'])
                page_id = sub_data['params']['params']['record_range']['page_id']
                total_pages = sub_data['params']['params']['record_range']['total_pages']
                print('%d/%d' % (page_id, total_pages))

            self._write_to_file(result, log_type, customer_info)
            print("query_logs_realtime successfully.")
        else:
            err = True
            print("query_logs_realtime return error.")
        return err

    def check_log_existence(self, customers=None):
        err = False
        #Variable declaration for start and end query then convert it from Epoch to Normal Date
        start_normal = datetime.datetime.fromtimestamp(self.latest_query)
        end_normal = datetime.datetime.fromtimestamp(self.end_time)
        request_body = {
            "range_from": self.latest_query,
            "range_to": self.end_time,
        }
        if customers:
            request_body["cids"] = customers
        res_status, res_data = self._run("POST", self.LOG_EXISTENCE_URI, json.dumps(request_body))
        result = {}
        if res_status == 200 and res_data["result"]:
            print(u'Checking log existence')
            print(u'time range %d ~ %d' % (self.latest_query, self.end_time))
            #Show the converted Epoch time
            print(u'time range %s ~ %s' % (start_normal, end_normal))
            print(u'|%50s | %140s|' % ('customer id', 'log_types'))
            for i in res_data["result"]:
                result[i.get("cid", "endpoint")] = i["log_types"]
                print(u'|%50s | %140s|' % (i.get("cid"), ', '.join(i["log_types"])))
        elif res_status == 200:
            print("There is no log in time range in Epoch %d ~ %d" % (self.latest_query, self.end_time))
            #Show the converted Epoch time
            print("There is no log in time range in Normal %s ~ %s" % (start_normal, end_normal))
        else:
            print("Server response error: %s" % res_status)
            err = True
        return result, err

    @staticmethod
    def _print_err(status, result):
        print("Get customer error(%s): %s" % (status, result))

    def list_customers(self, page):
        uri = self.LIST_CUSTOMER_URI + "?limit=%s&page=%s" % (CUSTOMER_PAGE_LIMIT, page)
        res_status, result = self._run("GET", uri)
        if res_status != 200:
            self._print_err(res_status, result)
            result = {}
        return res_status, result

    def query_customers(self, q):
        params = {
            "q": q
        }
        uri = self.LIST_CUSTOMER_URI + '?' + urlencode(params)
        # in python2 ~ will be encoded to %7E but python3 won't.
        uri = uri.replace('%7E', '~')
        res_status, result = self._run("GET", uri)
        if res_status != 200:
            self._print_err(res_status, result)
            result = {}
        return res_status, result

    def get_specific_customers(self):
        customers = []
        if os.path.exists(CUSTOMER_CACHE):
            with io.open(CUSTOMER_CACHE, 'r', encoding='utf8') as op:
                customer_cache = json.load(op)
        else:
            customer_cache = {}

        new_cache = copy.deepcopy(customer_cache)

        not_in_cache = []
        for customer_name in self.specific_customers:
            customer_name = customer_name.strip() if python_ver == 3 else customer_name.strip().encode('utf8')
            if customer_name in customer_cache:
                customers.append(
                    {
                        'name': customer_name,
                        'id': customer_cache[customer_name]['id'],
                        'eid': customer_cache[customer_name]['eid']
                    }
                )
            else:
                not_in_cache.append(customer_name)

        for c in not_in_cache:
            res_status, res = self.query_customers(c)
            if res_status != 200:
                self._print_err(res_status, result)
                continue
            for r in res['customers']:
                name = r['name'].encode('utf8') if python_ver == 2 else r['name']
                if name == c:
                    customers.append(r)
                    new_cache[c] = {
                        'id': r['id'],
                        'eid': r['eid'],
                    }
                    break
            else:
                print("Customer %s is not in customer list" % c)

        if new_cache != customer_cache:
            with io.open(CUSTOMER_CACHE, 'w', encoding='utf8') as op:
                j = json.dumps(new_cache, indent=2) if python_ver == 3 else json.dumps(new_cache, indent=2).decode('utf8')
                op.write(j)

        return customers
