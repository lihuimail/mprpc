# -*- coding: utf-8 -*-

import urllib
import logging
import msgpack
import cPickle as pickle
try:
    from gevent.coros import Semaphore
except:
    pass

from exceptions import MethodNotFoundError, RPCProtocolError
from constants import MSGPACKRPC_REQUEST, MSGPACKRPC_RESPONSE, SOCKET_RECV_SIZE,METHOD_RECV_SIZE,METHOD_STRINGS_SIZE,METHOD_URIHTTP_SIZE

#####################################################
cdef tuple decode_urihttp(url):
    kwargs={}
    method='default'
    if url is None:
        return method,tuple(),kwargs
    url=url.strip()
    if url.find('?')==-1 and url.find('|')!=-1:
        url=url.replace('|','?')
    if url.find('?')!=-1:
        method,a1=url.split('?',1)
        if a1.find('#')!=-1:
            a1=a1.split('#')[0]
    else:
        method=url
        a1=''
    method='/'.join([v.strip() for v in method.strip('/').split('/') if v.strip()])
    if method.find('/')==-1:
        a2=''
    else:
        method,a2=method.split('/',1)
    args=[v for v in a2.split('/') if v]
    if method=='':
        method='default'
    if a1=='':
        return method,tuple(args),kwargs
    for v in a1.split('&'):
        if not v:
            continue
        elif v.find('=')==-1:
            continue
        v1,v2=v.split('=',1)
        if v2.find('%')!=-1:
            v2=urllib.unquote(v2)
        kwargs[v1]=v2
    result=method,tuple(args),kwargs
    return result

