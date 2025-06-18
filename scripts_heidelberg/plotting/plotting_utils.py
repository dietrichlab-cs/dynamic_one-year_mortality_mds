import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, LinearSegmentedColormap, BoundaryNorm
from sklearn.calibration import CalibrationDisplay
from sklearn.metrics import PrecisionRecallDisplay, RocCurveDisplay


def get_length_metric(df, metric, length):
    return df[df["length"] == length][metric].dropna()


def aur_roc_plot(estimator, X_test, y_test, plot_dir):
    RocCurveDisplay.from_estimator(estimator, X_test, y_test, pos_label=1)
    plt.savefig(plot_dir + "/auroc_curve.svg")
    plt.clf()


def calibration_plot(y_test, y_prob, plot_dir):
    CalibrationDisplay.from_predictions(y_test, y_prob[:, 1])
    plt.savefig(plot_dir + "/calibration.svg")


def precision_recall_plot(y_test, y_prob, file_name, plot_dir, plot=False):
    if type(y_prob[0]) != np.float64: positive_class_prob = y_prob[:,1]
    else: positive_class_prob = y_prob
    display = PrecisionRecallDisplay.from_predictions(y_test, positive_class_prob, pos_label=1)
    if plot: plt.savefig(plot_dir + "/" + file_name  + ".svg")
    plt.clf()
    return display.average_precision, display


def plot_loss(clf, plot_dir):
    # Retrieve evaluation results
    results = clf.evals_result()

    # Number of boosting rounds
    epochs = len(results['validation_0']['logloss'])
    x_axis = range(epochs)

    # Plot training and validation log loss
    plt.figure()
    plt.plot(x_axis, results['validation_0']['logloss'], label='Train')
    plt.plot(x_axis, results['validation_1']['logloss'], label='Test')
    plt.legend()
    plt.xlabel('Boosting Round')
    plt.ylabel('Log Loss')
    plt.title('XGBoost Log Loss Over Boosting Rounds')
    plt.savefig(plot_dir + "/loss.svg")
    plt.clf()


def classification_plot(test_data_df, y_test, output_file, plot_dir, max_quarters):
    patients = test_data_df.index.str.split(".").str[0].unique()
    patient_rows = []
    patient_ground_truth = []
    for patient in patients:
        values = np.zeros(shape=(max_quarters))
        ground_truth = np.zeros(shape=(max_quarters))
        for i in range(max_quarters):
            sample_index = patient + "." + str(i+1)
            if not sample_index in test_data_df.index:
                values[i] = -1
                ground_truth[i] = -1
            else:
                values[i] = test_data_df.loc[sample_index, "c_1"]
                ground_truth[i] = y_test.loc[sample_index]

        patient_rows.append(values)
        patient_ground_truth.append(ground_truth)
    matrix = np.vstack(patient_rows)
    ground_truth = np.vstack(patient_ground_truth)
    gradient_cmap = LinearSegmentedColormap.from_list(
        "green_yellow_red", ["green", "yellow", "red"]
    )
    # Combine the gradient with gray for -1
    colors = ['lightgray'] + [gradient_cmap(i) for i in np.linspace(0, 1, 256)]
    combined_cmap = ListedColormap(colors)

    # Define the boundaries: -1 (gray), 0-1 (gradient)
    boundaries = [-1.5, -0.5] + list(np.linspace(0, 1, 256))  # Transition from -1 to the gradient
    norm = BoundaryNorm(boundaries, combined_cmap.N)
    # Plot
    fig, ax = plt.subplots(figsize=(10,len(patients)/3))
    cax = ax.matshow(matrix, cmap=combined_cmap, norm=norm)
    ax.xaxis.set_ticks_position('bottom')

    # Add a colorbar with labels
    cbar = plt.colorbar(cax, ticks=[0, 1])
    cbar.ax.set_yticklabels(['low probability', 'high probability'])
    # Add labels inside each cell
    for i in range(ground_truth.shape[0]):  # Iterate over patients
        for j in range(ground_truth.shape[1]):  # Iterate over quarters
            if ground_truth[i][j] == -1: text = "-"
            elif ground_truth[i][j] == 0: text = "0"
            elif ground_truth[i][j] == 1: text = "1"
            ax.text(j, i, text, ha='center', va='center', fontsize=8)
    # Customize ticks and labels
    ax.set_xticks(range(matrix.shape[1]))
    ax.set_xticklabels([f"{i + 1}" for i in range(matrix.shape[1])], fontsize=8)
    ax.set_yticks(range(matrix.shape[0]))
    ax.set_yticklabels([f"{p}" for p in patients], fontsize=8)

    # Add axis labels and title
    plt.xlabel("Time (Quarters)", fontsize=12)
    plt.ylabel("Patients", fontsize=12)
    plt.title("Patient Predictions Over Time", fontsize=14)
    # Show the plot
    plt.tight_layout()
    plt.savefig(plot_dir + "/classification_plot.svg")
    plt.clf()


