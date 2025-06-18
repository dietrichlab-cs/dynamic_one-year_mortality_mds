from lifelines import KaplanMeierFitter
import kaplanmeier as km
import matplotlib.pyplot as plt
from joblib import dump
import os
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.utils import compute_sample_weight
from xgboost import XGBClassifier

MODEL_PARAMS = snakemake.params[0]

def train_gbm(feature_matrix, output_file):
    X_train, y_train = feature_matrix.drop(columns=['label', 'time_to_event']), feature_matrix['label']

    # Calculate colsample_bytree
    colsample_bytree = MODEL_PARAMS["features_per_split"] / X_train.shape[1]
    colsample_bytree = min(1.0, colsample_bytree)  # Ensure it's within [0,1]

    clf = XGBClassifier(
        n_estimators=MODEL_PARAMS["n_estimators"],
        learning_rate=MODEL_PARAMS["learning_rate"],
        max_depth=MODEL_PARAMS["max_depth"],
        colsample_bytree=colsample_bytree,
        random_state=MODEL_PARAMS["random_state"],
        eval_metric='logloss')
    # droping the age adjusted ipss-r values
    if "ipssr_age" in X_train.columns: X_train = X_train.drop(columns=['ipssr_age'])
    # Feature selection
    selector = VarianceThreshold()
    selector.fit(X_train, y_train)
    selected_features = selector.get_support(1)
    X_train = X_train[X_train.columns[selected_features]]
    weights = compute_sample_weight({0:1,1:MODEL_PARAMS["sample_weight"]}, y_train)
    clf.fit(X_train, y_train, sample_weight=weights)
    dump(clf, output_file)


def train_and_classify(feature_matrix_csv, km_easix, baseline_all_patients_model):
    feature_matrix = pd.read_csv(feature_matrix_csv, dtype={"Unnamed: 0": str})
    easix_data = pd.read_csv(km_easix, dtype={"cis_id": str})
    easix_data["cis_id"] = easix_data["cis_id"].str.split(".").str[0]
    easix_data.set_index("cis_id", inplace=True)
    feature_matrix["pid"] = feature_matrix["Unnamed: 0"].str.split(".").str[0]
    feature_matrix = feature_matrix.merge(easix_data[["easix"]], left_on="pid", right_index=True, how="left")
    debug = feature_matrix[~feature_matrix["easix"].isna()]
    print("Trained models with easix as parameter")
    print(f"Patients reduced {debug['pid'].nunique()}")
    print(f"Patients all {feature_matrix['pid'].nunique()}")
    print(f"Samples all: {feature_matrix.shape[0]}")

    feature_matrix.drop(columns=["pid"], inplace=True)
    feature_matrix.set_index("Unnamed: 0", inplace=True)
    for column in feature_matrix.columns:
        if feature_matrix[column].dtype == bool:
            feature_matrix[column] = feature_matrix[column].astype(int)
    baseline_feature_matrix = feature_matrix[["quarters", "window_length", "time_to_event", "label", "gender", "age", "blasts", "cyto", "leuko_ed", "hb_ed", "easix"]]
    train_gbm(baseline_feature_matrix, baseline_all_patients_model)


train_and_classify(snakemake.input[0], snakemake.input[1], snakemake.output[0])
