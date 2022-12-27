#!/bin/bash
input="/trend/public-scripts/push_trend/logfeeder.ini"
cp /trend/public-scripts/push_trend/logfeeder.ini /trend/public-scripts/push_trend/logfeeder_bkp.ini
rm -f /trend/public-scripts/push_trend/logfeeder.ini
read -p "Access Token: " varToken
read -p "Secret Key: " varKey
match_token="ACCESS_TOKEN ="
match_key="SECRET_KEY ="
touch /trend/public-scripts/push_trend/logfeeder.ini
while read -r line
do
if [[ $line = "$match_token" ]]; then
    echo "$line" | sed "s/$match_token/& $varToken/g" >> /trend/public-scripts/push_trend/logfeeder.ini
elif [[ $line = "$match_key" ]]; then
    echo "$line" | sed "s/$match_key/& $varKey/g" >> /trend/public-scripts/push_trend/logfeeder.ini
else
    echo "$line" >> /trend/public-scripts/push_trend/logfeeder.ini
fi
done < "$input"
cd /trend
mkdir end_customer_v2
mv public-scripts/push_trend/* end_customer_v2/
rm -rf public-scripts/
printf "#logs Trend Micro Worry Free\n*/15 * * * * sh /trend/end_customer_v2/push_worryfree.sh\n" >> /var/spool/cron/root