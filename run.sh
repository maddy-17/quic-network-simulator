#!/bin/bash

BANDWIDTH=100
QUEUE=50
DELAY=30

echo -e "\e[1;33mNetwork Details: [${QUEUE}] [${BANDWIDTH} Mbps] [${DELAY} ms] \e[0m"

CC=$1
REQUEST=50000000
COUNT=1

echo -e "\e[1;33mRequest Details: [${COUNT}] [${REQUEST}] \e[0m"

export SCENARIO="simple-p2p --delay=${DELAY}ms --bandwidth=${BANDWIDTH}Mbps --queue=${QUEUE}"
export SERVER_PARAMS="--cc ${CC}"
export CLIENT_PARAMS="--cc ${CC} -r ${REQUEST} -n ${COUNT}"

case  ${CC}  in
	0)
	CC_NAME="NewReno Congestion Control"
		;;
	1)
	CC_NAME="Cubic Congestion Control"
		;;
	2)
	CC_NAME="Vivace Congestion Control"
		;;
	*)
		;;
esac

echo -e "\e[1;34mUsing ${CC_NAME} \e[0m"
for ITERATION in $(eval echo {1..$2})
do
	echo -e "\e[1;33mRunning Iteration: ${ITERATION}\e[0m"
	echo -e "\e[1;32mBuilding containers \e[0m"
	docker-compose up -d >> /dev/null 2>&1
	docker exec -it client python3 examples/http3_client.py \
		--ca-certs tests/pycacert.pem \
		${CLIENT_PARAMS} \
		https://193.167.100.100:4433/
	echo -e "\e[1;31mDestroying containers \e[0m"
	docker-compose down >> /dev/null 2>&1
done
