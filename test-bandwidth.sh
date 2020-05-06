#!/bin/bash

cd logs
if [[ ! -e results ]]; then
    mkdir results

echo "Running tests with varying bandwidth"
# Run different sims with docker here
for BANDWIDTH in {10..100..10}
do
    SCENARIO="simple-p2p --delay=30ms --bandwidth=${BANDWIDTH}Mbps --queue=25"
	docker-compose up --no-start
    for CC in {0..2}
    do
        SERVER_PARAMS="--cc ${CC}"
        docker-compose start
        # Pass the CC value to docker-compose with env variables
        # docker exec -d server "python examples/http3_server.py --certificate tests/ssl_cert.pem --private-key tests/ssl_key.pem --cc $${CC}"
        docker exec -it client python examples/http3_client.py --ca-certs tests/pycacert.pem https://193.167.100.100:4433/ --cc ${CC} -r 500000000 -n 1
        docker-compose stop
    done
    docker-compose down
done

echo "Plotting window graph for 60Mbps"
gnuplot window-fixed.gp
mv window-fixed.svg results/window-fixed-bandwidth.svg

echo "Plotting loss graph for 60Mbps"
gnuplot loss-fixed.gp
mv loss-fixed.svg results/loss-fixed-bandwidth.svg

echo "Plotting latency graph for 60Mbps"
gnuplot latency-fixed.gp
mv latency-fixed.svg results/latency-fixed-bandwidth.svg

echo "Plotting window graph for range of bandwidths"
python3 window.py
gnuplot -e "labelname='Bandwidth (Mbps)'" window-varied.gp
mv window-varied.svg results/window-varied-bandwidth.svg

echo "Plotting loss graph for range of bandwidths"
python3 loss.py
gnuplot -e "labelname='Bandwidth (Mbps)'" loss-varied.gp
mv loss-varied.svg results/loss-varied-bandwidth.svg

echo "Plotting latency graph for range of bandwidths"
python3 latency.py
gnuplot -e "labelname='Bandwidth (Mbps)'" latency-varied.gp
mv latency-varied.svg results/latency-varied-bandwidth.svg

echo "Removing old backups"
rm -rf bandwidth
mkdir bandwidth

echo "Backing up logs"
mv reno bandwidth/
mv cubic bandwidth/
mv vivace bandwidth/
