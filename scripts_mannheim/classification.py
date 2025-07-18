import os

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score, log_loss, mean_squared_error, average_precision_score

from scripts_mannheim.lib.helper import compute_tte_mse
from scripts_mannheim.plotting.plotting_utils import precision_recall_plot, aur_roc_plot, \
    classification_plot, calibration_plot

MAX_QUARTER = 32
DATASET_DIR = "../data/publication_output/d_mannheim"
PLOT_DIR = DATASET_DIR + "/plot"


def classify(pretrained_model, X_test, y_test, feature_matrix, verbose=False):
    # Load the pretrained model
    clf = joblib.load(pretrained_model)
    # Drop potential easix scores
    X_test = X_test.drop(columns=['easix'], errors='ignore')
    # Retrieve feature names from the pretrained model
    feature_names = clf.get_booster().feature_names
    # Filter X_test based on the feature names
    # Assuming X_test is a pandas DataFrame
    X_test = X_test[feature_names]
    print("X_test", X_test.shape)
    y_prob = clf.predict_proba(X_test)
    y_pred = clf.predict(X_test)

    mse = mean_squared_error(y_test, y_prob[:,1])
    loss = log_loss(y_test, y_prob[:,1])
    auroc = roc_auc_score(y_test, y_prob[:, 1])
    mse_c0 = mean_squared_error(y_test[y_test == 0], y_prob[y_test == 0, 1])
    mse_c1 = mean_squared_error(y_test[y_test == 1], y_prob[y_test == 1, 1])
    auprc, _ = precision_recall_plot(y_test, y_prob, "pr_gbm", PLOT_DIR)
    report = classification_report(y_test, y_pred, output_dict=True)

    print("MSE: ", mse)
    print("MSE class 0", mse_c0)
    print("MSE class 1", mse_c1)
    print("AUPRC:", auprc)
    print("Log loss:", loss)
    print("AUROC:\n{:.6f}".format(auroc))
    print(classification_report(y_test, y_pred))

    test_data_df = feature_matrix.loc[X_test.index]
    test_data_df = test_data_df.assign(predicted_class=y_pred)

    mse_tte = compute_tte_mse(test_data_df, y_test, y_prob[:,1])
    if verbose:
        print(classification_report(y_test, y_pred))
        aur_roc_plot(clf, X_test, y_test, PLOT_DIR)
        precision_recall_plot(y_test, y_prob, "pr_gbm", PLOT_DIR, True)

        prob_df = pd.DataFrame(y_prob, columns=["c_0", "c_1"], index=test_data_df.index)
        test_data_df = pd.concat([test_data_df, prob_df], axis=1)
        prob_df.to_csv("../data/publication_output/d_mannheim/probs_longitudinal.csv")

        classification_plot(test_data_df, y_test, "_gbm", PLOT_DIR, MAX_QUARTER)
        calibration_plot(y_test, y_prob, PLOT_DIR, "calibration")
    return [mse, mse_c0, mse_c1, auroc, auprc], y_prob, mse_tte


def classify_baseline(pretrained_model, X_test, y_test, feature_matrix, verbose=False):
    # Load the pretrained model
    clf = joblib.load(pretrained_model)
    # Retrieve feature names from the pretrained model
    feature_names = clf.get_booster().feature_names
    # Filter X_test based on the feature names
    # Assuming X_test is a pandas DataFrame
    X_test = X_test[feature_names]
    print("X_test", X_test.shape)
    y_prob = clf.predict_proba(X_test)
    y_pred = clf.predict(X_test)

    mse = mean_squared_error(y_test, y_prob[:,1])
    loss = log_loss(y_test, y_prob[:,1])
    auroc = roc_auc_score(y_test, y_prob[:, 1])
    mse_c0 = mean_squared_error(y_test[y_test == 0], y_prob[y_test == 0, 1])
    mse_c1 = mean_squared_error(y_test[y_test == 1], y_prob[y_test == 1, 1])
    auprc, _ = precision_recall_plot(y_test, y_prob, "pr_gbm", PLOT_DIR)
    report = classification_report(y_test, y_pred, output_dict=True)

    print("MSE: ", mse)
    print("MSE class 0", mse_c0)
    print("MSE class 1", mse_c1)
    print("AUPRC:", auprc)
    print("Log loss:", loss)
    print("AUROC:\n{:.6f}".format(auroc))
    print(classification_report(y_test, y_pred))

    test_data_df = feature_matrix.loc[X_test.index]
    test_data_df = test_data_df.assign(predicted_class=y_pred)

    mse_tte = compute_tte_mse(test_data_df, y_test, y_prob[:,1])
    if verbose:
        print(classification_report(y_test, y_pred))
        aur_roc_plot(clf, X_test, y_test, PLOT_DIR, "auroc_baseline_gbm")
        precision_recall_plot(y_test, y_prob, "pr_baseline_gbm", PLOT_DIR, True)

        prob_df = pd.DataFrame(y_prob, columns=["c_0", "c_1"], index=test_data_df.index)
        test_data_df = pd.concat([test_data_df, prob_df], axis=1)
        prob_df.to_csv("../data/publication_output/d_mannheim/probs_baseline.csv")

        classification_plot(test_data_df, y_test, "_baseline_gbm", PLOT_DIR, MAX_QUARTER)
        calibration_plot(y_test, y_prob, PLOT_DIR, "calibration_baseline")
    return [mse, mse_c0, mse_c1, auroc, auprc], y_prob, mse_tte

