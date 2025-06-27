import csv
import math
import uuid
from collections import defaultdict

import numpy as np
import tsflex.features as ts
from tsflex.features.integrations import tsfresh_settings_wrapper
from tsflex.features.utils import make_robust
import pandas as pd
import scipy as sc
from datetime import datetime


TS_FRESH_FUNCS = {
        "kurtosis": None,
        "large_standard_deviation":[{'r': 0.05}, {'r': 0.1}, {'r': 0.25}, {'r': 0.5}],
        "linear_trend": [{'attr': 'slope'}, {'attr': 'intercept'}, {'attr': 'pvalue'}],
        "linear_trend_timewise": [{'attr': 'slope'}, {'attr': 'intercept'}, {'attr': 'pvalue'}],
        "maximum": None,
        "mean": None,
        "median": None,
        "minimum": None,
        "skewness": None,
        "percentage_of_reoccurring_datapoints_to_all_datapoints": None,
        "quantile": [{'q': 0.1}, {'q': 0.25}, {'q': 0.5}, {'q': 0.75}, {'q': 0.9}, ],
        "standard_deviation": None,
        "variance": None,
        "variation_coefficient": None,
        "first_location_of_maximum": None,
        "first_location_of_minimum": None,
        "last_location_of_maximum": None,
        "last_location_of_minimum": None,
        "cid_ce": [{"normalize": True}]
    }


def slope(p1, p2):
    return (p2[1] - p1[1]) / (p2[0] - p1[0]).days


def lomb_scargle(x: pd.Series):
    tf_max = 200
    grid_spacing = 5000
    periods = np.linspace(.1, tf_max, grid_spacing)
    sample_freq = tf_max/grid_spacing
    angular_freqs = 2 * np.pi / periods
    pgram = sc.signal.lombscargle(x.index, (x.values- np.mean(x.values)), angular_freqs)
    std = np.std(x.values)
    if std == 0: std = 1e-10
    pgram *= 2 / (len(x.index) * std ** 2)
    max_index = np.sort(np.argpartition(pgram, -3)[-3:])
    max1, max2, max3 = periods[max_index[0]], periods[max_index[1]], periods[max_index[2]]
    power_of_max_period = pgram[np.argmax(pgram)]
    complexity_03 = len(periods[np.nonzero(pgram > 0.3)]) / len(periods)
    complexity_05 = len(periods[np.nonzero(pgram > 0.5)]) / len(periods)
    mean_power = np.mean(pgram)
    std_power = np.std(pgram)
    max_monthly_period_idx = np.argmax(pgram[:int(30/sample_freq)])
    max_quarterly_period_idx = np.argmax(pgram[:int(90/sample_freq)])
    max_monthly_period, max_monthly_power = periods[max_monthly_period_idx], pgram[max_monthly_period_idx]
    max_quarterly_period, max_quarterly_power = periods[max_quarterly_period_idx], pgram[max_quarterly_period_idx]
    return max1, max2, max3, power_of_max_period, complexity_03, complexity_05, max_monthly_period, max_monthly_power, max_quarterly_period, max_quarterly_power, mean_power, std_power


def additional_custom_features(x: pd.Series):
    last_three_points_slope = slope((x.index[-1], x.iloc[-1]), (x.index[-3], x.iloc[-3]))
    return last_three_points_slope#, x.iloc[-1]




