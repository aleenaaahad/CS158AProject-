"""Analyze the five E1 trials per algorithm and regenerate E1 figures.

Run from project-cc with: python3 analyze_e1.py
The optional paths allow checking plots before copying this script to a repo.
"""

import argparse
from pathlib import Path
import statistics as st
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


ALGOS = ('reno', 'cubic', 'bbr')
TRIALS = range(1, 6)


def mean_std(values):
    return st.mean(values), st.stdev(values)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--project', type=Path, default=Path(__file__).resolve().parent)
    cli.add_argument('--out', type=Path, default=None)
    args = cli.parse_args()
    project = args.project.resolve()
    out = args.out.resolve() if args.out else project / 'plots'
    sys.path.insert(0, str(project))
    from parse import parse_iperf, parse_ss

    summaries = {}
    traces = {}
    for algo in ALGOS:
        rates, retrans = [], []
        for trial in TRIALS:
            stem = project / 'data' / 'e1' / f'e1_b1_{algo}_t{trial}'
            flow = parse_iperf(str(stem) + '.json')
            if len(flow['intervals']) != 120:
                raise ValueError(f'{stem}: expected 120 throughput intervals')
            rows = [row for row in parse_ss(str(stem) + '_ss.txt')
                    if row['algo'] == algo and row['cwnd'] is not None]
            if not rows:
                raise ValueError(f'{stem}: no {algo} cwnd samples')
            rates.append(flow['steady_mbps'])
            retrans.append(flow['retransmits'])
            if trial == 1:
                traces[algo] = rows
        summaries[algo] = (mean_std(rates), mean_std(retrans))

    out.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    for ax, algo in zip(axes, ALGOS):
        rows = traces[algo]
        ax.plot([row['t'] for row in rows], [row['cwnd'] for row in rows],
                linewidth=0.8, color={'reno': '#2876b8', 'cubic': '#e1812c',
                                      'bbr': '#23916b'}[algo])
        ax.axhline(83, linestyle=':', linewidth=1, color='gray',
                   label='BDP ≈ 83 packets')
        ax.set_ylabel('cwnd (packets)')
        ax.set_title(f'{algo.upper()} — trial 1')
        ax.legend(loc='upper right')
    axes[-1].set_xlabel('Time since first recorder sample (s)')
    axes[-1].set_xlim(0, 65)
    fig.suptitle('E1: congestion window over time (50 Mbps, 20 ms RTT, B = 1 × BDP)')
    fig.tight_layout()
    fig.savefig(out / 'e1_cwnd.png', dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    means = [summaries[a][0][0] for a in ALGOS]
    errors = [summaries[a][0][1] for a in ALGOS]
    bars = ax.bar([a.upper() for a in ALGOS], means, yerr=errors, capsize=5,
                  color=['#2876b8', '#e1812c', '#23916b'])
    ax.set_ylabel('Steady-state throughput (Mbps)')
    ax.set_xlabel('Congestion control algorithm')
    ax.set_ylim(0, 52)
    ax.set_title('E1: throughput, mean ± standard deviation over 5 trials')
    for bar, mean in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, mean + 1.2,
                f'{mean:.1f}', ha='center', va='bottom')
    fig.tight_layout()
    fig.savefig(out / 'e1_throughput.png', dpi=160)
    plt.close(fig)

    print('E1: mean ± standard deviation over 5 trials')
    for algo in ALGOS:
        (rate, rate_sd), (retr, retr_sd) = summaries[algo]
        print(f'{algo.upper():5s} throughput {rate:.2f} ± {rate_sd:.2f} Mbps; '
              f'retransmissions {retr:.1f} ± {retr_sd:.1f}')
    print(f'Saved {out / "e1_cwnd.png"} and {out / "e1_throughput.png"}')


if __name__ == '__main__':
    main()
