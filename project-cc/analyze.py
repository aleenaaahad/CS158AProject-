"""Analyze E3 and E4: print mean ± std tables and save plots.

Usage (run from project-cc/):
    python3 analyze.py

Reads the trial files in data/e3 and data/e4 (named as in the handout)
and writes PNG plots to plots/.
"""

import os
import statistics as st

import matplotlib
matplotlib.use('Agg')          # save PNG files; no window needed
import matplotlib.pyplot as plt

from parse import parse_iperf, parse_ss

TRIALS = range(1, 6)           # t1 ... t5
SKIP = 5                       # seconds of slow start to skip (handout)
WINDOW = 10                    # Jain window: 10 intervals x 0.5 s = 5 s
INTERVAL = 0.5                 # iperf3 report interval (-i 0.5), seconds
E3_ALGOS = ['reno', 'cubic', 'bbr']
E4_BUFS = ['0.1', '1', '4']
PLOTS = 'plots'


# ---------- small helpers ----------

def mean_std(values):
    """Return (mean, standard deviation) of a list of numbers."""
    return st.mean(values), st.stdev(values)


def jain(xs):
    """Jain's fairness index: 1 = equal shares, 1/n = one flow takes all."""
    return sum(xs) ** 2 / (len(xs) * sum(x * x for x in xs))


def avg_rtt(path):
    """Average smoothed RTT (ms) after slow start, from an ss recorder file."""
    rtts = [row['rtt'] for row in parse_ss(path) if row['t'] >= SKIP]
    return sum(rtts) / len(rtts)


def steady(path):
    """Steady-state throughput (Mbps) from an iperf3 JSON file."""
    return parse_iperf(path)['steady_mbps']


def jain_over_time(json0, json1):
    """Jain's index over a sliding 5 s window of both flows' intervals.

    Returns (times, values), where each time is the end of its window.
    """
    a = parse_iperf(json0)['intervals']
    b = parse_iperf(json1)['intervals']
    n = min(len(a), len(b))
    times, values = [], []
    for end in range(WINDOW, n + 1):
        x0 = sum(mbps for _, mbps in a[end - WINDOW:end]) / WINDOW
        x1 = sum(mbps for _, mbps in b[end - WINDOW:end]) / WINDOW
        times.append(a[end - 1][0] + INTERVAL)
        values.append(jain([x0, x1]))
    return times, values


def save(fig, name):
    """Save a figure to plots/<name> and close it."""
    os.makedirs(PLOTS, exist_ok=True)
    path = os.path.join(PLOTS, name)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f'  saved {path}')


# ---------- E3: two flows, same algorithm, different RTTs ----------

def e3_prefix(algo, t):
    return f'data/e3/e3_d40_{algo}_t{t}'


def e3_trial(algo, t):
    """Return (x0/x1, RTT1/RTT0) for one E3 trial."""
    p = e3_prefix(algo, t)
    thr_ratio = steady(p + '_snd0.json') / steady(p + '_snd1.json')
    rtt_ratio = avg_rtt(p + '_snd1_ss.txt') / avg_rtt(p + '_snd0_ss.txt')
    return thr_ratio, rtt_ratio


def analyze_e3():
    print('E3: throughput ratio vs RTT ratio (mean ± std, 5 trials)')
    stats = {}
    for algo in E3_ALGOS:
        trials = [e3_trial(algo, t) for t in TRIALS]
        thr = mean_std([thr for thr, _ in trials])
        rtt = mean_std([rtt for _, rtt in trials])
        stats[algo] = (thr, rtt)
        print(f'  {algo:5s}  x0/x1 = {thr[0]:.2f} ± {thr[1]:.2f}   '
              f'RTT1/RTT0 = {rtt[0]:.2f} ± {rtt[1]:.2f}   '
              f'(RTT1/RTT0)^2 = {rtt[0] ** 2:.2f}')
    plot_e3_ratios(stats)
    plot_e3_jain()


