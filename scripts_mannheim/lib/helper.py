import itertools

from sklearn.metrics import mean_squared_error


def compute_tte_mse(X_test, y_test, y_prob):
    index_positive_label_time_to_event = {3: [], 2: [], 1: [], 0: []}
    for p in X_test.index:
        if X_test.loc[p, "label"] != 1: continue
        index = 0
        if X_test.loc[p, "time_to_event"] >= 270:
            index = 3
        elif X_test.loc[p, "time_to_event"] >= 180:
            index = 2
        elif X_test.loc[p, "time_to_event"] >= 90:
            index = 1
        index_positive_label_time_to_event[index].append(X_test.index.get_loc(p))
    return [mean_squared_error(y_test.iloc[index_positive_label_time_to_event[i]],y_prob[index_positive_label_time_to_event[i]]) for i in range(4)]


def get_train_test(feature_matrix, train_idx, test_idx, max_quarter):
    sample_idx_train = list(
        itertools.chain(*[[str(idx) + "." + str(i) for i in range(max_quarter+1)] for idx in train_idx.index]))
    sample_idx_train = [idx for idx in sample_idx_train if idx in feature_matrix.index]
    X_train, y_train = feature_matrix.drop(columns=['label', 'time_to_event']).loc[sample_idx_train], \
                       feature_matrix['label'].loc[sample_idx_train]

    sample_idx_test = list(
        itertools.chain(*[[str(idx) + "." + str(i) for i in range(max_quarter+1)] for idx in test_idx.index]))
    sample_idx_test = [idx for idx in sample_idx_test if idx in feature_matrix.index]
    X_test, y_test = feature_matrix.drop(columns=['label', 'time_to_event']).loc[sample_idx_test], \
                     feature_matrix['label'].loc[sample_idx_test]

    return X_train, y_train, X_test, y_test