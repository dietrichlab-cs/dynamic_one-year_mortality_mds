import csv
from collections import defaultdict
from datetime import datetime


MINIMUM_LIFETIME = snakemake.params[0]

def filter_patients(input_file, error_file=None):
    ids = []
    rows = []
    error_ids = []
    if error_file is not None:
        with open(error_file) as error_csv:
            reader = csv.reader(error_csv)
            for row in reader:
                error_ids.append(row[0])

    with open(input_file, encoding='UTF-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        fieldnames = ["id", "cis_id", "age", "gender", "blasts", "cyto", "birthdate", "diagnosis_date", "censoring_date", "censoring_type"]
        filter_reason = defaultdict(int)
        for row in reader:
            # only include patients with first diagnosis date and cis id
            if row['Erstdiagnose Datum'] == '' or row['iMED Lebensnr.'] == '' or row['Geburtsdatum'] == '':
                filter_reason["diagnosis, cid id or bd empty"] += 1
                continue
            # skip patients that got a stem cell transplantation
            if not (row['Einteilung KMT/SCT (alt) Code 1'] in ['0', '']):
                filter_reason["KMT"] += 1
                continue
            # skip patients who might have only the date for the sct date set (they might not have gotten an SCT but just to be sure)
            if row['Datum SCT 1'] != '':
                filter_reason["KMT_date"] += 1
                continue
            # skip patients which are lost to follow-up
            if row['Definitives Schicksal Code'] in ['', '1']:
                filter_reason["Fate"] += 1
                continue
            # Exclude patients with no definitive date
            if row['Datum definitives Schicksal'] == '':
                filter_reason["Fate_date"] += 1
                continue
            # check if a patient lived more than MINIMUM_LIFETIME years -> if so we can add the living patient with label
            # "lived longer than 5 years"
            if row['Definitives Schicksal Code'] == '0':
                first_diagnosis = datetime.strptime(row['Erstdiagnose Datum'], '%d.%m.%Y')
                last_fate = datetime.strptime(row['Datum definitives Schicksal'], '%d.%m.%Y')
                if (last_fate-first_diagnosis).days / 365 < MINIMUM_LIFETIME:
                    filter_reason["short"] += 1
                    continue
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
                "cis_id": row['iMED Lebensnr.'],
                "age": age,
                "gender": int(row['Geschlecht'] == 'm'),
                "blasts": blasten,
                "cyto": karyotyp,
                "birthdate": row['Geburtsdatum'],
                "diagnosis_date": row['Erstdiagnose Datum'],
                "censoring_date": row['Datum definitives Schicksal'],
                "censoring_type": int(row['Definitives Schicksal Code']),
                #"ipssr": int(row['IPSS-R Code ED'])
            }


            ids.append(row['iMED Lebensnr.'])
            # safe complete row for user output
            rows.append(patient_data)
    print(filter_reason)
    print("Patients left after filtering:", len(ids))

    with open(snakemake.output[0], "w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with open(snakemake.output[1], "w", newline="") as cis_ids_output:
        writer = csv.writer(cis_ids_output)
        for id in ids: writer.writerow([id])



filter_patients(snakemake.input[0])
