#!/bin/bash

SAVE_DIR="drop-rate-varied"
RESULT_DIR=${SAVE_DIR}/results

echo -e "\e[1;33mRunning tests with varying drop-rate \e[0m"
REQUEST=5000000
RCOUNT=1
ICOUNT=5
STEP=1
OFFSET=0
for ITERATION in $(eval echo {1..$ICOUNT})
do
    let DROP_RATE="$OFFSET + ($ITERATION * $STEP)"
    echo -e "\e[1;34mSetting drop rate to ${DROP_RATE} % \e[0m"
    export SCENARIO="drop-rate --delay=30ms \
        --bandwidth=10Mbps \
        --queue=50 \
        --rate_to_server=0 \
        --rate_to_client=${DROP_RATE}"
    for CC in {0..2}
    do
        export SERVER_PARAMS="--cc ${CC}"
        export CLIENT_PARAMS="--cc ${CC} -r ${REQUEST} -n ${RCOUNT}"
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
echo -e "\e[1;31mRemoving old backups \e[0m"
rm -rf ${SAVE_DIR}
mkdir ${SAVE_DIR}
mkdir ${RESULT_DIR}

sudo chown -R $USER reno
sudo chown -R $USER cubic
sudo chown -R $USER vivace

for PHASE in $(eval echo {1..$ICOUNT})
do
    let PHASE_DR="$OFFSET + ($PHASE * $STEP)"
    PHASE_DIR=${RESULT_DIR}/phase-${PHASE_DR}
    mkdir ${PHASE_DIR}

    echo -e "\e[1;33mPlotting window graph for ${PHASE_DR} % \e[0m"
    gnuplot -e "phase=${PHASE}" window-fixed.gp
    mv window-fixed.svg ${PHASE_DIR}/window-fixed-drop-rate.svg
    mv window-fixed.png ${PHASE_DIR}/window-fixed-drop-rate.png

    echo -e "\e[1;33mPlotting loss graph for ${PHASE_DR} % \e[0m"
    gnuplot -e "phase=${PHASE}" loss-fixed.gp
    mv loss-fixed.svg ${PHASE_DIR}/loss-fixed-drop-rate.svg
    mv loss-fixed.png ${PHASE_DIR}/loss-fixed-drop-rate.png

    echo -e "\e[1;33mPlotting latency graph for ${PHASE_DR} % \e[0m"
    gnuplot -e "phase=${PHASE}" latency-fixed.gp
    mv latency-fixed.svg ${PHASE_DIR}/latency-fixed-drop-rate.svg
    mv latency-fixed.png ${PHASE_DIR}/latency-fixed-drop-rate.png
done

echo -e "\e[1;33mPlotting window graph for range of drop-rates \e[0m"
python3 window.py $OFFSET $STEP $ICOUNT
gnuplot -e "labelname='Drop Rate (%)'" window-varied.gp
mv window-varied.svg ${RESULT_DIR}/window-varied-drop-rate.svg
mv window-varied.png ${RESULT_DIR}/window-varied-drop-rate.png

echo -e "\e[1;33mPlotting loss graph for range of drop-rates \e[0m"
python3 loss.py $OFFSET $STEP $ICOUNT
gnuplot -e "labelname='Drop Rate (%)'" loss-varied.gp
mv loss-varied.svg ${RESULT_DIR}/loss-varied-drop-rate.svg
mv loss-varied.png ${RESULT_DIR}/loss-varied-drop-rate.png

echo -e "\e[1;33mPlotting latency graph for range of drop-rates \e[0m"
python3 latency.py $OFFSET $STEP $ICOUNT
gnuplot -e "labelname='Drop Rate (%)'" latency-varied.gp
mv latency-varied.svg ${RESULT_DIR}/latency-varied-drop-rate.svg
mv latency-varied.png ${RESULT_DIR}/latency-varied-drop-rate.png

echo -e "\e[1;33mPlotting throughput graph for range of drop-rates \e[0m"
python3 throughput.py $OFFSET $STEP
gnuplot -e "labelname='Drop Rate (%)'" throughput-varied.gp
mv throughput-varied.svg ${RESULT_DIR}/throughput-varied-drop-rate.svg
mv throughput-varied.png ${RESULT_DIR}/throughput-varied-drop-rate.png

echo -e "\e[1;32mBacking up logs \e[0m"
mv reno ${SAVE_DIR}/
mv cubic ${SAVE_DIR}/
mv vivace ${SAVE_DIR}/
