import asyncio
import datetime
import json
import os
import time
import txtorcon
import urllib.request

from twisted.internet import asyncioreactor
from twisted.internet.defer import ensureDeferred
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.task import react

def write_json(filestem, data):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M");
    print(data)
    jsonStr = json.dumps(data)
    with open(filestem + "_" + now + ".json", "w") as f:
        f.write(jsonStr)
    with open(filestem + "_latest.json", "w") as f:
        f.write(jsonStr)

def relay_data(exits):
    url = "https://onionoo.torproject.org/details?type=relay&fields=nickname,fingerprint,as_name,country_name,contact,platform,or_addresses,bandwidth_rate,exit_probability"
    if exits:
        url += "&flag=exit"
    req = urllib.request.Request(url)
    response = urllib.request.urlopen(req).read()
    data = json.loads(response.decode('utf-8'))
    return data["relays"]

async def launch_tor(reactor):
    control_ep = TCP4ClientEndpoint(reactor, "localhost", 9051)
    tor = await txtorcon.connect(reactor, control_ep, password_function = lambda: "bilboBaggins789")
    #tor = await txtorcon.launch(reactor, progress_updates=print, data_directory="./tor_data")
    config = await tor.get_config()
    state = await tor.create_state()
    socks = await config.create_socks_endpoint(reactor, "9050")
    print("Connected to tor {}".format(tor.version))
    return [tor, config, state, socks]

async def time_two_hop(reactor, state, socks, guard, exit_node):
    circuit = await state.build_circuit(routers = [guard, exit_node], using_guards = False)
    #circuit = await state.build_circuit(routers = [exit_node], using_guards = False)
    await circuit.when_built()
    # print("Circuit", circuit.id, circuit.path)
    t_start = time.time()
    agent = circuit.web_agent(reactor, socks)
    resp = await agent.request(b'HEAD', b"http://example.com")
    t_stop = time.time()
    return t_stop - t_start

def record_result(results, fingerprint, address, result, delta):
    if address not in results:
        results[address] = {}
    if fingerprint not in results[address]:
        results[address][fingerprint] = []
    dateString = str(datetime.datetime.now())
    results[address][fingerprint].append((result, dateString, delta))

async def test_relays(reactor, state, socks, relays, exits, repeats):
    results = {}
    nr = len(relays)
    ne = len(exits)
    n = nr * ne
    for i in range(repeats):
        j = 0
        for relay in relays:
            for exit_node in exits:
                j = j + 1
                result = ""
                delta = -1
                try:
                    delta = await time_two_hop(reactor, state, socks, relay, exit_node)
                    result = "SUCCEEDED"
                except Exception as err:
                    result = str(err)
                relay_key = relay.id_hex if (nr > 1) else exit_node.id_hex
                record_result(results, relay_key, "example.com", result, delta)
                print('%d/%d: %d/%d' % (i+1, repeats, j, n),
                      relay.id_hex, "->", exit_node.id_hex, ":", results["example.com"][relay_key])
    return results

async def _main(reactor, fingerprint):
    [tor, config, state, socks] = await launch_tor(reactor)
    config.CircuitBuildTimeout = 10
    config.SocksTimeout = 10
    config.CircuitStreamTimeout = 10
    config.save()
    if fingerprint == None:
        routers = state.all_routers
    else:
        routers = [state.routers_by_hash[fingerprint]]

    guard1 = state.routers_by_hash["$CB4EBE9C475A60A5F2CDA92C83CE093BD945D940"]
    exits = list(filter(lambda router: "exit" in router.flags, routers))
    exit_results = await test_relays(reactor, state, socks, [guard1], exits, 10)
    exit_results["_relays"] = relay_data(True)
    write_json("../all_exit_results/exit_results", exit_results)

    exit_node = state.routers_by_hash["$7BD7B547676257EF147F5D5B7A5B15F840F4B579"]
    relays = list(filter(lambda router: "exit" not in router.flags, routers))
    relay_results = await test_relays(reactor, state, socks, relays, [exit_node], 3)
    relay_results["_relays"] = relay_data(False)
    write_json("../all_relay_results/relay_results", relay_results)

def main(fingerprint):
    return react(
        lambda reactor: ensureDeferred(
            _main(reactor, fingerprint)
        )
    )

if __name__ == '__main__':
    main(None)
