import socket, ssl
import time
import requests

# context = ssl.SSLContext()
# context.verify_mode = ssl.CERT_REQUIRED
# context.check_hostname = True
# context.load_default_certs()

# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# ssl_sock = context.wrap_socket(s, server_hostname='pritunl.siliconcupcake.wtf')
# start = time.time()
# ssl_sock.connect(('pritunl.siliconcupcake.wtf', 443))
# perfTime = time.time() - start

# print ("Handshake Time: %.1f ms" % (perfTime * 1000))

start = time.time()
requests.get('https://pritunl.siliconcupcake.wtf/videos/cards.mp4')
perfTime = time.time() - start

print ("Data Transfer Time: %.1f s" % (perfTime))