def plot_kaplan_meier(km, results, plot_dir):
    fig, ax = km.plot(results, visible=False)
    ax_list = fig.axes
    axis = ax_list[0]
    axis.set_xlim(0, 2000)
    fig.savefig(plot_dir + "/kaplan_meier_train.svg")
    plt.clf()


def plot_tte(tte_gbm, meanlineprops, medianprops, colors, plot_dir):
    print("PLOTTING BRIER BY TTE")
    plt.clf()
    plt.title("Brier Score for positive class depending on time-to-event", fontsize=14)
    for i in range(4):
        bp1 = plt.boxplot([tte_gbm[:, i]], positions=[i * 4], patch_artist=True,
                          widths=.5, notch=False, showmeans=True, meanprops=meanlineprops, medianprops=medianprops)
        for patch, color in zip(bp1['boxes'], colors):
            patch.set_facecolor(color)
        print(i)
        print("Median:", [item.get_ydata() for item in bp1['medians']])
        print("Means:", [item.get_ydata() for item in bp1['means']])
        print("Whiskers:", [item.get_ydata() for item in bp1['whiskers']])
    ticks = ["<" + str((i + 1) * 90) for i in range(4)]
    plt.xticks([(i * 4) + .5 for i in range(len(ticks))], ticks)
    hB, = plt.plot([1, 1], [0.2, 0.2], '-', color='cornflowerblue')
    plt.legend([hB], ['GBM'], loc="upper left")
    hB.set_visible(False)
    plt.ylabel("Brier Score", fontsize=12)
    plt.xlabel("days to event", fontsize=12)
    plt.tight_layout()
    plt.savefig(plot_dir + "/tte_analysis.svg")


def plot_ratio_over_time(df, lengths, meanlineprops, medianprops, colors, plot_dir):
    plt.clf()
    print("PLOTTING RATIO BY LENGTH")
    f = plt.figure()
    f.set_figheight(5)
    f.set_figwidth(12)
    for i, l in enumerate(lengths):
        bp1 = plt.boxplot(get_length_metric(df, "ratio_test", l), positions=[i * 8], patch_artist=True, widths=1.5, notch=False,
                          showmeans=True, meanprops=meanlineprops, medianprops=medianprops)
        for patch, color in zip(bp1['boxes'], colors):
            patch.set_facecolor(color)
        print(i)
        print("Median:", [item.get_ydata() for item in bp1['medians']])
        print("Means:", [item.get_ydata() for item in bp1['means']])
        print("Whiskers:", [item.get_ydata() for item in bp1['whiskers']])
    ticks = [str(i) for i in [1] + list(range(3, 31, 3))]
    plt.xticks([(i * 8) + 1 for i in [0] + list(range(2, 30, 3))], ticks)
    plt.xlim(left=-5)
    plt.ylim(0, 1)
    plt.ylabel("fraction of positive labels", fontsize=12)
    plt.xlabel("sample length in quarterly intervals $Q_i$", fontsize=12)
    # plt.title("Positive test set label ratio for snapshots grouped by length", fontsize=14)
    plt.tight_layout()
    plt.savefig(plot_dir + "/stability_over_time_ratio.svg")


def plot_brier(results_gbm, meanlineprops, medianprops, plot_dir):
    print("PLOTTING BRIER")
    plt.clf()
    labels = ["Complete", "Class 0", "Class 1"]
    fig, axs = plt.subplots(1, 3, sharey='row')
    # fig.suptitle("Brier scores for IPSS-R and GBM model", fontsize=14)
    for i in range(3):
        ax = axs[i]
        bp1 = ax.boxplot([results_gbm[:, i]], labels=['GBM'], notch=False, showmeans=True,
                         meanprops=meanlineprops, medianprops=medianprops)
        print("Median:", [item.get_ydata() for item in bp1['medians']])
        print("Means:", [item.get_ydata() for item in bp1['means']])
        print("Whiskers:", [item.get_ydata() for item in bp1['whiskers']])
        ax.set_title(labels[i])
    plt.ylabel("Brier Score", fontsize=12)
    plt.tight_layout()
    fig.savefig(plot_dir + "/brier_score.svg")


