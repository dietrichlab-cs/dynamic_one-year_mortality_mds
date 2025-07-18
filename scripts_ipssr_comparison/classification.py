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

from scripts_ipssr_comparison.lib.helper import get_train_test,compute_tte_mse
from scripts_ipssr_comparison.plotting.plotting_utils import plot_metric_by_length, plot_average_metric_by_length, \
    plot_feature_importance, plot_single_index_result_metric, plot_tte, plot_ratio_over_time, plot_brier, \
    precision_recall_plot, aur_roc_plot, plot_loss, classification_plot, calibration_plot, plot_kaplan_meier

PLOT_DIR = snakemake.params[0]
MAX_QUARTER = snakemake.params[1]
MODEL_PARAMS = snakemake.params[2]


def classify(X_train, y_train, X_test, y_test, feature_matrix, verbose=False, output_file=None):
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
    X_train = X_train.drop(columns=['ipssr_age'])
    X_test = X_test.drop(columns=['ipssr_age'])

    # drop the "last values" feature which was only used for testing the feature extraction
    #X_train.drop(columns=[c for c in X_train.columns if c not in ["quarters", "window_length", "gender", "age", "blasts", "cyto"]], inplace=True)
    #X_test.drop(columns=[c for c in X_test.columns if  c not in ["quarters", "window_length", "gender", "age", "blasts", "cyto"]],
    #             inplace=True)

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
        {'learning_rate': [.01, .02, .05, .1],
         'max_depth': [4,6], "min_samples_leaf": [3,5,9,17], "max_features": [1.0,0.3,0.1]}
    ]
    est = GradientBoostingClassifier(n_estimators=1000)
    clf = GridSearchCV(est, param_grid, n_jobs=8, scoring='roc_auc_ovr', verbose=True)
    clf.fit(X_train, y_train)
    y_prob = clf.best_estimator_.predict_proba(X_test)
    auroc = roc_auc_score(y_test, y_prob[:, 1])
    print("ROC AUC scores (macro):\n{:.6f}".format(auroc))
    print(clf.best_params_)
    return clf.best_estimator_


