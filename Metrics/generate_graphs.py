"""
Generate evaluation graphs for the report.
Saves PNG files into the Report directory.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Report")

# ── Graph 1: Metric Comparison Bar Chart ────────────────────────────────────

def plot_metric_comparison():
    metrics = ['Precision@5', 'Recall@20', 'mAP', 'Success Rate']
    clip_values = [0.1944, 0.9790, 0.9177, 0.958]
    hybrid_values = [0.1719, 0.9289, 0.7169, 0.808]

    x = np.arange(len(metrics))
    width = 0.32

    fig, ax = plt.subplots(figsize=(9, 5.5))

    bars1 = ax.bar(x - width/2, clip_values, width, label='CLIP + Local Re-ranking',
                   color='#2563EB', edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x + width/2, hybrid_values, width, label='Deep Hybrid (BM25 + CLIP)',
                   color='#F97316', edgecolor='white', linewidth=0.8)

    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}' if height < 1 else f'{height:.1%}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}' if height < 1 else f'{height:.1%}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title('Search Quality: CLIP vs. Deep Hybrid (Flickr8k, 499 Queries)',
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(REPORT_DIR, "metric_comparison.png")
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


# ── Graph 2: Search Latency Comparison ──────────────────────────────────────

def plot_latency_comparison():
    operations = [
        'CLIP Text\nEncoding',
        'Qdrant ANN\n(top-20)',
        'Mode 1\n(Global CLIP)',
        'Mode 2\n(Re-rank)',
        'Mode 3\n(Deep Hybrid)'
    ]
    min_vals = [45, 2, 55, 210, 180]
    avg_vals = [52, 3, 65, 290, 240]
    max_vals = [78, 8, 95, 480, 390]

    x = np.arange(len(operations))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5.5))

    ax.bar(x - width, min_vals, width, label='Min (ms)',
           color='#10B981', edgecolor='white', linewidth=0.8)
    ax.bar(x, avg_vals, width, label='Avg (ms)',
           color='#2563EB', edgecolor='white', linewidth=0.8)
    ax.bar(x + width, max_vals, width, label='Max (ms)',
           color='#EF4444', edgecolor='white', linewidth=0.8)

    # Add value labels on avg bars
    for i, v in enumerate(avg_vals):
        ax.annotate(f'{v}ms', xy=(x[i], v), xytext=(0, 5),
                    textcoords="offset points", ha='center', va='bottom',
                    fontsize=9, fontweight='bold')

    ax.set_ylabel('Response Time (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Search Response Latency by Mode (CPU-only, 100 Images)',
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(operations, fontsize=10)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(REPORT_DIR, "latency_comparison.png")
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    plot_metric_comparison()
    plot_latency_comparison()
    print("All graphs generated!")
