"""Write the Mininet commands for a batch of two-flow trials.

Usage:
    python3 gen_trials.py <prefix> <algo0> <algo1> <first> <last> > batch.txt
Then, at the mininet> prompt:
    source batch.txt

Example (E3, Reno, trials 2-5):
    python3 gen_trials.py e3_d40_reno reno reno 2 5 > e3_d40_reno.txt

Each trial is the handout's commands: one ss recorder per sender, then both
iperf3 flows, then a 10 s wait so the recorders finish.
"""

import sys

# Same commands as handout with blanks to fill in
RECORDER = ("{host} timeout 65 sh -c 'while :; do date +%s.%N; "
            "ss -tin dst {ip}:5201; sleep 0.01; done' > {name}_ss.txt &")
FLOW = "{host} iperf3 -c {ip} -C {algo} -t 60 -i 0.5 -J --logfile {name}.json"

def trial_commands(prefix, algo0, algo1, trial):
    """Return the command lines for one two-flow trial."""
    name0 = f'{prefix}_t{trial}_snd0'
    name1 = f'{prefix}_t{trial}_snd1'
    return [
        RECORDER.format(host='snd0', ip='10.0.0.101', name=name0),
        RECORDER.format(host='snd1', ip='10.0.0.102', name=name1),
        FLOW.format(host='snd1', ip='10.0.0.102', algo=algo1, name=name1) + ' &',
        FLOW.format(host='snd0', ip='10.0.0.101', algo=algo0, name=name0),
        'sh sleep 10',
    ]

def main():
    prefix, algo0, algo1, first, last = sys.argv[1:6]
    for trial in range(int(first), int(last) + 1):
        for line in trial_commands(prefix, algo0, algo1, trial):
            print(line)

if __name__ == '__main__':
    main()
