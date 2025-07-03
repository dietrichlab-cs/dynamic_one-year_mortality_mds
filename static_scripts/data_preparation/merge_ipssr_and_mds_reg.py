import csv

def merge_csv_files():
    ipssr_reader = csv.DictReader(open("../../data/publication_ipssr/calculated_ipssr_publication.csv", "r", encoding="utf-8"), delimiter=",")
    mds_registry_reader = csv.DictReader(open("../../data/publication_ipssr/mds_register_publication.csv", "r", encoding="utf-8-sig"), delimiter=";")

    patients = {}
    for row in ipssr_reader:
        patients[row['ID']] = row

    for row in mds_registry_reader:
        if row["ID"] in patients.keys():
            #print(patients[row['ID']])
            patients[row['ID']].update(row)

    header = ipssr_reader.fieldnames
    header.extend(x for x in mds_registry_reader.fieldnames if x not in header)
    print(header)
    writer = csv.DictWriter(open("../../data/publication_ipssr/constant_parameter.csv", "w", encoding="utf-8", newline=""), fieldnames=header)
    writer.writeheader()
    for p in patients.keys():
        writer.writerow(patients[p])

if __name__ == "__main__":
    merge_csv_files()