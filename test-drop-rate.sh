#!/bin/bash

cd logs
if [[ ! -e results ]]; then
    mkdir results

echo "Running tests with varying drop-rate"
# Run different sims with docker here

echo "Plotting window graph for 0.6%"
gnuplot window-fixed.gp
mv window-fixed.svg results/window-fixed-drop-rate.svg

echo "Plotting loss graph for 0.6%"
gnuplot loss-fixed.gp
mv loss-fixed.svg results/loss-fixed-drop-rate.svg

echo "Plotting latency graph for 0.6%"
gnuplot latency-fixed.gp
mv latency-fixed.svg results/latency-fixed-drop-rate.svg

echo "Plotting window graph for range of drop-rates"
python3 window.py
gnuplot -e "labelname='Drop Rate (%)'" window-varied.gp
mv window-varied.svg results/window-varied-drop-rate.svg

echo "Plotting loss graph for range of drop-rates"
python3 loss.py
gnuplot -e "labelname='Drop Rate (%)'" loss-varied.gp
mv loss-varied.svg results/loss-varied-drop-rate.svg

echo "Plotting latency graph for range of drop-rates"
python3 latency.py
gnuplot -e "labelname='Drop Rate (%)'" latency-varied.gp
mv latency-varied.svg results/latency-varied-drop-rate.svg

echo "Removing old backups"
rm -rf drop-rate
mkdir drop-rate

echo "Backing up logs"
mv reno drop-rate/
mv cubic drop-rate/
mv vivace drop-rate/
