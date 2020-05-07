import sys
import pandas as pd

offset = int(sys.argv[1])
step = int(sys.argv[2])

reno = pd.read_csv('reno/throughput.log', sep=' ', header=None)
reno[1] = [(offset + (i * step)) for i in range(1, len(reno) + 1)]
reno.to_csv('reno/throughput.log', sep=' ', header=False, index=False)

cubic = pd.read_csv('cubic/throughput.log', sep=' ', header=None)
cubic[1] = [(offset + (i * step)) for i in range(1, len(cubic) + 1)]
cubic.to_csv('cubic/throughput.log', sep=' ', header=False, index=False)

vivace = pd.read_csv('vivace/throughput.log', sep=' ', header=None)
vivace[1] = [(offset + (i * step)) for i in range(1, len(vivace) + 1)]
vivace.to_csv('vivace/throughput.log', sep=' ', header=False, index=False)
