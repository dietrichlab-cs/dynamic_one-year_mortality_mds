import csv
import os
import shutil
from datetime import datetime

import numpy as np

def generate_stats(dataset_name, patient):
    with open(os.path.normpath(dataset_name + "/stats/" + patient.split("/")[-1]), "w", newline='') as stat_file:
        writer = csv.writer(stat_file)
        writer.writerow(["start", "end", "time_span", "entries"])

        with open(patient, "r") as csv_file:
            reader = csv.reader(csv_file)
            rows = [row for row in reader]
            try:
                start = datetime.strptime(rows[1][0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                start = datetime.strptime(rows[1][0], '%Y-%m-%d')
            try:
                end = datetime.strptime(rows[-1][0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                end = datetime.strptime(rows[-1][0], '%Y-%m-%d')

            writer.writerow([start, end, end - start, len(rows)])

# mainly gather information
def analyse_data(patient, dataset_name, patient_meta_file, label_output):
    with open(patient_meta_file) as meta_file:
        meta_reader = csv.DictReader(meta_file)
        with open(label_output, "w", newline='') as label_file:
            writer = csv.writer(label_file)
            writer.writerow(["Patient", "Medico", "lifetime", "diagnosis",
                             "First observation", "event",  "Last observation", "difference_start", "difference_death",
                             "entries", "span", "alive"])
            for row in meta_reader:
                if row['cis_id'] == patient.split("/")[-1][:-4]:
                    last_observation, first_observation = None, None
                    entries = 0
                    obs_duration = None
                    with open(os.path.normpath(dataset_name + "/stats/" + row['cis_id'] + ".csv")) as stats_file:
                        stats_reader = csv.DictReader(stats_file)
                        for stat_row in stats_reader:
                            last_observation = datetime.strptime(stat_row['end'], '%Y-%m-%d %H:%M:%S')
                            first_observation = datetime.strptime(stat_row['start'], '%Y-%m-%d %H:%M:%S')
                            entries = int(stat_row['entries'])
                            obs_duration = last_observation - first_observation

                    first_diagnosis = datetime.strptime(row['diagnosis_date'], '%d.%m.%Y')
                    event = datetime.strptime(row['censoring_date'], '%d.%m.%Y')
                    status = int(row['censoring_type'])
                    # if the patient is still alive but just right censored, set the time of event to the newest measured value.
                    # This is fine since the patient had to be alive for the measurement to take place and we can update the date accordingly
                    if status == 0:
                        event = max(event, last_observation)

                    # it can happen, that there are observations for patients after the event
                    difference_obs_end_death = (event - last_observation).days

                    lifetime = event - first_diagnosis
                    # write all stats to a csv file
                    writer.writerow([row['id'], row['cis_id'], lifetime.days, first_diagnosis, first_observation, event,
                                    last_observation, (first_observation-first_diagnosis).days, difference_obs_end_death , entries, obs_duration.days, 1 - status])



generate_stats(snakemake.params[0], snakemake.input[1])
analyse_data(snakemake.input[1], snakemake.params[0], snakemake.input[0], snakemake.output[0])
