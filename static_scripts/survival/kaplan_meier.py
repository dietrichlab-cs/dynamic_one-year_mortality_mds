from collections import defaultdict

import numpy as np
import pandas as pd
import pylab as pl
from lifelines import KaplanMeierFitter
import kaplanmeier as km
from matplotlib import pyplot as plt

PLOT_DIR = "../../data/publication_output/dataset/plots"

# train Kaplan Meier estimator for each IPSS-R category based on the given patient set and plot all Kaplan-Meier curves using lifelines
def kaplan_meier(kaplan_meier_input):
    km_train = kaplan_meier_input
    kmf_estimators = {}
    for i in [0.0, 1.0, 2.0, 3.0, 4.0]:
        group_idx = (km_train["ipssr_group"] == i)
        kmf = KaplanMeierFitter()
        group_fit = kmf.fit(durations=km_train.loc[group_idx, "lifetime"],
                            event_observed=km_train.loc[group_idx, "event_occurred"], label=i)
        kmf_estimators[i] = kmf

    time_event, censoring, y = km_train["lifetime"], km_train["event_occurred"], km_train["ipssr_group"]
    results = km.fit(time_event, censoring, y)
    km.plot(results, title="", fontsize=14)
    fig = plt.gcf()
    ax_list = fig.axes
    axis = ax_list[0]
    ax_list[1].set_visible(False)
    axis.set_xlim(0, 4500)
    axis.set_xlabel("days", fontsize=14)
    axis.set_ylabel("probability", fontsize=14)
    plt.tight_layout()
    plt.savefig(PLOT_DIR + "/kaplan_meier.pdf")

    conditional_prob = defaultdict(list)
    plt.clf()
    colors = ["tab:red", "tab:blue", "tab:green", "tab:purple", "tab:orange"]
    cat_names = ["very low", "low", "intermediate", "high", "very high"]
    for cat in kmf_estimators.keys():
        for i in range(0, 2720, 90):
            conditional_prob[cat].append(kmf_estimators[cat].predict(i+365) / kmf_estimators[cat].predict(i))
        plt.plot(list(range(0, 2720, 90)), conditional_prob[cat], '-', color=colors[int(cat)], label=str(cat) + " " + cat_names[int(cat)])
    plt.legend(loc="lower right")
    plt.xlabel("$h$ [days]", fontsize=12)
    plt.ylabel("conditional probability", fontsize=12)
    plt.xlim(left=0)
    plt.tight_layout()
    plt.savefig(PLOT_DIR + "/kaplan_meier_cs.pdf")
    plt.show()

    return kmf_estimators

if __name__ == "__main__":
    kaplan_meier_input = pd.read_csv("../../data/publication_output/dataset/kaplan_meier_input.csv", index_col="id")
    kaplan_meier(kaplan_meier_input)

    # plot snapshot counts depending on IPSS-R category and snapshot length
    df = pd.read_csv("../../data/publication_output/dataset/survival_feature_matrix.csv", index_col="Unnamed: 0")
    plt.clf()
    colors = ["tab:red", "tab:blue", "tab:green", "tab:purple", "tab:orange"]
    cat_names = ["very low", "low", "intermediate", "high", "very high"]
    for i in [0.0, 1.0, 2.0, 3.0, 4.0]:
        group_df = df[df["ipssr_age"] == i]
        group_counts = defaultdict(int)
        for j in range(1, 2720, 90):
            group_counts[j] = len(group_df[(group_df["window_length"] < j) & (group_df["window_length"] >= j-90)])
        plt.plot(np.array(range(len(group_counts.keys()))), list(group_counts.values()), '.-', color=colors[int(i)], label=str(i) + " " + cat_names[int(i)])
    plt.title("Snapshot counts for different $Q_i$ grouped by IPSS-R", fontsize=14)
    plt.ylabel("counts", fontsize=12)
    plt.xlabel("Snapshot length $Q_i$ [quarters]", fontsize=12)
    plt.xlim(left=1)
    plt.ylim(bottom=-0.01)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(PLOT_DIR + "/kaplan_meier_length.pdf")
    plt.show()

    # similar to above but just for snapshots with negative or 0 label
    plt.clf()
    for i in [0.0, 1.0, 2.0, 3.0, 4.0]:
        group_df = df[(df["ipssr_age"] == i) & (df["label"] == 0)]
        group_counts = defaultdict(int)
        for j in range(1, 2720, 90):
            group_counts[j] = len(group_df[(group_df["window_length"] < j) & (group_df["window_length"] >= j - 90)])
        plt.plot(np.array(range(len(group_counts.keys()))), list(group_counts.values()), '.-', color=colors[int(i)],
                 label=str(i) + " " + cat_names[int(i)])
    plt.title("Negative label counts for different $Q_i$ grouped by IPSS-R", fontsize=14)
    plt.ylabel("counts", fontsize=12)
    plt.xlabel("Snapshot length $Q_i$ [quarters]", fontsize=12)
    plt.xlim(left=1)
    plt.ylim(bottom=-0.01)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(PLOT_DIR + "/kaplan_meier_length_neg.pdf")
    plt.show()

    # similar to above but just for snapshots with positive or 1 label
    plt.clf()
    for i in [0.0, 1.0, 2.0, 3.0, 4.0]:
        group_df = df[(df["ipssr_age"] == i) & (df["label"] == 1)]
        group_counts = defaultdict(int)
        for j in range(1, 2720, 90):
            group_counts[j] = len(group_df[(group_df["window_length"] < j) & (group_df["window_length"] >= j - 90)])
        plt.plot(np.array(range(len(group_counts.keys()))), list(group_counts.values()), '.-', color=colors[int(i)],
                 label=str(i) + " " + cat_names[int(i)])
    plt.title("Positive label counts for different $Q_i$ grouped by IPSS-R", fontsize=14)
    plt.ylabel("counts", fontsize=12)
    plt.xlabel("Snapshot length $Q_i$ [quarters]", fontsize=12)
    plt.xlim(left=1)
    plt.ylim(bottom=-0.01)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(PLOT_DIR + "/kaplan_meier_length_pos.pdf")
    plt.show()