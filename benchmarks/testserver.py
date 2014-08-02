# -*- coding: utf-8 -*-

import time
from gevent.server import StreamServer
from mprpc import RPCServer

def run_sum_server():

    class SumServer(RPCServer):
        def sum(self, x, y):
            return x + y

    server = StreamServer(('127.0.0.1', 6000), SumServer)
    server.serve_forever()

if __name__ == '__main__':
    run_sum_server()