#####################################################
cdef class RPCServer:
    """RPC server.

    This class is assumed to be used with gevent StreamServer.

    :param socket: Socket object.
    :param tuple address: Client address.
    :param str pack_encoding: (optional) Character encoding used to pack data
        using Messagepack.
    :param str unpack_encoding: (optional) Character encoding used to unpack
        data using Messagepack.

    Usage:
        >>> from gevent.server import StreamServer
        >>> import mprpc
        >>> 
        >>> class SumServer(mprpc.RPCServer):
        ...     def sum(self, x, y):
        ...         return x + y
        ... 
        >>> 
        >>> server = StreamServer(('127.0.0.1', 6000), SumServer)
        >>> server.serve_forever()
    """

    cdef _socket
    cdef _packer
    cdef _unpacker
    cdef _send_lock

    #####################################################
    def __init__(self, sock, address, pack_encoding='utf-8',unpack_encoding='utf-8'):
        self._socket = sock
        self._packer = msgpack.Packer(encoding=pack_encoding)
        self._unpacker = msgpack.Unpacker(encoding=unpack_encoding,use_list=False)
        try:
            self._send_lock = Semaphore()
        except:
            self._send_lock = None
        self._run()
    def __del__(self):
        try:
            self._socket.close()
        except:
            logging.exception('Failed to clean up the socket')

    #####################################################
    def _run(self):
        cdef bytes rpc_type
        cdef int result=0
        while True:
            rpc_type = self._socket.recv(METHOD_RECV_SIZE)
            if not rpc_type:
                logging.debug('Client disconnected')
                break
            if rpc_type == 'MSGPACK:':
                result=self._msgpack_run()
            elif rpc_type=='STRINGS:':
                result=self._strings_run()
            elif rpc_type=='PICKLES:':
                result=self._pickles_run()
            elif rpc_type=='URIHTTP:':
                result=self._urihttp_run()
            elif rpc_type=='UNKOWNS:':
                raise
            elif rpc_type=='FILEOBJ:':
                raise
            elif rpc_type=='BUFFERS:':
                raise
            elif rpc_type=='JSONSTR:':
                raise
            elif rpc_type=='BSONSTR:':
                raise
            else:
                self._unpacker.feed(rpc_type)
                result=self._msgpack_run()
            if result==-1:
                logging.debug('Client disconnected')
                break

    #####################################################
    def test_connect(self,*args,**kwargs):
        return '1'

    #####################################################
    def _get_handle(self):
        return self._socket
    cdef bytes _handle_read(self,int length):
        return self._socket.recv(length)
    cdef bytes _handle_write(self,bytes value):
        if self._send_lock:
            self._send_lock.acquire()
        try:
            self._socket.sendall(value)
        finally:
            if self._send_lock:
                self._send_lock.release()
        return True
    def _system_read(self,length):
        return self._socket.recv(length)
    def _system_write(self,value):
        if self._send_lock:
            self._send_lock.acquire()
        try:
            self._socket.sendall(value)
        finally:
            if self._send_lock:
                self._send_lock.release()
        return True

    #####################################################
    cdef int  _msgpack_run(self):
        cdef bytes data
        cdef tuple req, args
        cdef dict kwargs
        cdef int msg_id=0
        cdef int result=0
        while True:
            data = self._socket.recv(SOCKET_RECV_SIZE)
            if not data:
                logging.debug('Client disconnected')
                result=-1
                break
            self._unpacker.feed(data)
            try:
                req = self._unpacker.next()
            except StopIteration:
                continue
            (msg_id, method, args, kwargs) = self._msgpack_parse_request(req)
            try:
                ret = method(*args,**kwargs)
            except Exception, e:
                logging.exception('An error has occurred')
                self._msgpack_send_error(str(e), msg_id)
                result=0
                break
            else:
                self._msgpack_send_result(ret, msg_id)
                result=0
                break
        return result
    cdef tuple _msgpack_parse_request(self, tuple req):
        if (len(req) != 5 or req[0] != MSGPACKRPC_REQUEST):
            raise RPCProtocolError('Invalid protocol')
        cdef tuple args
        cdef dict kwargs
        cdef int msg_id=0
        (_, msg_id, method_name, args ,kwargs) = req
        if method_name.startswith('_'):
            raise MethodNotFoundError('Method not callow: %s', method_name)
        if not hasattr(self, method_name):
            raise MethodNotFoundError('Method not found: %s', method_name)
        method = getattr(self, method_name)
        if not hasattr(method, '__call__'):
            raise MethodNotFoundError('Method is not callable: %s', method_name)
        return (msg_id, method, args, kwargs)
    cdef _msgpack_send_result(self, object result, int msg_id):
        msg = (MSGPACKRPC_RESPONSE, msg_id, None, result)
        self._msgpack_send(msg)
    cdef _msgpack_send_error(self, str error, int msg_id):
        msg = (MSGPACKRPC_RESPONSE, msg_id, error, None)
        self._msgpack_send(msg)
    cdef _msgpack_send(self,tuple  msg):
        if self._send_lock:
            self._send_lock.acquire()
        try:
            self._socket.sendall(self._packer.pack(msg))
        finally:
            if self._send_lock:
                self._send_lock.release()

    #####################################################
    cdef int _pickles_run(self):
        cdef bytes data
        cdef tuple req, args
        cdef dict kwargs
        cdef int msg_id=0
        cdef int result=0
        data = self._socket.recv(SOCKET_RECV_SIZE)
        if not data:
            logging.debug('Client disconnected')
            result=-1
            return result
        try:
            req = pickle.loads(data)
        except Exception, e:
            logging.exception('An error has occurred')
            self._pickles_send_error(str(e), msg_id)
            result=0
            return result
        (msg_id, method, args, kwargs) = self._pickles_parse_request(req)
        try:
            ret = method(*args,**kwargs)
        except Exception, e:
            logging.exception('An error has occurred')
            self._pickles_send_error(str(e), msg_id)
            result=0
        else:
            self._pickles_send_result(ret, msg_id)
            result=0
        return result
    cdef tuple _pickles_parse_request(self, tuple req):
        if (len(req) != 5 or req[0] != MSGPACKRPC_REQUEST):
            raise RPCProtocolError('Invalid protocol')
        cdef tuple args
        cdef dict kwargs
        cdef int msg_id=0
        (_, msg_id, method_name, args ,kwargs) = req
        if method_name.startswith('_'):
            raise MethodNotFoundError('Method not callow: %s', method_name)
        if not hasattr(self, method_name):
            raise MethodNotFoundError('Method not found: %s', method_name)
        method = getattr(self, method_name)
        if not hasattr(method, '__call__'):
            raise MethodNotFoundError('Method is not callable: %s', method_name)
        return (msg_id, method, args, kwargs)
    cdef _pickles_send_result(self, object result, int msg_id):
        msg = (MSGPACKRPC_RESPONSE, msg_id, None, result)
        self._pickles_send(msg)
    cdef _pickles_send_error(self, str error, int msg_id):
        msg = (MSGPACKRPC_RESPONSE, msg_id, error, None)
        self._pickles_send(msg)
    cdef _pickles_send(self, tuple msg):
        if self._send_lock:
            self._send_lock.acquire()
        try:
            self._socket.sendall(pickle.dumps(msg))
        finally:
            if self._send_lock:
                self._send_lock.release()

    #####################################################
    cdef int _strings_run(self):
        cdef bytes data
        cdef tuple req, args
        cdef dict kwargs
        cdef int msg_id=0
        cdef int result=0
        data = self._socket.recv(METHOD_STRINGS_SIZE)
        if not data:
            logging.debug('Client disconnected')
            result=-1
            return result
        req=data[0:1],data[1:9],data[9:METHOD_STRINGS_SIZE]
        (msg_id, method, args, kwargs) = self._strings_parse_request(req)
        try:
            ret = method(*args,**kwargs)
        except Exception, e:
            logging.exception('An error has occurred')
            self._strings_send_error(str(e), msg_id)
            result=0
        else:
            self._strings_send_result(ret, msg_id)
            result=0
        return result
    cdef tuple _strings_parse_request(self, tuple req):
        if (len(req) != 3 or int(req[0]) != MSGPACKRPC_REQUEST):
            raise RPCProtocolError('Invalid protocol')
        cdef tuple args=()
        cdef dict kwargs={}
        cdef int msg_id=0
        msg_id=int(req[1].lstrip())
        method_name=req[2].lstrip()
        if method_name.startswith('_'):
            raise MethodNotFoundError('Method not callow: %s', method_name)
        if not hasattr(self, method_name):
            raise MethodNotFoundError('Method not found: %s', method_name)
        method = getattr(self, method_name)
        if not hasattr(method, '__call__'):
            raise MethodNotFoundError('Method is not callable: %s', method_name)
        return (msg_id, method, args, kwargs)
    cdef _strings_send_result(self, object result, int msg_id):
        msg = (MSGPACKRPC_RESPONSE, msg_id,'', result)
        self._strings_send(msg)
    cdef _strings_send_error(self, str error, int msg_id):
        msg = (MSGPACKRPC_RESPONSE, msg_id, error, '')
        self._strings_send(msg)
    cdef _strings_send(self, tuple msg):
        if self._send_lock:
            self._send_lock.acquire()
        try:
            if hasattr(msg[3],'read'):
                self._socket.sendall('%1d%8d%21s'%(msg[0],msg[1],msg[2])+msg[3].read())
            else:
                self._socket.sendall('%1d%8d%21s'%(msg[0],msg[1],msg[2])+msg[3])
        finally:
            if self._send_lock:
                self._send_lock.release()

    #####################################################
    cdef int _urihttp_run(self):
        cdef bytes data
        cdef tuple req, args
        cdef dict kwargs
        cdef int msg_id=0
        cdef int result=0
        data = self._socket.recv(METHOD_URIHTTP_SIZE)
        if not data:
            logging.debug('Client disconnected')
            result=-1
            return result
        req=decode_urihttp(url=data)
        (msg_id, method, args, kwargs) = self._urihttp_parse_request(req)
        try:
            ret = method(*args,**kwargs)
        except Exception, e:
            logging.exception('An error has occurred')
            self._urihttp_send_error(str(e), msg_id)
            result=0
        else:
            self._urihttp_send_result(ret, msg_id)
            result=0
        return result
    cdef tuple _urihttp_parse_request(self, tuple req):
        if len(req) != 3:
            raise RPCProtocolError('Invalid protocol')
        cdef tuple args=()
        cdef dict kwargs={}
        cdef int msg_id=0
        method_name=req[0]
        args=req[1]
        kwargs=req[2]
        if method_name.startswith('_'):
            raise MethodNotFoundError('Method not callow: %s', method_name)
        if not hasattr(self, method_name):
            raise MethodNotFoundError('Method not found: %s', method_name)
        method = getattr(self, method_name)
        if not hasattr(method, '__call__'):
            raise MethodNotFoundError('Method is not callable: %s', method_name)
        if kwargs.has_key('msgsysid'):
            msg_id=int(kwargs.get('msgsysid'))
            del kwargs['msgsysid']
        return (msg_id, method, args, kwargs)
    cdef _urihttp_send_result(self, object result, int msg_id):
        msg = (MSGPACKRPC_RESPONSE, msg_id,'', result)
        self._urihttp_send(msg)
    cdef _urihttp_send_error(self, str error, int msg_id):
        msg = (MSGPACKRPC_RESPONSE, msg_id, error, '')
        self._urihttp_send(msg)
    cdef _urihttp_send(self, tuple msg):
        if self._send_lock:
            self._send_lock.acquire()
        try:
            if hasattr(msg[3],'read'):
                self._socket.sendall('%1d%8d%21s'%(msg[0],msg[1],msg[2])+msg[3].read())
            else:
                self._socket.sendall('%1d%8d%21s'%(msg[0],msg[1],msg[2])+msg[3])
        finally:
            if self._send_lock:
                self._send_lock.release()

    #####################################################












