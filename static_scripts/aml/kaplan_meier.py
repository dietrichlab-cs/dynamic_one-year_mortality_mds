from collections import defaultdict

import pandas as pd
from lifelines import KaplanMeierFitter
import kaplanmeier as km
from matplotlib import pyplot as plt

PLOT_DIR = "../../data/old_data/output/aml/dataset/plots"

# calculate Kaplan Meier curves for all five IPSS-R categories on the complete patient set
def kaplan_meier(kaplan_meier_input, plot):
    km_train = kaplan_meier_input
    kmf_estimators = {}
    for i in [0.0, 1.0, 2.0, 3.0, 4.0]:
        group_idx = (km_train["ipssr_group"] == i)
        kmf = KaplanMeierFitter()
        group_fit = kmf.fit(durations=km_train.loc[group_idx, "observation_time"], event_observed=km_train.loc[group_idx, "event_occurred"], label=i)
        kmf_estimators[i] = kmf

    time_event, censoring, y = km_train["observation_time"], km_train["event_occurred"], km_train["ipssr_group"]
    results = km.fit(time_event, censoring, y)

    conditional_prob = defaultdict(list)
    for cat in kmf_estimators.keys():
        for i in range(0,4500,50):
            conditional_prob[cat].append(kmf_estimators[cat].predict(i) / kmf_estimators[cat].predict(i + 365))


    #print(results)
    if plot:
        km.plot(results, title="", fontsize=14)
        fig = plt.gcf()
        ax_list = fig.axes
        axis = ax_list[0]
        axis.set_ylim(0,1)
        ax_list[1].set_visible(False)
        axis.set_xlim(0, 4500)
        axis.set_xlabel("days", fontsize=14)
        axis.set_ylabel("probability", fontsize=14)

        plt.tight_layout()
        plt.savefig(PLOT_DIR + "/kaplan_meier_aml.pdf")
        plt.clf()
    return kmf_estimators

if __name__ == "__main__":
    kaplan_meier_input = pd.read_csv("../../data/old_data/output/aml/dataset/kaplan_meier_input.csv", index_col="id")
    kaplan_meier(kaplan_meier_input, True)