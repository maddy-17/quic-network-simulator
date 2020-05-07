cd logs

SAVE_DIR=$1
OFFSET=0
STEP=1

rm -rf ${SAVE_DIR}
mkdir ${SAVE_DIR}
RESULT_DIR=${SAVE_DIR}/results

if [[ ! -e ${RESULT_DIR} ]]; then
    mkdir ${RESULT_DIR}
fi

sudo chown -R $USER reno
sudo chown -R $USER cubic
sudo chown -R $USER vivace

echo -e "\e[1;33mPlotting window graph against time \e[0m"
gnuplot window-fixed.gp
mv window-fixed.svg ${RESULT_DIR}/window-time.svg

echo -e "\e[1;33mPlotting loss graph against time \e[0m"
gnuplot loss-fixed.gp
mv loss-fixed.svg ${RESULT_DIR}/loss-time.svg

echo -e "\e[1;33mPlotting latency graph against time \e[0m"
gnuplot latency-fixed.gp
mv latency-fixed.svg ${RESULT_DIR}/latency-time.svg

echo -e "\e[1;33mPlotting window graph against iterations \e[0m"
python3 window.py $OFFSET $STEP
gnuplot -e "labelname='Iteration'" window-varied.gp
mv window-varied.svg ${RESULT_DIR}/window-iterations.svg

echo -e "\e[1;33mPlotting loss graph against iterations \e[0m"
python3 loss.py $OFFSET $STEP
gnuplot -e "labelname='Iteration'" loss-varied.gp
mv loss-varied.svg ${RESULT_DIR}/loss-iterations.svg

echo -e "\e[1;33mPlotting latency graph against iterations \e[0m"
python3 latency.py $OFFSET $STEP
gnuplot -e "labelname='Iteration'" latency-varied.gp
mv latency-varied.svg ${RESULT_DIR}/latency-iterations.svg

echo -e "\e[1;33mPlotting throughput graph against iterations \e[0m"
python3 throughput.py $OFFSET $STEP
gnuplot -e "labelname='Iteration'" throughput-varied.gp
mv throughput-varied.svg ${RESULT_DIR}/throughput-iterations.svg

echo -e "\e[1;32mBacking up logs \e[0m"
mv reno ${SAVE_DIR}/
mv cubic ${SAVE_DIR}/
mv vivace ${SAVE_DIR}/