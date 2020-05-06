import sys
import pandas as pd

rlog = open('reno/window.log', 'w')
clog = open('cubic/window.log', 'w')
vlog = open('vivace/window.log', 'w')

interval = sys.argv[1]

for i in range(1, 11):
	reno = pd.read_csv('reno/server/s%d/window.log' % i, sep=' ', header=None)
	speed = i * interval
	window = reno[0].mean()
	rlog.write('{0} {1}\n'.format(speed, window))

for i in range(1, 11):
	cubic = pd.read_csv('cubic/server/s%d/window.log' % i, sep=' ', header=None)
	speed = i * interval
	window = cubic[0].mean()
	clog.write('{0} {1}\n'.format(speed, window))

for i in range(1, 11):
	vivace = pd.read_csv('vivace/server/s%d/window.log' % i, sep=' ', header=None)
	speed = i * interval
	window = vivace[0].mean()
	vlog.write('{0} {1}\n'.format(speed, window))

rlog.close()
clog.close()
vlog.close()
