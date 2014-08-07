# -*- coding: utf-8 -*-

try:
    from client import RPCClient, RPCPoolClient
except:
    pass
try:
    from server import RPCServer
except:
    pass
try:
    from client_simple import ClientRPC as RPCSimple
    from client_simple import ClientPIK as PIKSimple
    from client_simple import ClientSTR as STRSimple
    from client_simple import ClientURI as URISimple
except:
    pass


def get_client_class(host=None,port=None,timeout=None,lazy=False,pack_encoding='utf-8',unpack_encoding='utf-8',with_type=None):
    if with_type is None or with_type=='client_normal':
        result=RPCClient(host,port)
    elif with_type=='client_pool':
        raise
    elif with_type=='client_simple':
        result=RPCSimple(host,port)
    elif with_type=='client_pickle':
        result=PIKSimple(host,port)
    elif with_type=='client_string':
        result=STRSimple(host,port)
    elif with_type=='client_urihttp':
        result=URISimple(host,port)
    else:
        raise
    return result