import csv

import warnings
from collections import defaultdict

import numpy as np

warnings.simplefilter(action='ignore', category=FutureWarning)

import pandas as pd
from datetime import datetime

def get_hb_and_leuko(id, dataset_dir):
    raw_file = f"{dataset_dir}/raw_data/{id}.csv"
    columns_to_load = ["Leukozyten", "Hämoglobin"]
    index_column = "date"
    # Load the CSV with the necessary columns and parse dates
    df = pd.read_csv(raw_file, usecols=[index_column] + columns_to_load, parse_dates=[index_column], index_col=index_column)
    values = []
    for column in columns_to_load:
        # Check if the first value is not null
        if pd.notnull(df[column].iloc[0]):
            # If the first value is not null, use it
            first_value = df[column].iloc[0]
        else:
            # If the first value is null, check if the second row's date is within 7 days
            second_row_date = df.index[1] if len(df) > 1 else None
            if second_row_date and (second_row_date - df.index[0]).days <= 7:
                second_value = df[column].iloc[1]
                first_value = second_value
            else:
                first_value = np.nan # Or choose some other fallback if the second value is not valid
        values.append(first_value)
    return values

def extract_constant_features(constant_feature_file, patients, dataset_dir):
    with open(constant_feature_file, "r") as constant_features_csv:
        reader = csv.DictReader(constant_features_csv)
        constant_features = {}
        for row in reader:
            id = row['cis_id']
            if id not in patients: continue
            gender = int(row['gender'])
            #ipss_r_age = row['ipssr']
            blasts = int(float(row['blasts'])) if row['blasts'] else None
            cyto = int(row['cyto']) if row['cyto'] else None
            age = row['age']
            if age == '':
                birthday = datetime.strptime(row['birthdate'], '%d.%m.%Y')
                first_diagnosis = datetime.strptime(row['diagnosis_date'], '%d.%m.%Y')
                age = (first_diagnosis-birthday).days/365
            else:
                age = float(age)

            hb_leuko = get_hb_and_leuko(id, dataset_dir)

            constant_features[id] = [gender, age, blasts, cyto, hb_leuko[0], hb_leuko[1]]
            #constant_features[id] = [gender, age, ipss_r_age, blasts, cyto]

        return constant_features


# join together all feature dataframes for all patients
def join_ts_dataframes(dynamic_files):
    joined_df = pd.DataFrame()
    for file in dynamic_files:
        ts_dataframe = pd.read_csv(file, dtype={'Unnamed: 0':str})
        if "Excluded" in ts_dataframe.columns: continue
        ts_dataframe.set_index("Unnamed: 0", inplace=True)
        joined_df = pd.concat([joined_df, ts_dataframe])
    return joined_df


def build_complete_feature_matrix(dynamic_files, constant_patient_data_file, output_file, output_constant_only, dataset_dir):
    input_df = join_ts_dataframes(dynamic_files)
    print(input_df)
    patients, patient_samples = set(), defaultdict(list)
    # get patients and their custom feature matrix indices
    for idx in input_df.index:
        patient = str(idx).split(".")[0]
        patients.add(patient)
        patient_samples[patient].append(idx)
    patients = sorted(list(patients), key=str)
    # fetch constant features and a list of patients with missing constants that will need to be excluded
    # additionally we get the who classification one-hot encoded
    constant_features = extract_constant_features(constant_patient_data_file, patients, dataset_dir)

    # prepare the output dataframe
    # const_feat_names = ['gender', 'age', 'ipssr_age', 'blasts', 'cyto', 'lifetime']
    const_feat_names = ['gender', 'age', 'blasts', 'cyto', 'leuko_ed', 'hb_ed', 'lifetime']
    output_df = pd.DataFrame(columns=list(input_df.columns) + const_feat_names[:-1])
    output_df_constant_only = pd.DataFrame(columns=const_feat_names)

    # prepare a dataframe with ipssr, lifetime and censoring for kaplan meier curve calculation
    #km_df = pd.DataFrame(columns=["id","ipssr_group", "lifetime", "event_occurred"])
    #km_df = km_df.set_index("id")

    # add constant features to extracted time series features and store them in the output dataframe
    for patient in patients:
        eda_file = open(dataset_dir + "/labels/" + patient + "_labels.csv")
        eda_reader = csv.DictReader(eda_file)
        for row in eda_reader:
            #km_df.loc[patient] = [constant_features[patient][2], row["lifetime"], 0 if row["alive"] == "1" else 1]
            new_series = pd.Series(constant_features[patient] + [row['lifetime']], index=const_feat_names)
            output_df_constant_only.loc[patient] = new_series
            for patient_idx in patient_samples[patient]:
                output_df.loc[patient_idx] = pd.concat([input_df.loc[patient_idx], new_series[:-1]])
            break

    # store the final two matrices (constant features only and all features) as csv files
    output_df.to_csv(output_file)
    output_df_constant_only.to_csv(output_constant_only)
    #km_df.to_csv(kaplan_meier_file)


build_complete_feature_matrix(snakemake.input[1:], snakemake.input[0], snakemake.output[0], snakemake.output[1], snakemake.params[1])
