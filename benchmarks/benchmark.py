# -*- coding: utf-8 -*-

import time
import multiprocessing

NUM_CALLS = 10000


def run_sum_server():
    from gevent.server import StreamServer
    from mprpc import RPCServer

    class SumServer(RPCServer):
        def sum(self, x, y):
            return x + y

    server = StreamServer(('127.0.0.1', 6000), SumServer)
    server.serve_forever()


def call0():
    from mprpc import RPCClient
    client = RPCClient('127.0.0.1', 6000)
    start = time.time()
    [client.call('sum', 1, 2) for _ in xrange(NUM_CALLS)]
    print 'call0: %d qps' % (NUM_CALLS / (time.time() - start))



def call1():
    from mprpc import RPCSimple
    client = RPCSimple('127.0.0.1', 6000)
    start = time.time()
    [client.call('sum', 1, 2) for _ in xrange(NUM_CALLS)]
    print 'call1: %d qps' % (NUM_CALLS / (time.time() - start))


def call2():
    from mprpc import PIKSimple
    client = PIKSimple('127.0.0.1', 6000)
    start = time.time()
    [client.call('sum', 1, 2) for _ in xrange(NUM_CALLS)]
    print 'call2: %d qps' % (NUM_CALLS / (time.time() - start))


def call_using_connection_pool():
    from mprpc import RPCPoolClient
    import gevent.pool
    import gsocketpool.pool
    def _call(n):
        with client_pool.connection() as client:
            return client.call('sum', 1, 2)
    options = dict(host='127.0.0.1', port=6000)
    client_pool = gsocketpool.pool.Pool(RPCPoolClient, options, initial_connections=20)
    glet_pool = gevent.pool.Pool(20)
    start = time.time()
    [None for _ in glet_pool.imap_unordered(_call, xrange(NUM_CALLS))]
    print 'call_using_connection_pool: %d qps' % (NUM_CALLS / (time.time() - start))



def call4():
    from mprpc import STRSimple
    client = STRSimple('127.0.0.1', 6000)
    start = time.time()
    #[client.call('bday', body='1234') for _ in xrange(NUM_CALLS)]
    #print 'call2: %d qps' % (NUM_CALLS / (time.time() - start))
    print client.call('bday', '1234').recv(100)



def call5():
    from mprpc import URISimple
    client = URISimple('127.0.0.1', 6000)
    start = time.time()
    #[client.call('bday', body='1234') for _ in xrange(NUM_CALLS)]
    #print 'call2: %d qps' % (NUM_CALLS / (time.time() - start))
    print client.call('test', a1='1234',a2='33').recv(100)
    print client.call('test', a1='1234',a2='33').recv(100)
    print client.call('test', a1='1234',a2='33').recv(100)


if __name__ == '__main__':
    #p = multiprocessing.Process(target=run_sum_server)
    #p.start()

    #call0()

    #$call1()
    #call2()
    #call4()
    call5()

    #call_using_connection_pool()

    #p.terminate()
