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
        fieldnames = ["id", "cis_id", "age", "gender", "blasts", "cyto", "easix", "birthdate", "diagnosis_date", "censoring_date", "censoring_type"]
        filter_reason = defaultdict(int)
        for row in reader:
            # only include patients with first diagnosis date and cis id
            if row['DWH_Erst_Datum'] == '' or row['PATNR'] == '' or row['Geburtsdatum'] == '':
                filter_reason["diagnosis, cid id or bd empty"] += 1
                continue

            # check if a patient lived more than MINIMUM_LIFETIME years -> if so we can add the living patient with label
            # "lived longer than 5 years"
            if row['Todesdatum'] == '':
                first_diagnosis = datetime.strptime(row['DWH_Erst_Datum'], '%d.%m.%Y')
                last_fate = datetime.strptime(row['Letzter_Kontakt'], '%d.%m.%Y')
                if (last_fate-first_diagnosis).days / 365 < MINIMUM_LIFETIME:
                    filter_reason["short"] += 1
                    continue

            # exclude patients with missing constant features
            if row['LTFE_KM_MYELOBLASTEN'] == '':
                #filter_reason["blast/karyo"] += 1
                #continue
                blasten = None
            else:
                blasten = float(row['LTFE_KM_MYELOBLASTEN'].replace(",", "."))

            if row['Karyotyp nach IPSS-R'] in ['', '5']:
                karyotyp = None
            else:
                karyotyp = int(row['Karyotyp nach IPSS-R'])
            # exclude patients with missing ipssr
            #if row['IPSS-R Code ED'] == '':
            #    filter_reason["ipssr_missing"] += 1
            #    continue
            easix = float(row['easix'].replace(",", ".")) if row['easix'] else None

            birthday = datetime.strptime(row['Geburtsdatum'], '%d.%m.%Y')
            first_diagnosis = datetime.strptime(row['DWH_Erst_Datum'], '%d.%m.%Y')
            age = (first_diagnosis - birthday).days / 365
            patient_data = {
                "id": row['ID'],
                "cis_id": row['PATNR'],
                "age": age,
                "gender": int(row['Geschlecht'] == 'm'),
                "blasts": blasten,
                "cyto": karyotyp,
                "easix": easix,
                "birthdate": row['Geburtsdatum'],
                "diagnosis_date": row['DWH_Erst_Datum'],
                "censoring_date": row['Letzter_Kontakt'] if row['Todesdatum'] == '' else row['Todesdatum'],
                "censoring_type": int(row['Todesdatum'] != ''),
                #"ipssr": int(row['IPSS-R Code ED'])
            }


            ids.append(row['PATNR'])
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