def process_fold(i, split_idx, train_idx, test_idx, feature_matrix_constants, feature_matrix, kaplan_meier_input, lengths, folds):
    # Your existing code inside the loops goes here
    print("-----------NEW FOLD------------")

    X_train, y_train, X_test, y_test = get_train_test(feature_matrix, train_idx, test_idx, MAX_QUARTER)
    print("Total patients:", feature_matrix_constants.shape[0])
    print("Patient split. Train:", len(train_idx), "Test:", len(test_idx))
    print("Test samples:", X_test.shape[0])
    print("Test samples label distribution:")
    print(feature_matrix.loc[X_test.index, "label"].value_counts())

    # IPSSR EVAL
    print("IPSSR EVAL")
    kmf_estimators = kaplan_meier(train_idx, kaplan_meier_input, False)
    metrics_km, y_prob_ipssr, tte_cur = calculate_kaplan_meier_error(
        test_idx, X_test, y_test, kmf_estimators, feature_matrix
    )

    # GBM EVAL
    print("GBM EVAL")
    metrics_gbm, y_prob, fp, tte_analysis = classify(
        X_train, y_train, X_test, y_test, feature_matrix
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
        sample_auroc_ipssr = roc_auc_score(y_test[sample_idx_length], y_prob_ipssr[sample_idx_length])
        sample_auprc_gbm = average_precision_score(y_test[sample_idx_length], y_prob[sample_idx_length, 1])
        sample_auprc_ipssr = average_precision_score(y_test[sample_idx_length], y_prob_ipssr[sample_idx_length])
        sample_mse_gbm = mean_squared_error(y_test[sample_idx_length], y_prob[sample_idx_length, 1])
        sample_mse_ipssr = mean_squared_error(y_test[sample_idx_length], y_prob_ipssr[sample_idx_length])

        entry = {
            'length': l,
            'iteration': (i * folds + split_idx),  # Unique iteration index
            'ratio_test': length_ratio_test_l,
            'auroc_gbm': sample_auroc_gbm,
            'auroc_ipssr': sample_auroc_ipssr,
            'auprc_gbm': sample_auprc_gbm,
            'auprc_ipssr': sample_auprc_ipssr,
            'mse_gbm': sample_mse_gbm,
            'mse_ipssr': sample_mse_ipssr,
        }
        length_metrics_list.append(entry)


    length_metrics_df = pd.DataFrame(length_metrics_list)

    # Return all necessary results
    return {
        'metrics_km': metrics_km,
        'metrics_gbm': metrics_gbm,
        'y_prob_ipssr': y_prob_ipssr,
        'y_prob': y_prob,
        'tte_cur': tte_cur,
        'tte_analysis': tte_analysis,
        'fp': fp,
        'length_metrics_df': length_metrics_df,
        'prevalence': sum(y_test)/len(y_test)
    }


def cross_validation(feature_matrix, feature_matrix_constants, kaplan_meier_input, feature_importance_file):
    lengths = sorted(set(feature_matrix['quarters']))

    cross_val_iter = 10
    folds = 5

    results_km = np.empty((0,5))
    results_gbm = np.empty((0,5))
    feature_importance = defaultdict(list)
    tte_gbm, tte_ipssr = np.empty((0, 4)), np.empty((0, 4))
    execution_times = []

    # Define all the train and test sets for the cross validation split
    tasks = []
    for i in range(cross_val_iter):
        kf = KFold(n_splits=folds, shuffle=True, random_state=123 + 10*i)
        for split_idx, (train_index, test_index) in enumerate(kf.split(feature_matrix_constants)):
            train_idx, test_idx = feature_matrix_constants.iloc[train_index], feature_matrix_constants.iloc[test_index]
            tasks.append((i, split_idx, train_idx, test_idx))

    results = Parallel(n_jobs=-1)(
        delayed(process_fold)(
            i, split_idx, train_idx, test_idx,
            feature_matrix_constants, feature_matrix, kaplan_meier_input, lengths, folds
        )
        for i, split_idx, train_idx, test_idx in tasks
    )
    avg_prevalence = 0
    for res in results:
        # Append metrics
        results_km = np.vstack((results_km, res['metrics_km']))
        results_gbm = np.vstack((results_gbm, res['metrics_gbm']))

        tte_ipssr = np.vstack((tte_ipssr, res['tte_cur']))
        tte_gbm = np.vstack((tte_gbm, res['tte_analysis']))
        avg_prevalence += res['prevalence']
        # Feature importance
        for f in res['fp']:
            feature_importance[f[0]].append(f[1])

        length_metrics_dfs = [res['length_metrics_df'] for res in results]
        length_metrics_full_df = pd.concat(length_metrics_dfs, ignore_index=True)
    avg_prevalence /= len(results)
    meanlineprops = dict(marker='.', markeredgecolor='black', markersize= 4, markerfacecolor='black')
    medianprops = dict(linestyle=None, linewidth=1, color='black')
    colors = ['cornflowerblue', 'tomato']

    plot_tte(tte_gbm, tte_ipssr, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_ratio_over_time(length_metrics_full_df, lengths, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_brier(results_gbm, results_km, meanlineprops, medianprops, PLOT_DIR)

    plot_single_index_result_metric(results_gbm, results_km, 3, "AUROC", meanlineprops, medianprops, PLOT_DIR)
    plot_single_index_result_metric(results_gbm, results_km, 4, "AUPRC", meanlineprops, medianprops, PLOT_DIR, random_baseline=avg_prevalence)

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

    plot_metric_by_length(length_metrics_full_df, "auroc", "AUROC score", lengths, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_metric_by_length(length_metrics_full_df, "auprc", "AUPRC score", lengths, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_metric_by_length(length_metrics_full_df, "mse", "Brier score", lengths, meanlineprops, medianprops, colors, PLOT_DIR)
    plot_average_metric_by_length(length_metrics_full_df, "auroc", "AUROC score", lengths, colors, PLOT_DIR)
    plot_average_metric_by_length(length_metrics_full_df, "auprc", "AUPRC score", lengths, colors, PLOT_DIR)

    plt.close("all")


def kaplan_meier(X_train, kaplan_meier_input, plot):
    km_train = kaplan_meier_input.loc[X_train.index.astype(dtype=int)]
    kmf_estimators = {}
    for i in [0.0, 1.0, 2.0, 3.0, 4.0]:
        group_idx = (km_train["ipssr_group"] == i)
        kmf = KaplanMeierFitter()
        kmf.fit(durations=km_train.loc[group_idx, "lifetime"], event_observed=km_train.loc[group_idx, "event_occurred"], label=i)
        kmf_estimators[i] = kmf

    time_event, censoring, y = km_train["lifetime"], km_train["event_occurred"], km_train["ipssr_group"]
    results = km.fit(time_event, censoring, y)
    if plot:
        plot_kaplan_meier(km, results, PLOT_DIR)
    return kmf_estimators


def calculate_kaplan_meier_error(X_test_constant, X_test, y_test, kmf_estimators, feature_matrix = None):
    squared_errors, y_prob, y_prob_c0, y_prob_c1,y_pred = [], [], [], [],[]
    print("STARTING KAPLAN MEIER")
    for sample in X_test.index:
        true_label = y_test.loc[sample]
        ipssr_group = X_test_constant.loc[sample.split(".")[0], "ipssr_age"]
        prediction_point = X_test.loc[sample, "window_length"] + 365
        known_alive = X_test.loc[sample, "window_length"]
        survival_prob = kmf_estimators[ipssr_group].predict(prediction_point) / kmf_estimators[ipssr_group].predict(known_alive)
        y_prob.append(1- survival_prob)
        if true_label == 0: y_prob_c0.append(1 - survival_prob)
        else: y_prob_c1.append(1 - survival_prob)
        y_pred.append(1 if survival_prob < .5 else 0)

    auprc, _ = precision_recall_plot(y_test, y_prob, "pr_ipssr", PLOT_DIR)
    ll = log_loss(y_test, y_prob)
    mse = mean_squared_error(y_test, y_prob)
    mse_c0 = mean_squared_error(y_test[y_test == 0], y_prob_c0)
    mse_c1 = mean_squared_error(y_test[y_test == 1], y_prob_c1)
    auroc = roc_auc_score(y_test, y_prob)
    print([ll, mse, mse_c0, mse_c1, auroc])
    print("Log loss:", ll)
    print("MSE:", mse)
    print("MSE class 0:", mse_c0)
    print("MSE class 1:", mse_c1)
    print("AUROC:", auroc)
    y_prob = np.array(y_prob)
    mse_tte = None
    if feature_matrix is not None:
        X_test_full = feature_matrix.loc[X_test.index]
        mse_tte = compute_tte_mse(X_test_full, y_test, y_prob)
    return [mse, mse_c0, mse_c1, auroc, auprc], y_prob, mse_tte



def train_and_classify(feature_matrix_csv, feature_matrix_constants_csv, kaplan_meier_input_csv, classification_output, feature_output):
    feature_matrix = pd.read_csv(feature_matrix_csv, dtype={"Unnamed: 0": str})
    feature_matrix.set_index("Unnamed: 0", inplace=True)
    feature_matrix_constants = pd.read_csv(feature_matrix_constants_csv, dtype={"Unnamed: 0": str})
    feature_matrix_constants.set_index("Unnamed: 0", inplace=True)
    feature_matrix_constants.sort_index(inplace=True)
    for column in feature_matrix.columns:
        if feature_matrix[column].dtype == bool:
            feature_matrix[column] = feature_matrix[column].astype(int)

    kaplan_meier_input = pd.read_csv(kaplan_meier_input_csv, index_col="id")

    class_counts = feature_matrix['label'].value_counts()
    print("Sample label distribution")
    print(class_counts)
    X_train_constant, X_test_constant = train_test_split(feature_matrix_constants, train_size=0.80, shuffle=True, random_state=123)

    kmf_estimators = kaplan_meier(X_train_constant, kaplan_meier_input, True)

    print("Total patients:", feature_matrix_constants.shape[0])
    print("Patient split. Train:", X_train_constant.shape[0], "Test:", X_test_constant.shape[0])
    X_train, y_train, X_test, y_test = get_train_test(feature_matrix, X_train_constant, X_test_constant, MAX_QUARTER)


    print("Test samples:", X_test.shape[0])
    print("Test samples label distribution:")
    print(feature_matrix.loc[X_test.index, "label"].value_counts())


    _, y_prob, _ = calculate_kaplan_meier_error(X_test_constant, X_test, y_test, kmf_estimators)
    metrics, y_prob, feature_importance, _ = classify(X_train, y_train, X_test, y_test, feature_matrix, True, classification_output)
    #metrics, y_prob, _ = classify_mlp(X_train, y_train, X_test, y_test, feature_matrix, True, classification_output)

    start = time()
    cross_validation(feature_matrix, feature_matrix_constants, kaplan_meier_input, feature_output)
    end = time()
    print("Execution time cv", (end-start))

os.makedirs(snakemake.params[0], exist_ok=True)
train_and_classify(snakemake.input[0], snakemake.input[1], snakemake.input[2], snakemake.output[0], snakemake.output[1])
