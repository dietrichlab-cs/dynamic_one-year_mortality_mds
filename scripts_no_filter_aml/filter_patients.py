import csv
from collections import defaultdict
from datetime import datetime

import pandas as pd

MINIMUM_LIFETIME = snakemake.params[0]

def filter_patients(input_file, error_file=None):
    ids = []
    rows = []
    error_ids = []

    with open(error_file) as error_csv:
        reader = csv.reader(error_csv)
        for row in reader:
            error_ids.append(row[0])

    with open(input_file, encoding='UTF-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        fieldnames = ["id", "cis_id", "age", "gender", "blasts", "cyto", "birthdate", "diagnosis_date", "censoring_date", "censoring_type"]
        filter_reason = defaultdict(int)
        for row in reader:
            # only include patients with first diagnosis date and meddat id
            if row['Erstdiagnose Datum'] == '' or row['Meddat ID'] == '' or row['Geburtsdatum'] == '':
                filter_reason["diagnosis, meddat or bd empty"] += 1
                continue
            # exclude error patients, these are manually selected patients based on errors in the mds register
            if row['Meddat ID'] in error_ids:
                continue
            # skip patients that got a stem cell transplantation
            if not (row['Einteilung KMT/SCT (alt) Code 1'] in ['0', ''] and row['Einteilung KMT/SCT (alt) Code 2'] in ['0', '']):
                filter_reason["KMT"] += 1
                continue
            # skip patients who might have only the date for the sct date set (they might not have gotten an SCT but just to be sure)
            if row['Datum SCT 1'] != '' or row['Datum SCT 2'] != '':
                filter_reason["KMT_date"] += 1
                continue
            # skip patients which are lost to follow-up
            censoring_date = None
            if row['AML-Übergang Code'] == '1':
                censoring_type = 2
            elif row['Definitives Schicksal Code'] == '0':
                censoring_type = 0
            elif row['Definitives Schicksal Code'] == '2':
                censoring_type = 1
            else:
                filter_reason["Fate"] += 1
                continue
            # Exclude patients with no definitive date
            if censoring_type == 2 and row['Datum AML-Transformation'] == '':
                filter_reason["Fate_date"] += 1
                continue
            elif censoring_type in [0,1] and row['Datum definitives Schicksal'] == '':
                filter_reason["Fate_date"] += 1
                continue
            # check if a patient lived more than MINIMUM_LIFETIME years -> if so we can add the living patient with label
            # "lived longer than 5 years"
            if censoring_type == 0:
                first_diagnosis = datetime.strptime(row['Erstdiagnose Datum'], '%d.%m.%Y')
                censoring_date = datetime.strptime(row['Datum definitives Schicksal'], '%d.%m.%Y') - pd.Timedelta(365, "days")
                if (censoring_date-first_diagnosis).days / 365 < MINIMUM_LIFETIME:
                    filter_reason["short"] += 1
                    continue
            elif censoring_type == 1:
                first_diagnosis = datetime.strptime(row['Erstdiagnose Datum'], '%d.%m.%Y')
                censoring_date = datetime.strptime(row['Datum definitives Schicksal'], '%d.%m.%Y')
                if (censoring_date - first_diagnosis).days / 365 < MINIMUM_LIFETIME:
                    filter_reason["short"] += 1
                    continue
            elif censoring_type == 2:
                censoring_date = datetime.strptime(row['Datum AML-Transformation'], '%d.%m.%Y')

            # exclude patients with missing constant features
            if row['Blasten im KM % ED'] == '':
                #filter_reason["blast/karyo"] += 1
                #continue
                blasten = None
            else:
                blasten = float(row['Blasten im KM % ED'].replace(",", "."))
            if row['Karyotyp nach IPSS-R Code ED'] in ['', '5']:
                karyotyp = None
            else:
                karyotyp = int(row['Karyotyp nach IPSS-R Code ED'])
            # exclude patients with missing ipssr
            #if row['IPSS-R Code ED'] == '':
            #    filter_reason["ipssr_missing"] += 1
            #    continue

            age = row['Alter bei ED Jahre']
            if age == '':
                birthday = datetime.strptime(row['Geburtsdatum'], '%d.%m.%Y')
                first_diagnosis = datetime.strptime(row['Erstdiagnose Datum'], '%d.%m.%Y')
                age = (first_diagnosis - birthday).days / 365
            else:
                age = float(age.replace(",", "."))
            patient_data = {
                "id": row['ID'],
                "cis_id": row['Meddat ID'],
                "age": age,
                "gender": int(row['Geschlecht'] == 'm'),
                "blasts": blasten,
                "cyto": karyotyp,
                "birthdate": row['Geburtsdatum'],
                "diagnosis_date": row['Erstdiagnose Datum'],
                "censoring_date": censoring_date.strftime("%d.%m.%Y"),
                "censoring_type": censoring_type,
                #"ipssr": int(row['IPSS-R Code ED'])
            }


            ids.append(row['Meddat ID'])
            # safe complete row for user output
            rows.append(patient_data)
    print(filter_reason)
    print("Patients left after filtering:", len(ids))

    with open(snakemake.output[0], "w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with open(snakemake.output[1], "w", newline="") as meddat_ids_output:
        writer = csv.writer(meddat_ids_output)
        for id in ids: writer.writerow([id])



filter_patients(snakemake.input[0], snakemake.input[1])
