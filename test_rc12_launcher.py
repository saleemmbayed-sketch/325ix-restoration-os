#!/usr/bin/env python3
"""Focused regression check for RC12 port selection and launcher lifecycle helpers."""
import socket
from launch_rc12_trial import choose_port,port_available

def main():
    occupied=socket.socket();occupied.bind(('127.0.0.1',0));occupied.listen(1)
    try:
        preferred=occupied.getsockname()[1]
        assert not port_available(preferred)
        selected=choose_port(preferred)
        assert selected!=preferred and selected>preferred and port_available(selected)
    finally:occupied.close()
    assert port_available(preferred)
    print('PASS: occupied port is skipped and becomes reusable after release')

if __name__=='__main__':main()
