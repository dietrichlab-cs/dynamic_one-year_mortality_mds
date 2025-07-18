import csv

import warnings
from collections import defaultdict

warnings.simplefilter(action='ignore', category=FutureWarning)

import pandas as pd
from datetime import datetime


def extract_constant_features(constant_feature_file, patients):
    with open(constant_feature_file, "r") as constant_features_csv:
        reader = csv.DictReader(constant_features_csv)
        constant_features = {}
        for row in reader:
            id = row['cis_id']
            if id not in patients: continue
            gender = int(row['gender'])
            ipss_r_age = row['ipssr']
            blasts = int(float(row['blasts']))
            cyto = int(row['cyto'])
            age = row['age']
            if age == '':
                birthday = datetime.strptime(row['birthdate'], '%d.%m.%Y')
                first_diagnosis = datetime.strptime(row['diagnosis_date'], '%d.%m.%Y')
                age = (first_diagnosis-birthday).days/365
            else:
                age = float(age)

            constant_features[id] = [gender, age, ipss_r_age, blasts, cyto]

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


def build_complete_feature_matrix(dynamic_files, constant_patient_data_file, output_file, output_constant_only, dataset_dir, kaplan_meier_file):
    input_df = join_ts_dataframes(dynamic_files)
    print(input_df)
    patients, patient_samples = set(), defaultdict(list)
    # get patients and their custom feature matrix indices
    for idx in input_df.index:
        patient = str(idx).split(".")[0]
        patients.add(patient)
        patient_samples[patient].append(idx)
    patients = list(patients)
    # fetch constant features and a list of patients with missing constants that will need to be excluded
    # additionally we get the who classification one-hot encoded
    constant_features = extract_constant_features(constant_patient_data_file, patients)

    # prepare the output dataframe
    const_feat_names = ['gender', 'age', 'ipssr_age', 'blasts', 'cyto', 'lifetime']
    output_df = pd.DataFrame(columns=list(input_df.columns) + const_feat_names[:-1])
    output_df_constant_only = pd.DataFrame(columns=const_feat_names)

    # prepare a dataframe with ipssr, lifetime and censoring for kaplan meier curve calculation
    km_df = pd.DataFrame(columns=["id","ipssr_group", "lifetime", "event_occurred"])
    km_df = km_df.set_index("id")

    # add constant features to extracted time series features and store them in the output dataframe
    for patient in patients:
        eda_file = open(dataset_dir + "/labels/" + patient + "_labels.csv")
        eda_reader = csv.DictReader(eda_file)
        for row in eda_reader:
            km_df.loc[patient] = [constant_features[patient][2], row["lifetime"], 0 if row["alive"] == "1" else 1]
            new_series = pd.Series(constant_features[patient] + [row['lifetime']], index=const_feat_names)
            output_df_constant_only.loc[patient] = new_series
            for patient_idx in patient_samples[patient]:
                output_df.loc[patient_idx] = pd.concat([input_df.loc[patient_idx], new_series[:-1]])
            break

    # store the final two matrices (constant features only and all features) as csv files
    output_df.to_csv(output_file)
    output_df_constant_only.to_csv(output_constant_only)
    km_df.to_csv(kaplan_meier_file)


build_complete_feature_matrix(snakemake.input[3:], snakemake.input[0], snakemake.output[0], snakemake.output[1], snakemake.params[1], snakemake.output[2])
