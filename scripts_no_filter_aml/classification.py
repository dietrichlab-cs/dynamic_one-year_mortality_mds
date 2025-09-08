import itertools
import os
from collections import defaultdict
from time import time

import kaplanmeier as km
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from lifelines import KaplanMeierFitter
from matplotlib import pyplot as plt
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.metrics import classification_report, roc_auc_score, log_loss, mean_squared_error, \
    average_precision_score
from sklearn.model_selection import train_test_split, GridSearchCV, KFold
from sklearn.utils import compute_sample_weight
from xgboost import XGBClassifier

from scripts_no_filter_aml.lib.helper import get_train_test,compute_tte_mse
from scripts_no_filter_aml.plotting.plotting_utils import plot_metric_by_length, plot_average_metric_by_length, \
    plot_feature_importance, plot_single_index_result_metric, plot_tte, plot_ratio_over_time, plot_brier, \
    precision_recall_plot, aur_roc_plot, plot_loss, classification_plot, calibration_plot, plot_kaplan_meier, \
    plot_average_metrics_by_length, plot_metrics_by_length

DATASET_DIR = "../data/publication_output/dataset_aml"
PLOT_DIR = DATASET_DIR + "/plots"
MAX_QUARTER = 32
MODEL_PARAMS = {"n_estimators": 1500, "learning_rate": 0.01, "max_depth": 3, "features_per_split": 80, "random_state": 123, "sample_weight": 2.3}
BASELINE_MODEL_PARAMS = {"n_estimators": 500, "learning_rate": 0.01, "max_depth": 3, "features_per_split": 80, "random_state": 123, "sample_weight": 2.3}


def classify(X_train, y_train, X_test, y_test, feature_matrix, model_params = MODEL_PARAMS, verbose=False, output_file=None):
    # Calculate colsample_bytree
    colsample_bytree = model_params["features_per_split"] / X_train.shape[1]
    colsample_bytree = min(1.0, colsample_bytree)  # Ensure it's within [0,1]

    clf = XGBClassifier(
        n_estimators=model_params["n_estimators"],
        learning_rate=model_params["learning_rate"],
        max_depth=model_params["max_depth"],
        colsample_bytree=colsample_bytree,
        random_state=model_params["random_state"],
        eval_metric='logloss')

    # drop the "last values" feature which was only used for testing the feature extraction
    #X_train.drop(columns=[c for c in X_train.columns if c not in ["quarters", "window_length", "gender", "age", "blasts", "cyto"]], inplace=True)
    #X_test.drop(columns=[c for c in X_test.columns if  c not in ["quarters", "window_length", "gender", "age", "blasts", "cyto"]],
    #             inplace=True)
    X_train.drop(columns=[c for c in X_train.columns if "_large_standard_deviation_" in c], inplace=True)
    X_test.drop(columns=[c for c in X_test.columns if  "_large_standard_deviation_" in c], inplace=True)
    # Feature selection
    selector = VarianceThreshold()
    selector.fit(X_train, y_train)
    selected_features = selector.get_support(1)
    X_train = X_train[X_train.columns[selected_features]]
    X_test = X_test[X_test.columns[selected_features]]

    weights = compute_sample_weight({0:1,1:MODEL_PARAMS["sample_weight"]}, y_train)
    clf.fit(
        X_train,
        y_train,
        sample_weight=weights,
        eval_set = [(X_train, y_train), (X_test, y_test)] if verbose else None,
        verbose=False
    )

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
    print(y_pred.shape, X_test.shape, test_data_df.shape)
    test_data_df = test_data_df.assign(predicted_class=y_pred)

    mse_tte = compute_tte_mse(test_data_df, y_test, y_prob[:,1])
    if verbose:
        print(classification_report(y_test, y_pred))
        aur_roc_plot(clf, X_test, y_test, PLOT_DIR)
        precision_recall_plot(y_test, y_prob, "pr_gbm", PLOT_DIR, True)

        plot_loss(clf, PLOT_DIR)

        prob_df = pd.DataFrame(y_prob, columns=["c_0", "c_1"], index=test_data_df.index)
        test_data_df = pd.concat([test_data_df, prob_df], axis=1)

        classification = test_data_df[['label', 'predicted_class', 'quarters', 'time_to_event', "c_0", "c_1"]]
        classification.to_csv(output_file)

        classification_plot(test_data_df, y_test, output_file, PLOT_DIR, MAX_QUARTER)
        calibration_plot(y_test, y_prob, PLOT_DIR)

    most_important_features = list(zip(clf.feature_names_in_, clf.feature_importances_))

    return [mse, mse_c0, mse_c1, auroc, auprc], y_prob, most_important_features, mse_tte



