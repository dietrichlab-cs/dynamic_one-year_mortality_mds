from collections import defaultdict
from pathlib import Path

import joblib
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test
from matplotlib import pyplot as plt

PLOT_DIR = "../../data/publication_output/dataset/plots"

def kaplan_meier(kaplan_meier_input):
    km_train = kaplan_meier_input
    print(km_train.shape)
    kmf_estimators = {}
    groups = [1, 2, 3]
    q_labels = {1: "Lower Quartile", 2: "Inner Quartiles (2&3)", 3: "Upper Quartile"}
    # Create Kaplan-Meier estimators for each group
    for i in groups:
        group_idx = (km_train["easix_quartile"] == i)
        kmf = KaplanMeierFitter()
        kmf.fit(
            durations=km_train.loc[group_idx, "lifetime"],
            event_observed=km_train.loc[group_idx, "event_occurred"],
            label=f'{q_labels[i]}'
        )
        kmf_estimators[i] = kmf

        # Plot survival curves
        kmf.plot_survival_function()
    joblib.dump(kmf_estimators, "../../data/publication_output/dataset/models/kmf_estimators_easix.joblib")
    plt.title("Kaplan-Meier Survival Curves")
    plt.xlabel("Time")
    plt.ylabel("Survival Probability")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOT_DIR + "/kaplan_meier_easix.pdf")
    plt.show()

    # Perform pairwise log-rank tests
    print("\nLog-Rank Test Results:")
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            group1 = groups[i]
            group2 = groups[j]
            results = logrank_test(
                km_train.loc[km_train["easix_quartile"] == group1, "lifetime"],
                km_train.loc[km_train["easix_quartile"] == group2, "lifetime"],
                event_observed_A=km_train.loc[km_train["easix_quartile"] == group1, "event_occurred"],
                event_observed_B=km_train.loc[km_train["easix_quartile"] == group2, "event_occurred"]
            )
            print(f"Quartile {group1} vs Quartile {group2}: p-value = {results.p_value:.4f}")

    conditional_prob = defaultdict(list)
    plt.clf()
    colors = ["tab:blue", "tab:orange", "tab:green"]
    for cat in kmf_estimators.keys():
        for i in range(0, 6000, 90):
            conditional_prob[cat].append(kmf_estimators[cat].predict(i+365) / kmf_estimators[cat].predict(i))
        plt.plot(list(range(0, 6000, 90)), conditional_prob[cat], '-', color=colors[int(cat)-1], label=q_labels[int(cat)])
    plt.legend(loc="lower right")
    plt.xlabel("$h$ [days]", fontsize=12)
    plt.ylabel("conditional probability", fontsize=12)
    plt.xlim(left=0)
    plt.tight_layout()
    plt.savefig(PLOT_DIR + "/kaplan_meier_cs_easix.pdf")
    plt.show()

    return kmf_estimators

if __name__ == "__main__":
    easix = pd.read_csv("../../data/publication_output/dataset/patient_data_filtered_easix.csv")
    easix.set_index("cis_id", inplace=True)
    easix['easix_quartile'] = pd.qcut(easix['easix'], q=4, labels=[1, 2, 3, 4])
    # Rename groups: Q1 → 1 (Lower), Q2 & Q3 → 2 (Middle), Q4 → 3 (Upper)
    quartile_mapping = {1: 1, 2: 2, 3: 2, 4: 3}
    easix['easix_quartile'] = easix['easix_quartile'].map(quartile_mapping)
    kaplan_meier_input = pd.DataFrame(columns=["cis_id", "easix", "easix_quartile", "lifetime", "event_occurred"])
    for patient in easix.index:
        if not Path(f"../../data/publication_output/dataset/labels/{patient}_labels.csv").exists():
            continue
        label = pd.read_csv(f"../../data/publication_output/dataset/labels/{patient}_labels.csv")
        if pd.isna(easix.loc[patient]["easix_quartile"]) or pd.isna(label.iloc[0]["lifetime"]):
            continue
        kaplan_meier_input.loc[patient] = [patient,  easix.loc[patient]["easix"], easix.loc[patient]["easix_quartile"], label.iloc[0]["lifetime"], 0 if label.iloc[0]["alive"] == 1 else 1]
    kaplan_meier_input.to_csv("../../data/publication_output/dataset/kaplan_meier_input_easix.csv", index=False)
    kaplan_meier(kaplan_meier_input)
