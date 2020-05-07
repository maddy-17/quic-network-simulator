# Key
set key inside top right

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
set xlabel 'Time (s)' offset 0, 0.25
set ylabel 'RTT (ms)' offset 2
set title 'LATENCY' font ',18'

# Padding
set offset 1, 1, 1, 1

# Point Styles
set style fill solid 1.00
set style line 1 linecolor rgb '#E6193C' lt 1 pt 5 ps 0.3
set style line 2 linecolor rgb '#01A252' lt 1 pt 7 ps 0.3
set style line 3 linecolor rgb '#3949AB' lt 1 pt 9 ps 0.3

# Plot
set terminal svg
set output 'latency-fixed.svg'
plot "reno/server/s6/latency.log" using 3:2 title 'Default' with points linestyle 1, \
"cubic/server/s6/latency.log" using 3:2 title 'Event-Based' with points linestyle 2, \
"vivace/server/s6/latency.log" using 3:2 title 'Performance-Based' with points linestyle 3

# set terminal png
# set output 'reno-latency.png'
# plot "reno-server-latency.log" using 3:2 title 'NewReno' with boxes linestyle 1

# set terminal png
# set output 'cubic-latency.png'
# plot "cubic-server-latency.log" using 3:2 title 'Loss-Based' with boxes linestyle 2

# set terminal png
# set output 'vivace-latency.png'
# plot "vivace-server-latency.log" using 3:2 title 'Performance-Based' with boxes linestyle 3
