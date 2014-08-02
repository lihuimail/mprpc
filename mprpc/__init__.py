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
except:
    pass