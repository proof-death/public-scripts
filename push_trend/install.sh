#! /bin/bash

cp -p /trend/public-scripts/push_trend/logfeeder.ini /trend/public-scripts/push_trend/logfeeder_bkp.ini
cp -p /trend/public-scripts/push_trend/push_worryfree.sh /trend/public-scripts/push_trend/push_worryfree_bkp.sh

input_logfeeder="/trend/public-scripts/push_trend/logfeeder_bkp.ini"
input_push="/trend/public-scripts/push_trend/push_worryfree_bkp.sh"

rm -f /trend/public-scripts/push_trend/logfeeder.ini
rm -f /trend/public-scripts/push_trend/push_worryfree.sh

echo ""
read -p "Access Token: " varToken
echo ""
read -p "Secret Key: " varKey
echo ""
read -p "SourceIP [IP fictício]:" varIp
echo ""
match_token="ACCESS_TOKEN ="
match_key="SECRET_KEY ="
match_ip="10.10.102.150"
touch /trend/public-scripts/push_trend/logfeeder.ini
touch /trend/public-scripts/push_trend/push_worryfree.sh
echo "Installing..."
while read -r line
do
if [[ $line = "$match_token" ]]; then
    echo "$line" | sed "s/$match_token/& $varToken/g" >> /trend/public-scripts/push_trend/logfeeder.ini
elif [[ $line = "$match_key" ]]; then
    echo "$line" | sed "s/$match_key/& $varKey/g" >> /trend/public-scripts/push_trend/logfeeder.ini
else
    echo "$line" >> /trend/public-scripts/push_trend/logfeeder.ini
fi
done < "$input_logfeeder"

while read -r line
do
if [[ $line = *"$match_ip"* ]]; then
    echo "$line" | sed "s/$match_ip/$varIp/" >> /trend/public-scripts/push_trend/push_worryfree.sh
else
    echo "$line" >> /trend/public-scripts/push_trend/push_worryfree.sh
fi
done < "$input_push"

cd /trend
mkdir end_customer_v2
mv public-scripts/push_trend/* end_customer_v2/
rm -rf public-scripts/

echo ""
echo "[Testando integração]"
echo ""

cd end_customer_v2
python /trend/end_customer_v2/end_customer_query_logs.py

sleep 5s
echo ""
printf "#logs Trend Micro Worry Free\n*/15 * * * * sh /trend/end_customer_v2/push_worryfree.sh\n" >> /var/spool/cron/root
echo "Done!"
echo "Installing DSM ..."

/opt/qradar/bin/contentManagement.pl -a import -f /trend/end_customer_v2/DSM-Trend_Micro_Worry_Free.zip -u admin

echo "Install Done!"

#GCamara
