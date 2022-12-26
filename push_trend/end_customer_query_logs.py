import math
import os
import json
import time

from cspi_connection import CSPIConnection
from logfeeder import LogFeeder


def run():
    client = LogFeeder()

    if not client.check_query_time_range():
        return

    result, err = client.check_log_existence()
    if not result:
        print("There is nothing to do")

    for cid, log_types in result.items():
        print("cid: %s" % cid)
        for log_type in log_types:
            print ("log_type: %s" % log_type)
            err = client.query_logs_realtime(log_type)

    if not err:
        client.finish()


if __name__ == '__main__':
    print("Query logs start: ")
    run()
    print("Query logs finish.")
