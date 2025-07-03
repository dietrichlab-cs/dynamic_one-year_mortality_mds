import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd


def within_three_week(date1, date2):
    return abs((date1 - date2).days) <= 14

def is_after(date1, date2):
    return abs((date1 - date2).days) < 0

def load_patients(patient_file):
    patients = {}
    for patient in csv.DictReader(open(patient_file)):
        patients[patient["cis_id"]] = datetime.strptime(patient["diagnosis_date"], '%d.%m.%Y')
    return patients


def calculate_easix(pats):
    file_paths = Path('../../data/publication_meddat_data').rglob('ids_*001.csv')
    patient_easix_params = defaultdict(lambda: [None, None, None])
    for file in list(file_paths):
        print(f"Processing {file}")
        with open(file, encoding='iso-8859-1') as data_file:
            reader = csv.DictReader(data_file, delimiter=';')
            for row in reader:
                if row["Lebensnummer"] not in pats.keys(): continue
                # combine Analyt name and number into a unique key
                parameter_name = row['AnalytAbku'] + row['Analytnummer']
                if parameter_name not in ["CREA100", "LDH3784", "THROMB310"]:
                    continue
                if not within_three_week(datetime.strptime(row['Abnahmedatum'], '%d.%m.%Y'), pats[row['Lebensnummer']]):
                    continue
                # if all easix params are already there and the Abnahmedatum is after diagnosis, we simply break the loop
                # this way we choose the point in time closest to diagnosis
                if all(patient_easix_params[row['Lebensnummer']]) and is_after(pats[row['Lebensnummer']], datetime.strptime(row['Abnahmedatum'], '%d.%m.%Y')):
                    break
                if row['Messwert String'][0] in ['>', '<']:
                    value = row['Messwert String'].replace(">", "").replace("<", "")
                else:
                    try:
                        float(row['Messwert String'])
                    except:
                        continue
                    value = row['Messwert String']
                if parameter_name == "CREA100" and patient_easix_params[row['Lebensnummer']][0] is None:
                    patient_easix_params[row['Lebensnummer']][0] = value
                elif parameter_name == "LDH3784" and patient_easix_params[row['Lebensnummer']][1] is None:
                    patient_easix_params[row['Lebensnummer']][1] = value
                elif parameter_name == "THROMB310" and patient_easix_params[row['Lebensnummer']][2] is None:
                    patient_easix_params[row['Lebensnummer']][2] = value

    easix_scores = {}
    for pat in patient_easix_params.keys():
        easix_parameter = patient_easix_params[pat]
        if all(x is not None for x in easix_parameter):
            easix_score = float(easix_parameter[0]) * float(easix_parameter[1]) / float(easix_parameter[2])
            print(f"{pat}: {easix_score}. Parameter: {easix_parameter}")
            easix_scores[int(pat)] = easix_score
    print("Calculated easix score:", len(easix_scores.keys()))
    return easix_scores


if __name__ == "__main__":
    pats = load_patients("../../data/publication_output/dataset/patient_data_filtered.csv")
    easix = calculate_easix(pats)
    df = pd.read_csv("../../data/publication_output/dataset/patient_data_filtered.csv")
    df.set_index("cis_id", inplace=True)
    print(df.index)
    print(easix)
    df["easix"] = df.index.map(easix)
    df.to_csv("../../data/publication_output/dataset/patient_data_filtered_easix.csv")