class LongitudinalFeaturePredictor:

    def __init__(self, input_data):
        self.discrimination_point = 365
        self.min_nb_samples = 3
        self.max_quarters = 32
        self.first_diagnosis = None
        self.input_data = input_data

    def _extract_features_for_patient(self):
        # define lomb scargle feature functions
        ls_feats = make_robust(ts.FuncWrapper(lomb_scargle,
                                              [
                                                  "ls_max1", "ls_max2", "ls_max3", "power_of_max_period", "complexity_0.3", "complexity_0.5",
                                                  "max_monthly_period", "max_monthly_power", "max_quarterly_period", "max_quarterly_power",
                                                  "mean_power", "std_power"
                                              ],
                                              input_type=pd.Series), passthrough_nans=False, min_nb_samples=self.min_nb_samples)
        # define additional non tsfresh feature functions
        add_feats = make_robust(ts.FuncWrapper(additional_custom_features,
                                              [
                                                  "last_three_points_slope"
                                                  #"last_value"
                                              ],
                                              input_type=pd.Series), passthrough_nans=False, min_nb_samples=self.min_nb_samples)
        # define tsfresh feature funtions
        feature_funcs = [make_robust(f, passthrough_nans=False, min_nb_samples=self.min_nb_samples) for f in tsfresh_settings_wrapper(settings=TS_FRESH_FUNCS)]
        feature_funcs.append(ls_feats)
        feature_funcs.append(add_feats)
        # extract patients id from data csv file apth
        input_df = self.input_data["features"]
        self.first_diagnosis = input_df.index.min()
        # initialize list for valid quarters
        valid_quarter = False
        track_number_of_values = defaultdict(int)
        # for each date, check to which quarter it belongs
        for index in input_df.index:
            quarter_of_entry = math.ceil(max(((index - self.first_diagnosis).days / 90), 1e-8))
            # do not consider a row of the input dataframe if either it exceeds the MAX_QUARTER constant
            # or the value is within 60 days of the event
            if quarter_of_entry > self.max_quarters: continue
            # skip empty rows
            if input_df.loc[index].isnull().values.all():
                continue
            # for each parameter, update the number of values encountered so far for it
            for column in input_df.columns:
                if not np.isnan(input_df.loc[index, column]):
                    track_number_of_values[column] += 1
            # as soon as all columns have more than MIN_NB_SAMPLES we can evaluate the model
            if all(value > self.min_nb_samples for value in track_number_of_values.values()):
                valid_quarter = True
                break

        if not valid_quarter:
            return

        # extract features
        window = (input_df.index.max() - input_df.index.min()).days + 1
        print(window)
        # the stride for the feature collection is just the complete timespan between first_diagnosis and death.
        # This ensures we only get the first window since it is the only one we are interested in
        fc = ts.FeatureCollection(
            feature_descriptors=[
                ts.MultipleFeatureDescriptors(feature_funcs,
                                              series_names=[param_name for param_name in input_df.columns],
                                              windows="" + str(window) + "D",
                                              strides="" + str(window) + "D")
            ]
        )
        # calculate the extracted features
        extracted_features = fc.calculate(input_df, return_df=True, window_idx="begin", show_progress=False,
                                          approve_sparsity=True, include_final_window=True)
        print(extracted_features)
        # set NaN values to a very low value to indicate an unplausible value (this is possible because of very rare NaN values)
        extracted_features.fillna(value=-1000, inplace=True)

        # translate the ts-flex column names by removing window information
        translation_dict = {}
        for col in extracted_features.columns: translation_dict[col] = col.replace("__", "_").split("=")[0][:-2]
        extracted_features = extracted_features.rename(translation_dict, axis='columns')
        extracted_features['quarters'] = math.ceil(max(((input_df.index.max() - input_df.index.min()).days / 90), 1e-8))
        extracted_features['window_length'] = window
        self.feature_matrix = extracted_features


    def _add_constant_features(self):
        self.feature_matrix["blasts"] = self.input_data["blasts"]
        self.feature_matrix["age"] = self.input_data["age"]
        self.feature_matrix["cyto"] = self.input_data["karyotype"]
        self.feature_matrix["gender"] = 0 if self.input_data["gender"] == "f" else 1

    def get_prediction(self):
        # start with extracting all the features from the time-series
        self._extract_features_for_patient()
        # if the feature matrix is empty we exclude the patient from further analysis
        if self.feature_matrix is None:
            return None
        self._add_constant_features()
        print(self.feature_matrix)
