import json

def analyze_results(exit_results, address):
    exit_results_example = exit_results[address]
    timeout_rates = {}
    for k in exit_results_example.keys():
        result = exit_results_example[k]
        status = map(lambda r: r[0], result)
        timeouts = len(filter(lambda s: s=="TIMEOUT", status))
        successes = len(filter(lambda s: s=="SUCCEEDED", status))
        if (timeouts + successes > 0):
            timeout_rates[k] = timeouts / float(timeouts + successes)
    rates_alone = timeout_rates.values()
    average = sum(rates_alone)/len(rates_alone)
    worst = len(filter(lambda x: x == 1.0, rates_alone))
    flaky = len(filter(lambda x: x < 1.0 and x > 0.0, rates_alone))
    best = len(filter(lambda x: x == 0.0, rates_alone))
    return timeout_rates, average, worst, flaky, best