def plot_e3_ratios(stats):
    """Bar chart: throughput ratio next to RTT ratio for each algorithm."""
    xs = list(range(len(E3_ALGOS)))
    w = 0.35
    thr = [stats[a][0] for a in E3_ALGOS]
    rtt = [stats[a][1] for a in E3_ALGOS]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar([x - w / 2 for x in xs], [m for m, _ in thr], w,
           yerr=[s for _, s in thr], capsize=4,
           label='Throughput ratio x0 / x1')
    ax.bar([x + w / 2 for x in xs], [m for m, _ in rtt], w,
           yerr=[s for _, s in rtt], capsize=4,
           label='Measured RTT ratio RTT1 / RTT0')
    ax.axhline(1, color='gray', linestyle=':', linewidth=1)   # equal share
    ax.set_xticks(xs)
    ax.set_xticklabels([a.upper() for a in E3_ALGOS])
    ax.set_xlabel('Congestion control algorithm')
    ax.set_ylabel('Ratio (unitless)')
    ax.set_title('E3: RTT unfairness, 20 ms vs 80 ms flow (mean ± std, 5 trials)')
    ax.legend()
    save(fig, 'e3_ratios.png')


def plot_e3_jain():
    """Jain's index vs time, averaged over 5 trials, with a ±std band."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for algo in E3_ALGOS:
        runs = [jain_over_time(e3_prefix(algo, t) + '_snd0.json',
                               e3_prefix(algo, t) + '_snd1.json')
                for t in TRIALS]
        n = min(len(values) for _, values in runs)
        times = runs[0][0][:n]
        per_time = list(zip(*(values[:n] for _, values in runs)))
        means = [st.mean(v) for v in per_time]
        stds = [st.stdev(v) for v in per_time]
        ax.plot(times, means, label=algo.upper())
        ax.fill_between(times,
                        [m - s for m, s in zip(means, stds)],
                        [m + s for m, s in zip(means, stds)],
                        alpha=0.2)
    ax.set_ylim(0.5, 1.02)
    ax.set_xlabel('Time (s), end of 5 s window')
    ax.set_ylabel("Jain's fairness index J (unitless)")
    ax.set_title("E3: Jain's index over time (mean ± std band, 5 trials)")
    ax.legend()
    save(fig, 'e3_jain.png')


# ---------- E4: BBR (snd0) vs CUBIC (snd1) across buffer sizes ----------

def analyze_e4():
    print('E4: BBR (snd0) vs CUBIC (snd1) (mean ± std, 5 trials)')
    shares, jains = [], []
    for buf in E4_BUFS:
        share_list, jain_list = [], []
        for t in TRIALS:
            p = f'data/e4/e4_b{buf}_bbrcubic_t{t}'
            x0, x1 = steady(p + '_snd0.json'), steady(p + '_snd1.json')
            share_list.append(x0 / (x0 + x1))
            jain_list.append(jain([x0, x1]))
        shares.append(mean_std(share_list))
        jains.append(mean_std(jain_list))
        print(f'  buf {buf:3s}  BBR share = {shares[-1][0]:.3f} ± {shares[-1][1]:.3f}   '
              f'J = {jains[-1][0]:.3f} ± {jains[-1][1]:.3f}')
    plot_e4(shares, jains)


def plot_e4(shares, jains):
    """Left: each flow's share per buffer size. Right: Jain's index."""
    xs = list(range(len(E4_BUFS)))
    labels = [f'{b} x BDP' for b in E4_BUFS]
    w = 0.35
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.5))

    bbr = [m for m, _ in shares]
    err = [s for _, s in shares]
    left.bar([x - w / 2 for x in xs], bbr, w, yerr=err, capsize=4, label='BBR (snd0)')
    left.bar([x + w / 2 for x in xs], [1 - m for m in bbr], w, yerr=err, capsize=4,
             label='CUBIC (snd1)')
    left.axhline(0.5, color='gray', linestyle=':', linewidth=1)   # fair share
    left.set_xticks(xs)
    left.set_xticklabels(labels)
    left.set_ylim(0, 1)
    left.set_xlabel('Bottleneck buffer size B')
    left.set_ylabel('Throughput share x_i / (x0 + x1)')
    left.set_title('E4: throughput share (mean ± std, 5 trials)')
    left.legend()

    right.bar(xs, [m for m, _ in jains], 0.5, yerr=[s for _, s in jains], capsize=4)
    right.set_xticks(xs)
    right.set_xticklabels(labels)
    right.set_ylim(0.5, 1.02)
    right.set_xlabel('Bottleneck buffer size B')
    right.set_ylabel("Jain's fairness index J (unitless)")
    right.set_title("E4: Jain's index (mean ± std, 5 trials)")
    save(fig, 'e4_share_jain.png')


def main():
    analyze_e3()
    analyze_e4()


if __name__ == '__main__':
    main()
