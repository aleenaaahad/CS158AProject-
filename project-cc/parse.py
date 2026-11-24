"""Parse the raw files from each trial into numbers to analyze."""

import re
import json

def read_ss_samples(path):
    """Split an ss recorder file into samples.

    Returns a list of (timestamp, details) pairs. details is a list of the indented
    lines in that sample, one per TCP connection.
    """

    samples = []
    with open(path) as f:
        for line in f:
            if line[0].isdigit():
                # Timestamp line, ex: 1795325394.170260339: starts a new sample
                samples.append((float(line), []))
            elif line.startswith('\t') and samples:
                # Indented line: one connection's TCP details
                samples[-1][1].append(line.strip())

    return samples

def find_number(pattern, line, convert):
    """Search line for pattern and return the captured number, or None if missing."""
    match = re.search(pattern, line)
    if match:
        return convert(match.group(1))
    return None

def parse_details(line):
    """Pull the fields we need out of one connection's details line."""
    return {
            'algo': line.split()[0],
            'cwnd': find_number(r'\bcwnd:(\d+)', line, int),
            'rtt': find_number(r'\brtt:([\d.]+)/', line, float),
            'mss': find_number(r'\bmss:(\d+)', line, int),
            'bytes_acked': find_number(r'\bbytes_acked:(\d+)', line, int),
    }

def parse_ss(path):
    """Return the data connection's samples from an ss recorder file.

    Each row is a dict with t (seconds since the first sample in the file)
    plus the fields from parse_details. Samples that don't have both iperf3
    connections (before the flow starts or after it ends) are skipped.
    """

    samples = read_ss_samples(path)
    if not samples:
        return []

    t0 = samples[0][0] 
    rows = []
    for timestamp, details in samples:
        if len(details) < 2:
            continue
        conns = [parse_details(line) for line in details]

        data = max(conns, key=lambda c: c['bytes_acked'] or 0)
        data['t'] = timestamp - t0
        rows.append(data)

    return rows

def parse_iperf(path, skip=5):
    """Read an iperf JSON log.

    Returns a dict with:
      intervals:   list of (start time in s, throughput in Mbps), one per interval
      retransmits: total retransmitted packets for the flow
      steady_mbps: average throughput over intervals starting at or after `skip` s
    """
    
    with open(path) as f:
        report = json.load(f)

    intervals = [(i['sum']['start'], i['sum']['bits_per_second'] / 1e6)
                 for i in report['intervals']]
    late = [mbps for start, mbps in intervals if start >= skip]

    return {
        'intervals': intervals,
        'retransmits': report['end']['sum_sent']['retransmits'],
        'steady_mbps': sum(late) / len(late),
    }
