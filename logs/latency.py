import sys
import pandas as pd

rlog = open('reno/latency.log', 'w')
clog = open('cubic/latency.log', 'w')
vlog = open('vivace/latency.log', 'w')

interval = sys.argv[1]

for i in range(1, 11):
	reno = pd.read_csv('reno/server/s%d/latency.log' % i, sep=' ', header=None)
	speed = i * interval
	latency = reno[0].mean()
	rlog.write('{0} {1}\n'.format(speed, latency))

for i in range(1, 11):
	cubic = pd.read_csv('cubic/server/s%d/latency.log' % i, sep=' ', header=None)
	speed = i * interval
	latency = cubic[0].mean()
	clog.write('{0} {1}\n'.format(speed, latency))

for i in range(1, 11):
	vivace = pd.read_csv('vivace/server/s%d/latency.log' % i, sep=' ', header=None)
	speed = i * interval
	latency = vivace[0].mean()
	vlog.write('{0} {1}\n'.format(speed, latency))

rlog.close()
clog.close()
vlog.close()
