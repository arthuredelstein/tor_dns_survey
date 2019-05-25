import stem.control
import socks
import sys
import time
import datetime
import json
import urllib2

guard = "F6740DEABFD5F62612FA025A5079EA72846B1F67"
controller = stem.control.Controller.from_port(port = 9051)
controller.authenticate("bilboBaggins789")
#controller.set_conf("CircuitStreamTimeout", "10")
exit_results = {}

def record_exit_result(fingerprint, address, result, delta):
    if not exit_results.has_key(address):
        exit_results[address] = {}
    if not exit_results[address].has_key(fingerprint):
        exit_results[address][fingerprint] = []
    dateString = str(datetime.datetime.now())
    exit_results[address][fingerprint].append((result, dateString, delta))

def get_exit_fingerprints():
    relays = list(controller.get_server_descriptors())
    exits = filter(lambda relay: relay.exit_policy.can_exit_to(port=80), relays)
    return map(lambda exit: exit.fingerprint, exits)

def test_http_request(address):
    """   Attempt to connect to example.com through tor proxy,
    using remote DNS."""
    s = socks.socksocket()
    s.settimeout(12)
    s.set_proxy(socks.SOCKS5, "localhost", 9050, True)
    s.connect((address, 80))
    s.sendall("GET / HTTP/1.1\nHost: www.example.com\n\n")
    return s.recv(4096)

def test_exit(fingerprint, address):
    start = time.time()
    try:
        controller.set_conf('CircuitBuildTimeout', '10')
        circuit_id = controller.new_circuit([guard, fingerprint], await_build = True)
    except:
        print "circuit build failed", sys.exc_info()
        delta = time.time() - start
        record_exit_result(fingerprint, address, str(sys.exc_info()[1]), delta)
        return
    def attach_stream(stream):
        delta = time.time() - start
        print delta, stream
        if stream.status == 'NEW' and stream.purpose == 'USER':
            controller.attach_stream(stream.id, circuit_id)
        if stream.status == 'DETACHED':
            record_exit_result(fingerprint, address, stream.reason, delta)
        if stream.status == 'SUCCEEDED':
            record_exit_result(fingerprint, address, stream.status, delta)
    try:
        controller.add_event_listener(attach_stream, stem.control.EventType.STREAM)
        controller.set_conf('__LeaveStreamsUnattached', '1')
        test_http_request(address)
    except:
        print "error: ", sys.exc_info()
        record_exit_result(fingerprint, address, str(sys.exc_info()[1]), time.time() - start)
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
                print "Repeat", j, "\n* Exit", i, "/", n, "(" + address + ") " + exits[i]
                test_exit(exits[i], address)

def write_json(filestem, data):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M");
    print(data)
    jsonStr = json.dumps(data)
    with open(filestem + "_" + now + ".json", "w") as f:
        f.write(jsonStr)
    with open(filestem + "_latest.json", "w") as f:
        f.write(jsonStr)

def relay_data():
    url = "https://onionoo.torproject.org/details?type=relay&flag=exit&fields=nickname,fingerprint,as_name,country_name,contact,platform,or_addresses,bandwidth_rate,exit_probability"
    response = urllib2.urlopen(url)
    data = json.load(response)
    return data["relays"]

def test_all_exits(addresses = ["example.com", "93.184.216.34"], repeats = 10):
    relays = relay_data()
    exits = get_exit_fingerprints()
    test_exits(exits, addresses, repeats)
    time.sleep(20)
    exit_results["_relays"] = relays
    print(exit_results)
    write_json("../all_exit_results/exit_results", exit_results);

#ExcludeExitNodes node,node,...
special_exits = [
#    "204DFD2A2C6A0DC1FA0EACB495218E0B661704FD", # HaveHeart
    "77131D7E2EC1CA9B8D737502256DA9103599CE51", # CriticalMass
    "1D3174338A1131A53E098443E76E1103CDED00DC", # criticalmass
#    "7BFB908A3AA5B491DA4CA72CCBEE0E1F2A939B55", # sofia
#    "09FA8B4F665AD65D2C2A49870F1AA3BA8811E449", # StanMarsh
#    "335746A6DEB684FABDF3FC5835C3898F05C5A5A8", # KyleBroflovksi
#    "B0279A521375F3CB2AE210BDBFC645FDD2E1973A", # chulak
#    "0593F5255316748247EBA76353A3A61F62224903", # novatorrelay
#    "696ABFA60C2FEA676FAF2DC2DA58A6D09FDBF78C", # HorstHanfblatt
#    "A9EBCBCB0EC01FEE8480C02214E4120B1C17ACF7", # labaudric
#    "D9F004C4664E9EE5AED955F91A67A5405531F33C"  # SophieScholl
#    "366E36894AF7ED5AEAE3D26FBEBD3FA29AA34FDD" #SentriesExit2
]

def test_special_exits():
    test_exits(special_exits, ["example.com", "93.184.216.34"], 1)
    relays = relay_data()
    exit_results["_relays"] = relays
    print(exit_results)
    write_json("../all_exit_results/exit_results", exit_results);