def train_and_classify(pretrained_model, pretrained_model_baseline, feature_matrix_test_csv, metric_output_file):
    df_test = pd.read_csv(feature_matrix_test_csv, dtype={"Unnamed: 0": str})
    df_test.set_index("Unnamed: 0", inplace=True)
    df_test["easix"] = np.nan
    for column in df_test.columns:
        if df_test[column].dtype == bool:
            df_test[column] = df_test[column].astype(int)
    sample_idx_test = [idx for idx in df_test.index if int(idx.split(".")[1]) <= MAX_QUARTER]
    X_test, y_test = df_test.drop(columns=['label', 'time_to_event']).loc[sample_idx_test], \
        df_test['label'].loc[sample_idx_test]

    print("Test samples:", X_test.shape[0])
    print("Test samples label distribution:")
    print(df_test.loc[X_test.index, "label"].value_counts())

    metric_output = open(metric_output_file, "w")

    metric_output.write(f"Samples: {X_test.shape[0]}\n")
    metric_output.write(f"Value counts: {df_test.loc[X_test.index, 'label'].value_counts()}\n")
    metric_output.write(f"Patient: {df_test.index.str.split('.').str[0].nunique()}")

    gbm_metrics, gbm_y_prob, gbm_mse_tte = classify(pretrained_model, X_test, y_test, df_test, True)
    gbm_baseline_metrics, gbm_baseline_y_prob, gbm_baseline_mse_tte = classify_baseline(pretrained_model_baseline, X_test, y_test, df_test, True)

    metric_output.write(f"Overall metrics: ([mse, mse_c0, mse_c1, auroc, auprc], mse_tte)\n")
    metric_output.write(f"GBM metrics:{gbm_metrics}, {gbm_mse_tte}\n")
    metric_output.write(f"GBM_baseline metrics:{gbm_baseline_metrics}, {gbm_baseline_mse_tte}\n")
    metric_output.write("=" * 50 + "\n")
    metric_output.write("Lengthwise (AUROC, AUPRC, MSE):\n")

    lengths = sorted(set(df_test['quarters']))
    for l in lengths:
        sample_idx_length = df_test.loc[X_test.index, 'quarters'] == l
        length_ratio_test_l = sum(y_test[sample_idx_length]) / len(y_test[sample_idx_length])
        if sum(y_test[sample_idx_length]) in [0, len(y_test[sample_idx_length])]:
            continue
        sample_auroc_gbm = roc_auc_score(y_test[sample_idx_length], gbm_y_prob[sample_idx_length, 1])
        sample_auroc_gbm_baseline = roc_auc_score(y_test[sample_idx_length], gbm_baseline_y_prob[sample_idx_length, 1])
        sample_auprc_gbm = average_precision_score(y_test[sample_idx_length], gbm_y_prob[sample_idx_length, 1])
        sample_auprc_gbm_baseline = average_precision_score(y_test[sample_idx_length], gbm_baseline_y_prob[sample_idx_length, 1])
        sample_mse_gbm = mean_squared_error(y_test[sample_idx_length], gbm_y_prob[sample_idx_length, 1])
        sample_mse_gbm_baseline = mean_squared_error(y_test[sample_idx_length], gbm_baseline_y_prob[sample_idx_length, 1])
        metric_output.write(f"Length: {l} quarters\n")
        metric_output.write(f"Ratio: {length_ratio_test_l}\n")
        metric_output.write(f"GBM metrics: {sample_auroc_gbm}, {sample_auprc_gbm}, {sample_mse_gbm}\n")
        metric_output.write(f"GBM_baseline metrics: {sample_auroc_gbm_baseline}, {sample_auprc_gbm_baseline}, {sample_mse_gbm_baseline}\n")


os.makedirs(PLOT_DIR, exist_ok=True)
train_and_classify("../data/publication_output/dataset/models/gbm_all_patients.joblib",
        "../data/publication_output/dataset/models/gbm_all_patients_easix_baseline.joblib",
        DATASET_DIR + "/survival_feature_matrix.csv", DATASET_DIR + "/metrics_full_model.txt")
