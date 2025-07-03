import csv
import math

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


def additional_custom_features(x: pd.Series):
    last_three_points_slope = slope((x.index[-1], x.iloc[-1]), (x.index[-3], x.iloc[-3]))
    return last_three_points_slope#, x.iloc[-1]


class Feature_Extractor:

    def __init__(self, discrimination_point, min_nb_samples, max_quarters):
        self.discrimination_point = discrimination_point
        self.min_nb_samples = min_nb_samples
        self.max_quarters = max_quarters

    def _extract_features_for_patient(self, patient):
        # define additional non tsfresh feature functions
        add_feats = make_robust(ts.FuncWrapper(additional_custom_features,
                                              [
                                                  "last_three_points_slope"
                                                  #"last_value"
                                              ],
                                              input_type=pd.Series), passthrough_nans=False, min_nb_samples=self.min_nb_samples)
        # define tsfresh feature funtions
        feature_funcs = [make_robust(f, passthrough_nans=False, min_nb_samples=self.min_nb_samples) for f in tsfresh_settings_wrapper(settings=TS_FRESH_FUNCS)]
        feature_funcs.append(add_feats)
        # extract patients id from data csv file apth
        patient_id = patient.split("/")[-1][:-4]

        # load dataframe with time-series data and set the index
        input_df = pd.read_csv(patient)
        input_df['date'] = pd.to_datetime(input_df['date'])
        input_df = input_df.set_index('date')

        # initialize list for valid quarters
        valid_quarters_set = set()
        track_number_of_values = pd.Series(index=input_df.columns, dtype=np.float64)
        # keep track of the maximum index for each quarter
        max_quarter_index = dict()
        # for each date, check to which quarter it belongs
        for index in input_df.index:
            quarter_of_entry = math.ceil(max(((index - self.first_diagnosis).days / 90), 1e-8))
            # do not consider a row of the input dataframe if either it exceeds the MAX_QUARTER constant
            # or the value is within 60 days of the event
            if quarter_of_entry > self.max_quarters: break
            # if (self.event_date - index).days < 60: break
            if (self.event_date - index).days <= 0: break

            # skip empty rows
            if input_df.loc[index].isnull().values.all():
                continue

            # if the index is the first value for the current quarter of larger than the previous max, set the max index for the quarter
            #if quarter_of_entry not in max_quarter_index.keys() or max_quarter_index[quarter_of_entry] < index:
            max_quarter_index[quarter_of_entry] = index
            # for each parameter, update the number of values encountered so far for it
            for column in input_df.columns:
                if not np.isnan(input_df.loc[index, column]):
                    if np.isnan(track_number_of_values[column]):
                        track_number_of_values[column] = 1
                    else:
                        track_number_of_values[column] += 1
            # as soon as all columns have more than MIN_NB_SAMPLES we can add subsequent quarters as valid quarters
            # note that only quarters adding new information, i.e. with according rows in the input dataframe will be considered
            if track_number_of_values.ge(self.min_nb_samples).all():
                valid_quarters_set.add(quarter_of_entry)

        valid_quarters = list(valid_quarters_set)
        valid_quarters.sort()
        # skip patient if no valid quarters where found
        if len(valid_quarters) == 0:
            return None

        # to avoid a certain behavior, where tsflex does not calculate features if the window length is equal to the timespan of the
        # whole series, we add a dummy day, one day after the last entry if the last entry is not the event day.
        # This extra day will have no influence on the calculated features and in the case of the training data used since we make sure to
        # include the event day as the last entry in earlier steps
        if input_df.index.max() < self.event_date:
            input_df.loc[self.event_date + pd.to_timedelta(1, "D")] = pd.Series(dtype=float)

        feature_matrix_for_patient = pd.DataFrame()
        # extract features for each choice
        for quarter in valid_quarters:
            # always set the window size for the current quarter to the difference between first diagnosis and the last data point in the quarter
            # "+ 1 (day)" is needed since sometimes we added minutes to keep the index unique
            window = (max_quarter_index[quarter] - self.first_diagnosis).days + 1

            # the time to event of the current quarter will just be the difference between window size and total living days
            time_to_event = self.life_days - window
            # one last safety check to make sure the time to event is never lower than 30 days. This check should always be false given
            # the window calculation from earlier
            # if time_to_event < 60: continue

            # we can now label the quarter
            # only if the patient is still alive and the time to event is less than the time to label, we have to exclude the quarter
            # the reason being that at this point in time we can not draw any conclusions for the patients status at time of label
            # e.g. patient is alive i.e. event = right censored point,
            # we look at 365 days mortality and the last quarter's time to event is 300 days. Then the censor point is reached before the label point
            # and we have no information if the event was observed for the patient in the last 65 days to label point.
            if self.alive == 1:
                if time_to_event <= self.discrimination_point:
                    continue
                else:
                    label = 0
            else:
                if time_to_event <= self.discrimination_point:
                    label = 1
                else:
                    label= 0

            # the stride for the feature collection is just the complete timespan between first_diagnosis and death.
            # This ensures we only get the first window since it is the only one we are interested in
            fc = ts.FeatureCollection(
                feature_descriptors=[
                    ts.MultipleFeatureDescriptors(feature_funcs, series_names=[param_name for param_name in input_df.columns],
                                                  windows="" + str(window) + "D",
                                                  strides="" + str(self.event_date - self.first_diagnosis) + "D")
                ]
            )
            # calculate the extracted features
            extracted_features = fc.calculate(input_df, return_df=True, window_idx="begin", show_progress=False, approve_sparsity=True)
            # set NaN values to a very low value to indicate an unplausible value (this is possible because of very rare NaN values)
            extracted_features.fillna(value=-1000, inplace=True)

            # translate the ts-flex column names by removing window information
            translation_dict = {}
            for col in extracted_features.columns: translation_dict[col] = col.replace("__", "_").split("=")[0][:-2]
            extracted_features = extracted_features.rename(translation_dict, axis='columns')
            extracted_features['quarters'] = quarter
            extracted_features['window_length'] = window
            extracted_features['time_to_event'] = time_to_event
            extracted_features['label'] = label
            # append the extracted row to the patient feature matrix
            feature_matrix_for_patient = pd.concat([feature_matrix_for_patient, extracted_features.iloc[:1]])


        # skip a patient if no quarters were calculated
        if len(feature_matrix_for_patient.index) == 0: return None

        # get the number of quarters, i.e. samples for the patient
        number_of_samples = len(feature_matrix_for_patient.index)

        # reset the index and set it to a new index of format "<patient_id>.<index of sample>"
        feature_matrix_for_patient.reset_index(drop=True, inplace=True)
        feature_matrix_for_patient.index = [
            f"{patient_id}.{row['quarters']}"  # Correctly access 'quarters' from the row
            for _, row in feature_matrix_for_patient.iterrows()  # Unpack index and row from iterrows()
        ]
        return feature_matrix_for_patient


    def generate_subseries(self, labels_file, raw_data, feature_matrix_output):
        # extract first diagnosis and death from labels file
        self.first_diagnosis, self.event_date, self.life_days, self.alive = None, None, None, None
        excluded = False
        with open(labels_file) as labels:
            meta_reader = csv.DictReader(labels)
            for row in meta_reader:
                # skip the patient if he was excluded in the data analysis step
                if row['Patient'] == "Excluded":
                    excluded = True
                    break
                self.first_diagnosis = datetime.strptime(row['diagnosis'], '%Y-%m-%d %H:%M:%S')
                self.event_date = datetime.strptime(row['event'], '%Y-%m-%d %H:%M:%S')
                self.alive = int(row['alive'])
                self.life_days = int(row['lifetime'])
        if excluded:
            output_file = open(feature_matrix_output, "w")
            output_file.write("Excluded")
            return
        assert self.alive is not None
        feature_matrix = self._extract_features_for_patient(raw_data)
        # if the feature matrix is empty we exclude the patient from further analysis
        if feature_matrix is None:
            output_file = open(feature_matrix_output, "w")
            output_file.write("Excluded")
            return

        feature_matrix.to_csv(feature_matrix_output)