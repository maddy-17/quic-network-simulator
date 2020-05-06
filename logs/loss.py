import pandas as pd

rlog = open('reno/loss.log', 'w')
clog = open('cubic/loss.log', 'w')
vlog = open('vivace/loss.log', 'w')

for i in range(1, 11):
	reno = pd.read_csv('reno/server/s%d/loss.log' % i, sep=' ', header=None)
	speed = i * 10
	loss = reno.tail(1).iat[0,0]
	rlog.write('{0} {1}\n'.format(speed, loss))

for i in range(1, 11):
	cubic = pd.read_csv('cubic/server/s%d/loss.log' % i, sep=' ', header=None)
	speed = i * 10
	loss = cubic.tail(1).iat[0,0]
	clog.write('{0} {1}\n'.format(speed, loss))

for i in range(1, 11):
	vivace = pd.read_csv('vivace/server/s%d/loss.log' % i, sep=' ', header=None)
	speed = i * 10
	loss = vivace.tail(1).iat[0,0]
	vlog.write('{0} {1}\n'.format(speed, loss))

rlog.close()
clog.close()
vlog.close()
