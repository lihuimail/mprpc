# -*- coding: utf-8 -*-

import time
from gevent.server import StreamServer
from mprpc import RPCServer

def run_sum_server():

    class SumServer(RPCServer):
        def sum(self, x, y):
            return x + y
        def bday(self):
            result=self.handle_read(1000)
            print 'result',result
            return result
        def test(self,a1=None,a2=None):
            print '11111111111111',a1,a2
            return a1

    server = StreamServer(('127.0.0.1', 6000), SumServer)
    server.serve_forever()

if __name__ == '__main__':
    run_sum_server()
