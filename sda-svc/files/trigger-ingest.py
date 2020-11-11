#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests the installed release"""

import sys
import json
import argparse
import os
import ssl
import sys
import urllib.parse
from pathlib import Path

import pika

# Command-line arguments
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--connection', help="of the form 'amqp://<user>:<password>@<host>:<port>/<vhost>'")
parser.add_argument('--latest_message', action='store_true')
parser.add_argument('user')
parser.add_argument('filepath')
args = parser.parse_args()

exchange = os.getenv('MQ_EXCHANGE','localega')

env_connection = "amqps://%s:%s@%s/%s" % (
    os.getenv('MQ_USER', 'user'),
    os.getenv('MQ_PASSWORD', 'password'),
    os.getenv('MQ_HOST', 'mq'),
    urllib.parse.quote(os.getenv('MQ_VHOST', '/'), safe=''))


# MQ Connection
mq_connection = args.connection if args.connection else env_connection
parameters = pika.URLParameters(mq_connection)

if mq_connection.startswith('amqps'):

    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)  # Enforcing (highest) TLS version (so... 1.2?)

    context.check_hostname = False

    cacertfile = Path('/certs/ca.crt')
    certfile = Path('/certs/tester.ca.crt')
    keyfile = Path('/certs/tester.ca.key')

    context.verify_mode = ssl.CERT_NONE
    # Require server verification
    if cacertfile.exists():
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cafile=str(cacertfile))
        
    # If client verification is required
    if certfile.exists():
        assert( keyfile.exists() )
        context.load_cert_chain(str(certfile), keyfile=str(keyfile))

    # Finally, the pika ssl options
    parameters.ssl_options = pika.SSLOptions(context=context, server_hostname=None)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

message = """
{
  "type": "ingest",
  "user": "%s",
  "filepath": "%s"
}
""" % (args.user, args.filepath)

channel.basic_publish(exchange=exchange,
                      routing_key= 'files',
                      body=message,
                      properties=pika.BasicProperties(correlation_id="1",
                                                      content_type='application/json',
                                                      delivery_mode=2))

connection.close()