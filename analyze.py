import json
import urllib2

def analyze_results(exit_results, address):
    exit_results_example = exit_results[address]
    print(exit_results_example)
    total_timeouts = 0
    total_successes = 0
    timeout_rates = {}
    for k in exit_results_example.keys():
        result = exit_results_example[k]
        status = map(lambda r: r[0], result)
        timeouts = len(filter(lambda s: s=="TIMEOUT", status))
        successes = len(filter(lambda s: s=="SUCCEEDED", status))
        total_timeouts += timeouts
        total_successes += successes
        if (timeouts + successes > 0):
            timeout_rates[k] = timeouts / float(timeouts + successes)
    rates_alone = timeout_rates.values()
    average = sum(rates_alone)/len(rates_alone)
    worst = len(filter(lambda x: x == 1.0, rates_alone))
    flaky = len(filter(lambda x: x < 1.0 and x > 0.0, rates_alone))
    best = len(filter(lambda x: x == 0.0, rates_alone))
    return timeout_rates, average, worst, flaky, best, total_timeouts, total_successes

def relay_data(fingerprint):
    url = "https://onionoo.torproject.org/details?limit=1&search=" + fingerprint
    response = urllib2.urlopen(url)
    data = json.load(response)
    return data["relays"][0]

def build_table(timeout_rates):
    headers = None
    s = u""
    for fingerprint in timeout_rates.keys():
        relay = relay_data(fingerprint)
        relay["timeout_rate_21394"] = timeout_rates[fingerprint]
        if headers == None:
            headers = map(str, sorted(relay.keys()))
            headers.remove("fingerprint")
            headers.remove("timeout_rate_21394")
            headers.insert(0, "fingerprint")
            headers.insert(1, "timeout_rate_21394")
            print headers
            s += "\t".join(headers) + "\n"
        s += "\t".join([unicode(relay.get(header, "")) for header in headers]) + "\n"
    with open("relay_timeout_table.txt", "w") as f:
        f.write(s.encode('ascii', 'ignore'))

def success_times_for_address(exit_results, address):
    times = []
    exit_results_address = exit_results[address]
    for fingerprint in exit_results_address.keys():
        for status, date, return_time in exit_results_address[fingerprint]:
            if status == "SUCCEEDED":
                times.append(return_time)
    return sorted(times)

def success_times(exit_results):
    results = {}
    for address in exit_results.keys():
        results[address] = success_times_for_address(exit_results, address)
    return results
