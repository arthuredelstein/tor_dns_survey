import asyncio
import datetime
import json
import os
import time
import txtorcon
import urllib.request

from twisted.internet import asyncioreactor
from twisted.internet.defer import ensureDeferred, Deferred
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.task import react
from twisted.web.client import readBody

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
    socks = config.socks_endpoint(reactor, port = 9050)
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

async def test_exits(reactor, state, socks, guard, exits, repeats):
    exit_results = {}
    n = len(exits)
    for i in range(repeats):
        j = 0
        for exit_node in exits:
            j = j + 1
            result = ""
            delta = -1
            try:
                delta = await time_two_hop(reactor, state, socks, guard, exit_node)
                result = "SUCCEEDED"
            except Exception as err:
                result = str(err)
            record_result(exit_results, exit_node.id_hex, "example.com", result, delta)
            print('%d/%d: %d/%d' % (i, repeats, j, n), exit_node.id_hex, ":", exit_results["example.com"][exit_node.id_hex])
    return exit_results

async def test_relays(reactor, state, socks, relays, exit_node, repeats):
    relay_results = {}
    n = len(relays)
    for i in range(repeats):
        j = 0
        for relay in relays:
            j = j + 1
            result = ""
            delta = -1
            try:
                delta = await time_two_hop(reactor, state, socks, relay, exit_node)
                result = "SUCCEEDED"
            except Exception as err:
                result = str(err)
            record_result(relay_results, relay.id_hex, "example.com", result, delta)
            print('%d/%d: %d/%d' % (i, repeats, j, n), relay.id_hex, ":", relay_results["example.com"][relay.id_hex])
    return relay_results

async def _main(reactor):
    [tor, config, state, socks] = await launch_tor(reactor)
    config.CircuitBuildTimeout = 10
    config.SocksTimeout = 10
    config.CircuitStreamTimeout = 10
    config.save()
    routers = state.all_routers

    guard1 = state.routers_by_hash["$F6740DEABFD5F62612FA025A5079EA72846B1F67"]
    exits = list(filter(lambda router: "exit" in router.flags, routers))
    exit_results = await test_exits(reactor, state, socks, guard1, exits, 10)
    exit_results["_relays"] = relay_data(True)
    write_json("../all_exit_results/exit_results", exit_results)

    exit_node = state.routers_by_hash["$1AE949967F82BBE7534A3D6BA77A7EBE1CED4369"]
    relays = list(filter(lambda router: "exit" not in router.flags, routers))
    relay_results = await test_relays(reactor, state, socks, relays, exit_node, 4)
    relay_results["_relays"] = relay_data(False)
    write_json("../all_relay_results/relay_results", relay_results)

def main():
    return react(
        lambda reactor: ensureDeferred(
            _main(reactor)
        )
    )

if __name__ == '__main__':
    main()
