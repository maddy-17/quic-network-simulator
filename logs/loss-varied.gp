# Key
set key inside bottom right

# Borders
set style line 101 lc rgb '#000000' lt 1.5 lw 1.5
set border 3 front ls 101
set tics nomirror out scale 0.75

# Arrows
set arrow from graph 1,0 to graph 1.05,0 size screen 0.025,15,60 \
    filled ls 101
set arrow from graph 0,1 to graph 0,1.05 size screen 0.025,15,60 \
    filled ls 101

# Grid
set style line 102 lc rgb '#454545' lt 0 lw 1
set grid back ls 102

# Labels
set xlabel labelname offset 0, 0.25
set ylabel 'Packets Lost' offset 2
set title 'LOSS' font ',18'

# Padding
set offset 1, 1, 1, 1

# Line Styles
set style line 1 linecolor rgb '#E6193C' linewidth 2 pt 7 ps 0.6
set style line 2 linecolor rgb '#01A252' linewidth 2 pt 7 ps 0.6
set style line 3 linecolor rgb '#3949AB' linewidth 2 pt 7 ps 0.6

# Plot

set terminal svg
set output 'loss-varied.svg'
plot "reno/loss.log" using 1:2 title 'Default' with linespoints linestyle 1, \
"cubic/loss.log" using 1:2 title 'Event-Based' with linespoints linestyle 2, \
"vivace/loss.log" using 1:2 title 'Performance-Based' with linespoints linestyle 3

set terminal pngcairo
set output 'loss-varied.png'
replot
