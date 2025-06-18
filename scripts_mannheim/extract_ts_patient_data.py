import csv
import datetime
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

UNKNOWN = ['km', 'h.muebs', 'zwm=', 'häm', 'su', '...', 'sk', 'ff', 'ger', '~', 'MUEBS', '.',
           'ag', 'fm', 'zwm', 'esto', 'ent', 'ea', 'kma', 'h0', '              <6']
MINIMUM_ENTRIES = snakemake.params[3]
OUTPUT_DIR = snakemake.params[2]

def load_patients(id_file):
    patients = {}
    with open(id_file, "r") as ids_csv:
        reader = csv.DictReader(ids_csv)
        for row in reader:
            patients[row['cis_id']] = [datetime.strptime(row['diagnosis_date'], '%d.%m.%Y'),
                                          datetime.strptime(row['censoring_date'], '%d.%m.%Y')]
    return patients


def build_patient_data(patients, dataset_parameters, alias_parameter, data_files):
    os.mkdir(OUTPUT_DIR + "/raw_data")

    total_entries = 0
    total_input_files = len(data_files)
    current_input_file = 0
    entries = defaultdict(lambda: defaultdict(list))
    alias = {}
    for a in alias_parameter:
        alias[a.split("_")[0]] = a.split("_")[1]
    print("Alias mappings:", alias)
    for file in data_files:
        with open(file, encoding="UTF-8") as data_file:
            reader = csv.DictReader(data_file, delimiter=',')
            for row in reader:
                # combine Analyt name and number into a unique key
                parameter_name = row['Verfahrensname']
                # get the cis ID of the current row
                cis_id = row['Lebensnummer']
                if cis_id not in patients.keys():
                    continue
                # if the parameter or the patient is not in the respective predetermined sets, skip the row
                if parameter_name not in dataset_parameters and parameter_name not in alias.keys():
                    continue
                # skip entries that where taken before MDS diagnosis
                if datetime.strptime(row['Auftragsdatum'], '%Y-%m-%d') < patients[row['Lebensnummer']][0]:
                    continue
                # if the entry contains < or > then we can replace it by the respective upper or lower limit
                # there are two cases for this: Leukocytes < 0.1 * 1000 mu_l and platelets < 1 * 1000 mu_l
                if row['Ergebnis'] == "":
                    continue
                if row['Ergebnis'][0] in ['>', '<']:
                    value = row['Ergebnis'].replace(">", "").replace("<", "")
                else:
                    try: float(row['Ergebnis'].replace(",", "."))
                    except:
                        continue
                    value = row['Ergebnis'].replace(",", ".")
                # get the examination date
                examination_date = datetime.strptime(row['Auftragsdatum'], '%Y-%m-%d')
                # append info for entry using the patient and parameter identifier
                if parameter_name in alias:
                    #print("Found alias parameter", parameter_name, alias[parameter_name], value)
                    entries[cis_id][alias[parameter_name]].append([examination_date, value])
                else:
                    entries[cis_id][parameter_name].append([examination_date, value])
        current_input_file += 1
        print('File progress: {:d}/{:d} - {:.2f} %'.format(current_input_file, total_input_files,
                                                           (current_input_file / total_input_files) * 100))
        #sys.stdout.write("\033[F")
    print()
    processed_patients = 0
    # gather entries and group them by patient
    for patient in entries.keys():
        # if there are no entries for one parameter, skip the patient
        if len(entries[patient]) < len(dataset_parameters):
            print("Length mismatch for patient:", patient, entries[patient].keys(), len(dataset_parameters))
            continue
            # continue
        # init the dataframe holding the entries with the examination dates as keys
        data_df = pd.DataFrame(columns=['date'])
        data_df = data_df.set_index('date')
        start, end = None, None
        # process each parameter on its own
        for parameter in entries[patient].keys():
            cur_param_data = []
            # sort the entries for one parameter by their examination date
            entries[patient][parameter].sort(key=lambda x: x[0])
            # check if the first entry for the parameter is the global minimal or maximal entry date
            if start is None or entries[patient][parameter][0][0] < start: start = entries[patient][parameter][0][0]
            if end is None or entries[patient][parameter][-1][0] > end: end = entries[patient][parameter][-1][0]
            # if the first entry for this parameter is after the first diagnosis, add the first diagnosis as a blank entry
            if entries[patient][parameter][0][0] > patients[patient][0]:
                cur_param_data.append((patients[patient][0], np.float64(np.nan)))
            # for each entry, add it to the list of entries. If multiple measurements are associated with one day, offset them by one minute
            for value in entries[patient][parameter]:
                if len(cur_param_data) > 0 and value[0].date() == cur_param_data[-1][0].date():
                    value[0] = cur_param_data[-1][0] + timedelta(minutes=1)
                cur_param_data.append((value[0], np.float64(value[1])))
            # if the last entry if before the event, add the event time as a blank entry
            if cur_param_data[-1][0] < patients[patient][1]:
                cur_param_data.append((patients[patient][1], np.float64(np.nan)))
            # convert list of entries to dataframe
            param_df = pd.DataFrame(cur_param_data, columns=['date', dataset_parameters[parameter]]).set_index('date')
            # add the current parameter as a new column. Index sets are merged
            data_df = pd.concat([data_df, param_df], axis=1)

        # write the complete dataframe to a csv file
        with open(OUTPUT_DIR + "/raw_data/" + patient + ".csv", "w", newline='', encoding="UTF-8") as data_output:
            data_df.to_csv(data_output)
        processed_patients += 1
    print("Finished with", processed_patients)


    with open(OUTPUT_DIR + "/stats.csv", "w", newline='') as stats_file:
        writer = csv.writer(stats_file)
        writer.writerow(["Patients", "Parameters", "Average entries per patient"])
        writer.writerow([processed_patients, len(dataset_parameters), total_entries / processed_patients])


def write_debug(debug_file, dataset_parameters):
    with open(debug_file, "a+") as debug_file:
        debug_file.write("Parameter für dataset mit {:d} Parametern\n".format(len(dataset_parameters)))
        for p in dataset_parameters:
            debug_file.write("Abkürzung: " + p[0] + "\n")


patients = load_patients(snakemake.input[0])
build_patient_data(patients, snakemake.params[0], snakemake.params[1], snakemake.input[1:])
os.mkdir(OUTPUT_DIR + "/stats")
#write_debug(snakemake.output[1], snakemake.params[0])