def grid_search(X_train, y_train, X_test, y_test):
    param_grid = [
        {'learning_rate': [.01, .02, .05, .1], 'n_estimators': [1000,1250,1500],
         'max_depth': [3,5,7]}
    ]
    # Calculate colsample_bytree
    colsample_bytree = 40 / X_train.shape[1]
    colsample_bytree = min(1.0, colsample_bytree)  # Ensure it's within [0,1]
    est = XGBClassifier(
        colsample_bytree=colsample_bytree,
        random_state=123,
        eval_metric='logloss')
    #est = GradientBoostingClassifier(n_estimators=1000)
    clf = GridSearchCV(est, param_grid, scoring='roc_auc_ovr', verbose=True)
    clf.fit(X_train, y_train)
    y_prob = clf.best_estimator_.predict_proba(X_test)
    auroc = roc_auc_score(y_test, y_prob[:, 1])
    print("ROC AUC scores (macro):\n{:.6f}".format(auroc))
    print(clf.best_params_)
    return clf.best_estimator_


def process_fold(i, split_idx, train_idx, test_idx, feature_matrix_constants, feature_matrix, lengths, folds):
    # Your existing code inside the loops goes here
    print("-----------NEW FOLD------------")

    X_train, y_train, X_test, y_test = get_train_test(feature_matrix, train_idx, test_idx, MAX_QUARTER)

    X_train_baseline = X_train[["quarters", "window_length", "gender", "age", "blasts", "cyto", "leuko_ed", "hb_ed", "easix"]]
    X_test_baseline = X_test[["quarters", "window_length", "gender", "age", "blasts", "cyto", "leuko_ed", "hb_ed", "easix"]]
    X_train.drop(columns=["easix", "pid", "leuko_ed", "hb_ed"], inplace=True)
    X_test.drop(columns=["easix", "pid", "leuko_ed", "hb_ed"], inplace=True)
    print(X_train.columns)
    print(X_train_baseline.columns)
    print("Total patients:", feature_matrix_constants.shape[0])
    print("Patient split. Train:", len(train_idx), "Test:", len(test_idx))
    print("Test samples:", X_test.shape[0])
    print("Test samples label distribution:")
    print(feature_matrix.loc[X_test.index, "label"].value_counts())
    prevalence = sum(y_test)/len(y_test)
    # IPSSR EVAL
    #print("IPSSR EVAL")
    #kmf_estimators = kaplan_meier(train_idx, kaplan_meier_input, False)
    #metrics_km, y_prob_ipssr, tte_cur = calculate_kaplan_meier_error(
    #    test_idx, X_test, y_test, kmf_estimators, feature_matrix
    #)

    # GBM EVAL
    print("GBM EVAL")
    metrics_gbm, y_prob, fp, tte_analysis = classify(
        X_train, y_train, X_test, y_test, feature_matrix, model_params=MODEL_PARAMS
    )

    metrics_baseline_gbm, y_prob_baseline, fp_baseline, tte_analysis_baseline = classify(
        X_train_baseline, y_train, X_test_baseline, y_test, feature_matrix, model_params=BASELINE_MODEL_PARAMS
    )

    # Collect length-based metrics
    length_metrics = {}
    length_metrics_list = []
    for l in lengths:
        sample_idx_length = feature_matrix.loc[X_test.index, 'quarters'] == l
        length_ratio_test_l = sum(y_test[sample_idx_length]) / len(y_test[sample_idx_length])
        if sum(y_test[sample_idx_length]) in [0, len(y_test[sample_idx_length])]:
            continue
        sample_auroc_gbm = roc_auc_score(y_test[sample_idx_length], y_prob[sample_idx_length, 1])
        sample_auroc_baseline = roc_auc_score(y_test[sample_idx_length], y_prob_baseline[sample_idx_length, 1])
        sample_auprc_gbm = average_precision_score(y_test[sample_idx_length], y_prob[sample_idx_length, 1])
        sample_auprc_baseline = average_precision_score(y_test[sample_idx_length], y_prob_baseline[sample_idx_length, 1])
        sample_mse_gbm = mean_squared_error(y_test[sample_idx_length], y_prob[sample_idx_length, 1])
        sample_mse_baseline = mean_squared_error(y_test[sample_idx_length], y_prob_baseline[sample_idx_length, 1])

        entry = {
            'length': l,
            'iteration': (i * folds + split_idx),  # Unique iteration index
            'ratio_test': length_ratio_test_l,
            'auroc_gbm': sample_auroc_gbm,
            'auroc_baseline': sample_auroc_baseline,
            'auprc_gbm': sample_auprc_gbm,
            'auprc_baseline': sample_auprc_baseline,
            'mse_gbm': sample_mse_gbm,
            'mse_baseline': sample_mse_baseline,
        }
        length_metrics_list.append(entry)


    length_metrics_df = pd.DataFrame(length_metrics_list)

    # Return all necessary results
    return {
        'metrics_baseline': metrics_baseline_gbm,
        'metrics_gbm': metrics_gbm,
        'y_prob_baseline': y_prob_baseline,
        'y_prob': y_prob,
        #'tte_cur': tte_cur,
        'tte_analysis': tte_analysis,
        'fp_gbm': fp,
        'fp_baseline': fp_baseline,
        'length_metrics_df': length_metrics_df,
        'prevalence': prevalence
    }


