# -*- coding: utf-8 -*-

import time
import socket
try:
    import msgpack
except:
    pass
try:
    import cPickle as pickle
except:
    import pickle

MSGPACKRPC_REQUEST = 0
MSGPACKRPC_RESPONSE = 1
SOCKET_RECV_SIZE = 1024 ** 2
#MSGPACK,STRINGS,PICKLES
METHOD_RECV_SIZE = 7

class RPCProtocolError(Exception):
    pass
class MethodNotFoundError(Exception):
    pass
class RPCError(Exception):
    pass

class ClientRPC(object):
    def __init__(self, host, port, timeout=None, lazy=False,pack_encoding='utf-8', unpack_encoding='utf-8'):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._msg_id = 0
        self._socket = None
        self._packer = msgpack.Packer(encoding=pack_encoding)
        self._unpacker = msgpack.Unpacker(encoding=unpack_encoding, use_list=False)
        if not lazy:
            self.open()
    def open(self):
        assert self._socket is None, 'The connection has already been established'
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._host, self._port))
        if self._timeout:
            self._socket.settimeout(self._timeout)
    def close(self):
        assert self._socket is not None, 'Attempt to close an unopened socket'
        try:
            self._socket.close()
        except:
            pass
        self._socket = None
    def is_connected(self):
        if self._socket:
            return True
        else:
            return False
    def msgpack_call(self, method, *args,**kwargs):
        req = self._msgpack__create_request(method, args,kwargs)
        self._socket.sendall(req)
        while True:
            data = self._socket.recv(SOCKET_RECV_SIZE)
            if not data:
                raise IOError('Connection closed')
            self._unpacker.feed(data)
            try:
                response = self._unpacker.next()
                break
            except StopIteration:
                continue
        return self._msgpack__parse_response(response)
    def _msgpack__create_request(self, method, args,kwargs):
        self._msg_id += 1
        req = (MSGPACKRPC_REQUEST, self._msg_id, method, args,kwargs)
        return self._packer.pack(req)
    def _msgpack__parse_response(self,response):
        if (len(response) != 5 or response[0] != MSGPACKRPC_RESPONSE):
            raise RPCProtocolError('Invalid protocol')
        (_, msg_id, error, result) = response
        if msg_id != self._msg_id:
            raise RPCError('Invalid Message ID')
        if error:
            raise RPCError(str(error))
        return result
    def call(self, str method, *args, **kwargs):
        return self.msgpack_call(method, *args, **kwargs)

