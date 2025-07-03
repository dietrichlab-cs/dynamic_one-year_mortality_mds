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

MODEL_PARAMS = snakemake.params[2]

def train_gbm(feature_matrix, output_file):
    X_train, y_train = feature_matrix.drop(columns=['label', 'time_to_event', 'leuko_ed', 'hb_ed']), feature_matrix['label']

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


def train_and_classify(feature_matrix_csv, output_file):
    feature_matrix = pd.read_csv(feature_matrix_csv, dtype={"Unnamed: 0": str})
    feature_matrix.set_index("Unnamed: 0", inplace=True)
    print("Model training on unfiltered dataset")
    print(f"Patients: {feature_matrix.index.str.split('.').str[0].nunique()}")
    print(f"Samples: {feature_matrix.shape[0]}")
    for column in feature_matrix.columns:
        if feature_matrix[column].dtype == bool:
            feature_matrix[column] = feature_matrix[column].astype(int)
    train_gbm(feature_matrix, output_file)


train_and_classify(snakemake.input[0], snakemake.output[0])