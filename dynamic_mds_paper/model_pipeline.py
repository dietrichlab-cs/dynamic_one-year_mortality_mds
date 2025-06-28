import math
from collections import defaultdict

import math
from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from io import StringIO

import joblib
import numpy as np
import pandas as pd
import tsflex.features as ts
from fastapi import HTTPException
from tsflex.features.integrations import tsfresh_settings_wrapper
from tsflex.features.utils import make_robust

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




class LongitudinalFeaturePredictor:

    def __init__(self, input_data):
        self.discrimination_point = 365
        self.min_nb_samples = 3
        self.max_quarters = 32
        self.first_diagnosis = None
        self.input_data = input_data
        self.model = joblib.load('models/gbm_all_patients.joblib')
        self.BASE_DATE = datetime(2000, 1, 1)
        self.RENAME_DICT = {
            "leukocytes": "Leukozyten",
            "thrombocytes": "Thrombozyten",
            "erythrocytes": "Erythrozyten",
            "hemoglobin": "Hämoglobin",
            "hematocrit": "Hämatokrit",
            "day_from_diagnosis": "day_from_diagnosis"
        }

    def _convert_csv_string(self):
        csvString = self.input_data["features"]
        if len(csvString.strip().splitlines()) < 2:
            raise HTTPException(status_code=400, detail="CSV must contain header and at least one row.")
        df = pd.read_csv(StringIO(csvString))
        df.rename(columns=self.RENAME_DICT, inplace=True)
        df.set_index("day_from_diagnosis", inplace=True)
        # Ensure index is numeric days
        try:
            df.index = pd.to_numeric(df.index)
        except Exception:
            raise HTTPException(status_code=400, detail="CSV index must be numeric day offsets.")
        # Convert index to datetime
        df.index = [self.BASE_DATE + timedelta(days=int(d)) for d in df.index]
        # Insert BASE_DATE row if missing
        if self.BASE_DATE not in df.index:
            base_row = pd.DataFrame([[pd.NA] * len(df.columns)], columns=df.columns, index=[self.BASE_DATE])
            df = pd.concat([base_row, df])
            df = df[~df.index.duplicated(keep="first")]
            df.sort_index(inplace=True)

        df.index.name = "date"
        self.input_data["features"] = df

    def _extract_features_for_patient(self):
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
                                          approve_sparsity=True, include_final_window=True, n_jobs=1)
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

    def _get_probability(self):
        # Retrieve feature names from the pretrained model
        feature_names = self.model.get_booster().feature_names
        # Filter features for those used in the trained model
        self.feature_matrix = self.feature_matrix[feature_names]
        return self.model.predict_proba(self.feature_matrix)


    def get_prediction(self):
        self._convert_csv_string()
        # start with extracting all the features from the time-series
        self._extract_features_for_patient()
        # if the feature matrix is empty we exclude the patient from further analysis
        if self.feature_matrix is None:
            return None
        self._add_constant_features()
        print(self.feature_matrix)
        self.feature_matrix.to_csv("sanity.csv")
        return self._get_probability()[0][1]

class BaselineFeaturePredictor:

    def __init__(self, input_data):
        self.discrimination_point = 365
        self.min_nb_samples = 3
        self.max_quarters = 32
        self.first_diagnosis = None
        self.input_data = input_data
        self.model = joblib.load('models/gbm_all_patients_easix_baseline.joblib')
        self.feature_matrix = pd.DataFrame(columns=["blasts", "age", "cyto", "gender", "karyotype", "easix", "leuko_ed", "hb_ed"])


    def _add_constant_features(self):
        # Build a new row with constants
        const_row = {
            "blasts": float(self.input_data["blasts"]) if self.input_data["blasts"] is not None else np.nan,
            "age": float(self.input_data["age"]),
            "cyto": float(self.input_data["karyotype"]) if self.input_data["karyotype"] is not None else np.nan,
            "gender": 0.0 if self.input_data["gender"] == "f" else 1.0,
            "easix": float(self.input_data["easix"]) if self.input_data["easix"] is not None else np.nan,
            "leuko_ed": float(self.input_data["leuko_ed"]) if self.input_data["leuko_ed"] is not None else np.nan,
            "hb_ed": float(self.input_data["hb_ed"]) if self.input_data["hb_ed"] is not None else np.nan,
            "window_length": float(self.input_data["survival_time"]) if self.input_data["survival_time"] is not None else np.nan,
            "quarters": math.ceil(max((self.input_data["survival_time"] / 90), 1e-8)) if self.input_data["survival_time"] is not None else np.nan,
        }
        # Create a DataFrame with this single row
        const_df = pd.DataFrame([const_row], index=[0])
        # Append to the feature matrix
        self.feature_matrix = pd.concat([self.feature_matrix, const_df], axis=0)
        # Optional: ensure correct types
        self.feature_matrix = self.feature_matrix.astype("float32")

    def _get_probability(self):
        # Retrieve feature names from the pretrained model
        feature_names = self.model.get_booster().feature_names
        # Filter features for those used in the trained model
        self.feature_matrix = self.feature_matrix[feature_names]
        print(self.feature_matrix)
        return self.model.predict_proba(self.feature_matrix)


    def get_prediction(self):
        self._add_constant_features()
        print(self.feature_matrix)
        self.feature_matrix.to_csv("sanity_baseline.csv")
        return self._get_probability()[0][1]
