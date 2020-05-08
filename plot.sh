cd logs

SAVE_DIR=$1
RESULT_DIR=${SAVE_DIR}/results

OFFSET=0
STEP=1

rm -rf ${SAVE_DIR}
mkdir ${SAVE_DIR}
mkdir ${RESULT_DIR}

sudo chown -R $USER reno
sudo chown -R $USER cubic
sudo chown -R $USER vivace

for ITERATION in $(eval echo {1..$2})
do
    ITERATION_DIR=${RESULT_DIR}/ITERATION-${ITERATION}
    mkdir ${ITERATION_DIR}

    echo -e "\e[1;33mPlotting window graph for iteration ${ITERATION} \e[0m"
    gnuplot -e "ITERATION=${ITERATION}" window-fixed.gp
    mv window-fixed.svg ${ITERATION_DIR}/window-fixed.svg
    mv window-fixed.png ${ITERATION_DIR}/window-fixed.png

    echo -e "\e[1;33mPlotting loss graph for iteration ${ITERATION} \e[0m"
    gnuplot -e "ITERATION=${ITERATION}" loss-fixed.gp
    mv loss-fixed.svg ${ITERATION_DIR}/loss-fixed.svg
    mv loss-fixed.png ${ITERATION_DIR}/loss-fixed.png

    echo -e "\e[1;33mPlotting latency graph for iteration ${ITERATION} \e[0m"
    gnuplot -e "ITERATION=${ITERATION}" latency-fixed.gp
    mv latency-fixed.svg ${ITERATION_DIR}/latency-fixed.svg
    mv latency-fixed.png ${ITERATION_DIR}/latency-fixed.png
done

echo -e "\e[1;33mPlotting window graph against iterations \e[0m"
python3 window.py $OFFSET $STEP
gnuplot -e "labelname='Iteration'" window-varied.gp
mv window-varied.svg ${RESULT_DIR}/window-iterations.svg
mv window-varied.png ${RESULT_DIR}/window-iterations.png

echo -e "\e[1;33mPlotting loss graph against iterations \e[0m"
python3 loss.py $OFFSET $STEP
gnuplot -e "labelname='Iteration'" loss-varied.gp
mv loss-varied.svg ${RESULT_DIR}/loss-iterations.svg
mv loss-varied.png ${RESULT_DIR}/loss-iterations.png

echo -e "\e[1;33mPlotting latency graph against iterations \e[0m"
python3 latency.py $OFFSET $STEP
gnuplot -e "labelname='Iteration'" latency-varied.gp
mv latency-varied.svg ${RESULT_DIR}/latency-iterations.svg
mv latency-varied.png ${RESULT_DIR}/latency-iterations.png

echo -e "\e[1;33mPlotting throughput graph against iterations \e[0m"
python3 throughput.py $OFFSET $STEP
gnuplot -e "labelname='Iteration'" throughput-varied.gp
mv throughput-varied.svg ${RESULT_DIR}/throughput-iterations.svg
mv throughput-varied.png ${RESULT_DIR}/throughput-iterations.png

echo -e "\e[1;32mBacking up logs \e[0m"
mv reno ${SAVE_DIR}/
mv cubic ${SAVE_DIR}/
mv vivace ${SAVE_DIR}/