def cross_validation(feature_matrix, feature_matrix_constants, feature_importance_file):
    lengths = sorted(set(feature_matrix['quarters']))

    cross_val_iter = 10
    folds = 5

    results_gbm = np.empty((0,5))
    results_baseline = np.empty((0, 5))
    feature_importance = defaultdict(list)
    tte_gbm = np.empty((0, 4))

    # Define all the train and test sets for the cross validation split
    tasks = []
    for i in range(cross_val_iter):
        kf = KFold(n_splits=folds, shuffle=True, random_state=123 + 10*i)
        for split_idx, (train_index, test_index) in enumerate(kf.split(feature_matrix_constants)):
            train_idx, test_idx = feature_matrix_constants.iloc[train_index], feature_matrix_constants.iloc[test_index]
            tasks.append((i, split_idx, train_idx, test_idx))

    results = Parallel(n_jobs=8)(
        delayed(process_fold)(
            i, split_idx, train_idx, test_idx,
            feature_matrix_constants, feature_matrix, lengths, folds
        )
        for i, split_idx, train_idx, test_idx in tasks
    )
    avg_prevalence = 0
    for res in results:
        # Append metrics
        results_gbm = np.vstack((results_gbm, res['metrics_gbm']))
        results_baseline = np.vstack((results_baseline, res['metrics_baseline']))
        tte_gbm = np.vstack((tte_gbm, res['tte_analysis']))

        # Feature importance
        for f in res['fp_gbm']:
            feature_importance[f[0]].append(f[1])

        length_metrics_dfs = [res['length_metrics_df'] for res in results]
        length_metrics_full_df = pd.concat(length_metrics_dfs, ignore_index=True)
        avg_prevalence += res['prevalence']
    avg_prevalence /= len(results)
    meanlineprops = dict(marker='.', markeredgecolor='black', markersize= 4, markerfacecolor='black')
    medianprops = dict(linestyle=None, linewidth=1, color='black')
    colors = ['cornflowerblue', 'tomato']

    plot_tte(tte_gbm, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_ratio_over_time(length_metrics_full_df, lengths, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_brier(results_gbm, meanlineprops, medianprops, PLOT_DIR, "longitudinal")
    plot_brier(results_baseline, meanlineprops, medianprops, PLOT_DIR, "baseline")

    plot_single_index_result_metric(results_gbm, 3, "AUROC", meanlineprops, medianprops, PLOT_DIR, "longitudinal")
    plot_single_index_result_metric(results_baseline, 3, "AUROC", meanlineprops, medianprops, PLOT_DIR, "baseline")
    plot_single_index_result_metric(results_gbm, 4, "AUPRC", meanlineprops, medianprops, PLOT_DIR, "longitudinal", avg_prevalence)
    plot_single_index_result_metric(results_baseline, 4, "AUPRC", meanlineprops, medianprops, PLOT_DIR, "baseline", avg_prevalence)

    averaged_importance = {}
    sorted_importance = []
    for feature in feature_importance.keys():
        averaged_importance[feature] = np.mean(feature_importance[feature])
        sorted_importance.append((feature, np.mean(feature_importance[feature])))
    print(sorted_importance)
    sorted_importance.sort(key=lambda x: x[1], reverse=True)
    top_20 = sorted_importance[:20]
    plot_feature_importance(feature_importance, top_20, meanlineprops, medianprops, PLOT_DIR)
    with open(feature_importance_file, "w+") as f_file:
       for feature in averaged_importance.keys():
           f_file.write("%s, %.5f\n" % (feature, averaged_importance[feature]))

    plot_metric_by_length(length_metrics_full_df, "auroc", "AUROC score", ["gbm" ,"baseline"], lengths, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_metric_by_length(length_metrics_full_df, "auprc", "AUPRC score", ["gbm" ,"baseline"], lengths, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_metric_by_length(length_metrics_full_df, "mse", "Brier score", ["gbm" ,"baseline"], lengths, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_average_metric_by_length(length_metrics_full_df, "auroc", "AUROC score", ["gbm" ,"baseline"], lengths, colors, PLOT_DIR)
    plot_average_metric_by_length(length_metrics_full_df, "auprc", "AUPRC score", ["gbm", "baseline"], lengths, colors, PLOT_DIR)
    plot_average_metric_by_length(length_metrics_full_df, "mse", "Brier score", ["gbm", "baseline"], lengths, colors, PLOT_DIR)
    plot_average_metrics_by_length(length_metrics_full_df, ["gbm", "baseline"], lengths, colors, PLOT_DIR)
    plot_metrics_by_length(length_metrics_full_df, ["gbm", "baseline"], lengths, colors, PLOT_DIR)

    plt.close("all")


def train_and_classify(feature_matrix_csv, feature_matrix_constants_csv, km_easix, classification_output, feature_output):
    feature_matrix = pd.read_csv(feature_matrix_csv, dtype={"Unnamed: 0": str})
    easix_data = pd.read_csv(km_easix, dtype={"cis_id": str})
    easix_data["cis_id"] = easix_data["cis_id"].str.split(".").str[0]
    easix_data.set_index("cis_id", inplace=True)
    feature_matrix["pid"] = feature_matrix["Unnamed: 0"].str.split(".").str[0]
    feature_matrix = feature_matrix.merge(easix_data[["easix"]], left_on="pid", right_index=True, how="left")
    feature_matrix.set_index("Unnamed: 0", inplace=True)
    feature_matrix_constants = pd.read_csv(feature_matrix_constants_csv, dtype={"Unnamed: 0": str})
    feature_matrix_constants.set_index("Unnamed: 0", inplace=True)
    feature_matrix_constants.sort_index(inplace=True)
    for column in feature_matrix.columns:
        if feature_matrix[column].dtype == bool:
            feature_matrix[column] = feature_matrix[column].astype(int)
    class_counts = feature_matrix['label'].value_counts()
    print("Sample label distribution")
    print(class_counts)
    start = time()
    cross_validation(feature_matrix, feature_matrix_constants, feature_output)
    end = time()
    print("Execution time cv", (end-start))

os.makedirs(DATASET_DIR + "/plots", exist_ok=True)
train_and_classify(DATASET_DIR + "/survival_feature_matrix.csv",
        DATASET_DIR + "/survival_constant_only_feature_matrix.csv",
        DATASET_DIR + "/kaplan_meier_input_easix.csv", DATASET_DIR + "/classification.csv",
        DATASET_DIR + "/feature_importance.csv")
