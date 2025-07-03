from itertools import combinations

import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingClassifier
import pandas as pd
from sklearn.inspection import PartialDependenceDisplay

SMALL_SIZE = 10
MEDIUM_SIZE = 12
BIGGER_SIZE = 14

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

# compute partial dependence for a pre-defined feature set and the complete patient set
def partial_dependence():
    clf = GradientBoostingClassifier(n_estimators=1000, learning_rate=0.01, max_depth=3, max_features=40, random_state=123)
    df = pd.read_csv("../../data/old_data/output/survival_dynamic/dataset/survival_feature_matrix.csv")
    df.set_index("Unnamed: 0", inplace=True)
    X = df.drop(columns=["ipssr_age", "time_to_event", "label"])
    X.drop(columns=[c for c in X.columns if "last_values" in c], inplace=True)
    y = df["label"]
    clf.fit(X,y)



    print(clf.feature_names_in_[[262, 263, 261, 257, 245, 113, 198, 248, 122, 141]])
    features = ["age", "THROMB310_variation_coefficient", "blasts", "THROMB310_minimum", "HB304_mean", "cyto", "LEUKO302_maximum", "HK305_last_three_points_slope", "THROMB310_quantile_{'q': 0.1}", "HB304_quantile_{'q': 0.75}" ]
    label_dict = {
        "LEUKO302_median": "leukocytes median",
        "LEUKO302_last_three_points_slope": "leukocytes last three points slope",
        "HK305_mean": "hematocrit mean",
        "LEUKO302_variance": "leukocytes varianc",
        "HB304_quantile_{'q': 0.1}": "hb 10% quantile",
        "LEUKO302_standard_deviation": "leukocytes standard deviation",
        "HB304_median": "hb median",
        "LEUKO302_quantile_{'q': 0.25}": "leukocytes 25% quantile",
        "HB304_minimum": "HB minimum",
        "HB304_quantile_{'q': 0.5}": "hb 50% quantile",
        "THROMB310_quantile_{'q': 0.25}": "platelet 25% quantile",
        "HK305_last_three_points_slope": "hematocrit last three points slope",
        "HB304_quantile_{'q': 0.75}": "hb 75% quantile",
        "THROMB310_quantile_{'q': 0.1}": "platelet 10% quantile",
        "LEUKO302_maximum": "leukocytes maximum",
        "cyto": "IPSS karyotype category",
        "HB304_mean": "hb mean",
        "THROMB310_minimum": "platelet minimum",
        "blasts": "bone-marrow blasts",
        "THROMB310_variation_coefficient": "platelet variation coefficient",
        "age": "age"
    }
    PartialDependenceDisplay.from_estimator(clf, X, features, n_cols=5)
    #PartialDependenceDisplay.from_estimator(clf, X, features, n_cols=5, kind="both", centered=True)
    f = plt.gcf()
    for i, ax in enumerate(f.get_axes()):
        param = ax.get_xlabel()
        if param == "": continue
        ax.set_xlabel(label_dict[param])
        if label_dict[param] == "bone-marrow blasts": ax.set_xlim(0,25)
        if i % 5 == 1: ax.set_ylabel("partial dependence")

    f.set_figwidth(15)
    f.set_figheight(10)
    plt.tight_layout()
    plt.savefig("../../data/output/survival_dynamic/dataset/plots/pd.pdf")




if __name__ == "__main__":
    partial_dependence()