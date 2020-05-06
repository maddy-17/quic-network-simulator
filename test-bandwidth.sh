#!/bin/bash

echo -e "\e[1;33mRunning tests with varying bandwidth \e[0m"
REQUEST=20000000
COUNT=1
INTERVAL=5
for BANDWIDTH in {5..50..5}
do
    echo -e "\e[1;34mSetting bandwidth to ${BANDWIDTH} Mbps \e[0m"
    export SCENARIO="simple-p2p --delay=30ms --bandwidth=${BANDWIDTH}Mbps --queue=25"
    for CC in {0..2}
    do
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
        echo -e "\e[1;32mBuilding containers \e[0m"
        docker-compose up -d >> /dev/null 2>&1
        docker exec -it client python3 examples/http3_client.py \
            --ca-certs tests/pycacert.pem \
            ${CLIENT_PARAMS} \
            https://193.167.100.100:4433/
        echo -e "\e[1;31mDestroying containers \e[0m"
        docker-compose down >> /dev/null 2>&1
    done
done

cd logs
if [[ ! -e results ]]; then
    mkdir results
fi

sudo chown -R $USER reno
sudo chown -R $USER cubic
sudo chown -R $USER vivace

echo -e "\e[1;33mPlotting window graph for 60Mbps \e[0m"
gnuplot window-fixed.gp
mv window-fixed.svg results/window-fixed-bandwidth.svg

echo -e "\e[1;33mPlotting loss graph for 60Mbps \e[0m"
gnuplot loss-fixed.gp
mv loss-fixed.svg results/loss-fixed-bandwidth.svg

echo -e "\e[1;33mPlotting latency graph for 60Mbps \e[0m"
gnuplot latency-fixed.gp
mv latency-fixed.svg results/latency-fixed-bandwidth.svg

echo -e "\e[1;33mPlotting window graph for range of bandwidths \e[0m"
python3 window.py $INTERVAL
gnuplot -e "labelname='Bandwidth (Mbps)'" window-varied.gp
mv window-varied.svg results/window-varied-bandwidth.svg

echo -e "\e[1;33mPlotting loss graph for range of bandwidths \e[0m"
python3 loss.py $INTERVAL
gnuplot -e "labelname='Bandwidth (Mbps)'" loss-varied.gp
mv loss-varied.svg results/loss-varied-bandwidth.svg

echo -e "\e[1;33mPlotting latency graph for range of bandwidths \e[0m"
python3 latency.py $INTERVAL
gnuplot -e "labelname='Bandwidth (Mbps)'" latency-varied.gp
mv latency-varied.svg results/latency-varied-bandwidth.svg

echo -e "\e[1;31mRemoving old backups \e[0m"
rm -rf bandwidth
mkdir bandwidth

echo -e "\e[1;32mBacking up logs \e[0m"
mv reno bandwidth/
mv cubic bandwidth/
mv vivace bandwidth/
