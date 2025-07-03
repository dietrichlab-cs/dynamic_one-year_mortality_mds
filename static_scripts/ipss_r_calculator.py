import csv
from datetime import datetime
from time import sleep

import httpx
import pandas as pd

"""
With this script we can calculate the IPSS-R and the age-adjusted IPSS-R for all available patients. 
Before an online calculator is used to obtain the scores, a number of parameters are extracted and need to be available
"""

def calculate_ipssr():

    # read all patients and extract age (this can be done in multiple ways)
    reader = csv.DictReader(open("../data/old_data/constant_parameter.csv", "r", encoding="ISO-8859-1"))
    medico_to_mds_id = {}
    mds_ids = []
    ages = {}
    for row in reader:
        if row['Meddat ID'] == '': continue
        medico_to_mds_id[row['Meddat ID']] = row['ID']
        mds_ids.append(row['ID'])
        if row['Erstdiagnose Datum'] != "" and row['Geburtsdatum'] != "":
            ages[row['ID']] = (datetime.strptime(row['Erstdiagnose Datum'], "%d.%m.%Y") - datetime.strptime(row['Geburtsdatum'], "%d.%m.%Y")).days / 365
        elif row['Alter bei ED Jahre 1'] != "":
            ages[row['ID']] = float(row['Alter bei ED Jahre 1'])
        else:
            ages[row['ID']] = None

    # extract karyotype information from the cyto-genetic category
    cytogenetic_ipss = {}
    cyto_reader = csv.DictReader(open("../data/old_data/mds_register/zytogenetik_ed.csv", "r", encoding="utf-8-sig"), delimiter=";")
    for row in cyto_reader:
        if row['PatNum'] not in mds_ids: continue
        if row['ipssr_chrom'] not in ["", "6"]:
            cytogenetic_ipss[row['PatNum']] = row['ipssr_chrom']
        else:
            print(row['PatNum'], "cyto missing")
            cytogenetic_ipss[row['PatNum']] = None

    # extract lab information
    # some parameters can be obtained in multiple ways
    lab_ipss = {}
    lab_reader = csv.DictReader(open("../data/old_data/mds_register/labor_ed.csv", "r", encoding="utf-8-sig"), delimiter=";")
    count_missing = 0
    for row in lab_reader:
        if row['PatNum'] not in mds_ids: continue
        hb = row['Hb'].replace(",", ".")
        anc = row['ANCtotal'].replace(",", ".")
        pla = row['PLA'].replace(",", ".")
        if anc == "":
            stabk, segmentk, wbc = row['stabkern'], row['segmentk'], row['WBC']
            if stabk != "" and segmentk != "" and wbc != "":
                anc = (float(stabk.replace(",", ".")) + float(segmentk.replace(",", "."))) * float(wbc.replace(",", "."))
                #print("Calculated", anc)

        if hb == "" or anc == "" or pla == "":
            print(row['PatNum'], "missing lab values: HB", hb, "ANC", anc, "PLA", pla)
            lab_ipss[row['PatNum']] = None
            count_missing += 1
            continue

        if float(anc) < 15:
            anc = float(anc) * 1000
        lab_ipss[row['PatNum']] = (float(hb), float(anc)/1000, float(pla)/1000)

    # extract blast information
    km_ipss = {}
    km_reader = csv.DictReader(open("../data/old_data/mds_register/km_zyto_ed.csv", "r", encoding="utf-8-sig"), delimiter=";")
    for row in km_reader:
        if row['PatNum'] not in mds_ids: continue
        blasten = row['kmblasten']
        if blasten != "":
            km_ipss[row['PatNum']] = float(blasten.replace(",", "."))
        else:
            print(row['PatNum'], "missing Blasten")
            km_ipss[row['PatNum']] = None

    # the online calculator used is from the MDS Foundation
    request_URL = "https://www.mds-foundation.org/calculator_calc.php"
    cyto_category_mapper = {"0": 1, "1": 2, "2": 3, "3": 4, "4": 5}
    ipss_category_mapper = {"very low": 0, "low": 1, "intermediate": 2, "high": 3, "very high": 4}
    output_ipssr = pd.Series(name="IPSS-R_age", dtype=int)
    output_ipssr_no_age = pd.Series(name="IPSS-R", dtype=int)
    for patient in mds_ids:
        if patient not in cytogenetic_ipss.keys() or cytogenetic_ipss[patient] is None:
            print(patient, "skipped! Missing cytogenetics")
            continue
        if patient not in lab_ipss.keys() or lab_ipss[patient] is None:
            print(patient, "skipped! Missing lab")
            continue
        if patient not in km_ipss.keys() or km_ipss[patient] is None:
            print(patient, "skipped! Missing blasten")
            continue
        lab_values = lab_ipss[patient]

        # get the default IPSS-R
        params_without_age = {'cyca': cyto_category_mapper[cytogenetic_ipss[patient]], "hb": lab_values[0], "anc": lab_values[1],
                  "plt": lab_values[2], "bmb": km_ipss[patient]}
        r = httpx.get(url=request_URL, params=params_without_age)
        ipss_category = r.text.split("|")[1]
        output_ipssr_no_age[patient] = ipss_category_mapper[ipss_category]

        # get the age-adjusted IPSS-R
        if patient not in ages.keys() or ages[patient] is None:
            print(patient, "skipped! Missing age")
            continue
        params = {'cyca': cyto_category_mapper[cytogenetic_ipss[patient]], "hb": lab_values[0], "anc": lab_values[1], "plt": lab_values[2], "bmb": km_ipss[patient], "age": ages[patient]}
        r = httpx.get(url=request_URL, params=params)
        ipss_category = r.text.split("|")[1]
        output_ipssr[patient] = ipss_category_mapper[ipss_category]

        # wait 1 second before the next request as to not DDOS the calculator
        sleep(1)

    # join ipss_r and ipss_r_age_adjusted with constant parameter input from the MDS Register
    constant_parameter_df = pd.read_csv("../data/old_data/constant_parameter.csv", index_col="ID", dtype={'ID': str, 'MDS Typ Code': str, 'Meddat ID': str, 'IPSS-R Code ED':str, 'AML-Übergang Code 1': str, 'WHO-Klassifikation 2008 Code ED': str})
    constant_parameter_df = pd.merge(left=constant_parameter_df, right=output_ipssr, left_index=True, right_index=True, how="left")
    constant_parameter_df = pd.merge(left=constant_parameter_df, right=output_ipssr_no_age, left_index=True, right_index=True,
                                     how="left")
    constant_parameter_df.to_csv("../data/constant_parameter_with_ipssr.csv")



if __name__ == "__main__":
    calculate_ipssr()
