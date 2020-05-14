import sys
import pandas as pd

rlog = open('reno/loss.log', 'w')
clog = open('cubic/loss.log', 'w')
vlog = open('vivace/loss.log', 'w')

offset = int(sys.argv[1])
step = int(sys.argv[2])
count = int(sys.argv[3]) + 1

for i in range(1, count):
	reno = pd.read_csv('reno/server/s%d/loss.log' % i, sep=' ', header=None)
	speed = offset + (i * step)
	loss = reno.tail(1).iat[0,0]
	rlog.write('{0} {1}\n'.format(speed, loss))

for i in range(1, count):
	cubic = pd.read_csv('cubic/server/s%d/loss.log' % i, sep=' ', header=None)
	speed = offset + (i * step)
	loss = cubic.tail(1).iat[0,0]
	clog.write('{0} {1}\n'.format(speed, loss))

for i in range(1, count):
	vivace = pd.read_csv('vivace/server/s%d/loss.log' % i, sep=' ', header=None)
	speed = offset + (i * step)
	loss = vivace.tail(1).iat[0,0]
	vlog.write('{0} {1}\n'.format(speed, loss))

rlog.close()
clog.close()
vlog.close()
