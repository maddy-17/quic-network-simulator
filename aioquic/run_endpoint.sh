#!/bin/bash

# Set up the routing needed for the simulation.
/setup.sh

# The following variables are available for use:
# - ROLE contains the role of this execution context, client or server
# - SERVER_PARAMS contains user-supplied command line parameters
# - CLIENT_PARAMS contains user-supplied command line parameters

if [ "$ROLE" = "client" ]; then
    # Wait for the simulator to start up.
    /wait-for-it.sh sim:57832 -s -t 30

    # echo "Starting client"
	# python examples/http3_client.py \
	# 	--ca-certs tests/pycacert.pem \
	# 	--verbose \
	# 	$CLIENT_PARAMS \
	# 	$REQUESTS 2>> /logs/client_stderr.log

elif [ "$ROLE" = "server" ]; then
    echo "Starting server"
	python examples/http3_server.py \
		--certificate tests/ssl_cert.pem \
		--private-key tests/ssl_key.pem \
		--verbose \
		$SERVER_PARAMS 2>> /logs/server_stderr.log
fi