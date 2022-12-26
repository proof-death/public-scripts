#! /usr/bin/bash

rm -f /trend/end_customer_v2/logs/worryfree.log

cd /trend/end_customer_v2/

python3 end_customer_query_logs.py

/opt/qradar/bin/logrun.pl -u 10.10.102.150 -f /trend/end_customer_v2/logs/worryfree.log 1
