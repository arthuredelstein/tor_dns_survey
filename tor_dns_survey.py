import stem.control
import socks
import sys
import time
import datetime

guard = "F6740DEABFD5F62612FA025A5079EA72846B1F67"
controller = stem.control.Controller.from_port(port = 9051)

#exit_results = {}

def record_exit_result(fingerprint, address, result, delta):
    if not exit_results.has_key(address):
        exit_results[address] = {}
    if not exit_results[address].has_key(fingerprint):
        exit_results[address][fingerprint] = []
    dateString = str(datetime.datetime.now())
    exit_results[address][fingerprint].append((result, dateString, delta))

def get_exits():
    relays = list(controller.get_server_descriptors())
    return filter(lambda relay: relay.exit_policy.can_exit_to(port=80), relays)


def test_http_request(address):
    """Attempt to connect to example.com through tor proxy,
       using remote DNS."""
    s = socks.socksocket()
    s.settimeout(12)
    s.set_proxy(socks.SOCKS5, "localhost", 9050, True)
    s.connect((address, 80))
    s.sendall("GET / HTTP/1.1\nHost: www.example.com\n\n")
    return s.recv(4096)

def test_exit(exit, address):
    start = time.time()
    try:
        controller.set_conf('CircuitBuildTimeout', '10')
        circuit_id = controller.new_circuit([guard, exit.fingerprint], await_build = True)
    except:
        print "circuit build failed."
        return
    def attach_stream(stream):
        delta = time.time() - start
        print delta, stream
        if stream.status == 'NEW' and stream.purpose == 'USER':
            controller.attach_stream(stream.id, circuit_id)
        if stream.status == 'DETACHED':
            record_exit_result(exit.fingerprint, address, stream.reason, delta)
        if stream.status == 'SUCCEEDED':
            record_exit_result(exit.fingerprint, address, stream.status, delta)
    try:
        controller.add_event_listener(attach_stream, stem.control.EventType.STREAM)
        controller.set_conf('__LeaveStreamsUnattached', '1')
        test_http_request(address)
    except:
        print "error: ", sys.exc_info()[0]
    finally:
        controller.remove_event_listener(attach_stream)
        controller.reset_conf('__LeaveStreamsUnattached')
        controller.reset_conf('CircuitBuildTimeout')

def test_exits(exits, addresses, repeats):
    n = len(exits)
    print n, "exits to test."
    for j in range(repeats):
        for address in addresses:
            for i in range(n):
                print "\n* Exit", i, "/", n, "repeat", j
                test_exit(exits[i], address)

def test_all_exits(addresses, repeats = 1):
    exits = get_exits()
    test_exits(exits, addresses, repeats)

#ExcludeExitNodes node,node,...