def plot_single_index_result_metric(results_gbm, metric_index, metric_name, meanlineprops, medianprops, plot_dir):
    plt.clf()
    print(f"PLOTTING {metric_name}")
    # plt.title("AUROC for IPSS-R and GBM model", fontsize=14)
    bp1 = plt.boxplot([results_gbm[:, metric_index]], labels=["GBM"], notch=False, showmeans=True,
                      meanprops=meanlineprops, medianprops=medianprops)
    plt.axhline(0.5, linestyle="--")
    print("Median:", [item.get_ydata() for item in bp1['medians']])
    print("Means:", [item.get_ydata() for item in bp1['means']])
    print("Whiskers:", [item.get_ydata() for item in bp1['whiskers']])
    plt.ylim(0, 1)
    plt.ylabel(metric_name, fontsize=12)
    plt.tight_layout()
    plt.savefig(plot_dir + f"/{metric_name}.svg")

def plot_metric_by_length(df, metric, metric_title, lengths, meanlineprops, medianprops, colors, plot_dir):
    plt.clf()
    print(f"PLOTTING {metric_title} BY LENGTH")
    f = plt.figure()
    f.set_figheight(5)
    f.set_figwidth(12)
    for i, l in enumerate(lengths):
        bp1 = plt.boxplot([get_length_metric(df, f"{metric}_gbm", l)], positions=[i * 8],
                          notch=False, patch_artist=True, widths=1, showmeans=True, meanprops=meanlineprops,
                          medianprops=medianprops)
        for patch, color in zip(bp1['boxes'], colors):
            patch.set_facecolor(color)
        # plt.setp(bp1["medians"], color="aqua")
        print(i)
        print("Median:", [item.get_ydata() for item in bp1['medians']])
        print("Means:", [item.get_ydata() for item in bp1['means']])
        print("Whiskers:", [item.get_ydata() for item in bp1['whiskers']])
    ticks = [str(i) for i in [1] + list(range(3, 31, 3))]
    plt.xticks([(i * 8) for i in [0] + list(range(2, 30, 3))], ticks)
    hB, = plt.plot([1, 1], '-', color='cornflowerblue')
    plt.legend([hB], ['GBM'], loc="lower left")
    hB.set_visible(False)
    plt.xlim(left=-5)
    plt.ylim(0, 1)
    plt.ylabel(metric_title, fontsize=12)
    plt.xlabel("sample length in quarterly intervals $Q_i$", fontsize=12)
    # plt.title("AUROC scores for snapshots grouped by length", fontsize=14)
    plt.tight_layout()
    plt.savefig(plot_dir + f"/stability_over_time_{metric}.svg")


def plot_average_metric_by_length(df, metric, metric_title, lengths, colors, plot_dir):
    aurocs_gbm_mean = []
    for l in lengths:
        aurocs_gbm_mean.append(np.mean(get_length_metric(df, f"{metric}_gbm", l)))

    plt.clf()
    plt.title(f"Average {metric_title} grouped by snapshot length", fontsize=14)
    plt.ylabel(metric_title, fontsize=12)
    plt.xlabel("sample length in quarterly intervals", fontsize=12)
    plt.plot(lengths, aurocs_gbm_mean, linestyle="-", marker="o", color=colors[0], label="GBM")
    plt.legend(loc="lower left")
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(plot_dir + f"/stability_over_time_mean_{metric}.svg")


def plot_feature_importance(feature_importance, features_to_plot, meanlineprops, medianprops, plot_dir):
    plt.clf()
    f = plt.figure()
    f.set_figheight(12)
    f.set_figwidth(10)
    for i, f in enumerate(reversed(features_to_plot)):
        plt.boxplot(feature_importance[f[0]], positions=[i * 2], notch=False, vert=False, showmeans=True, labels=[f[0]],
                    widths=1.5, meanprops=meanlineprops, medianprops=medianprops)
    plt.ylabel("features", fontsize=12)
    plt.xlabel("importance", fontsize=12)
    # plt.title("Feature Importance for the 20 on average most important features", fontsize=14)
    plt.tight_layout()
    plt.savefig(plot_dir + "/fi.svg")
