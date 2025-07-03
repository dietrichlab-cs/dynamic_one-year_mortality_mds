## Overview

This repository cotains all code for the related publication titled "Dynamic Mortality Risk Prediction in Myelodysplastic Syndromes Using Longitudinal Clinical Data" by Bobak et al. 

The "publication" branch contains all plots and code related to the generation of results for the paper. Code in here is provided to make results reproducible and to allow for further analysis of the data. 
You should be able to get the exact same results as the publication given the same input data or may try to adapt the pipeline to your own data. 
The second part is not the main focus of this repository, but we provide the code to allow for it. Note that due to differing data formats you may need to adapt the code to your own data, see section "Run and train on your own data" below for more information.

The "webapp" branch contains the sample application avavailable here: https://dietrichlab.de/PythonApps/dynamic_mds_paper/
NOTE: This web-application is purely for research purposes.


### Pipeline

The pipeline is managed using snakemake. There are different pipelines for the three datasets. For the Düsseldorf dataset, there is a pipeline creating the feature matrix and all necessary data called `Snakefile_no_filter`. This was run first. Next the `Snakefile_training_only` pipeline trains the longitudinal and baseline model on the Düsseldorf dataset. 

For the Mannheim cohort we ran the `Snakefile_mannheim` pipeline which does generate a file called `metrics_mannheim.txt` containing the results of the Mannheim cohort.
For the Heidelberg cohort we ran the `Snakefile_mannheim` pipeline which does generate a file called `metrics_heidelberg.txt` containing the results of the Heidelberg cohort.
For the cross-validation on the Düsseldorf dataset run the `scripts_no_filter/classficiation.py` script. 

### Run and train on your own data

If you want to run the code on your own data, you can use the `Snakefile_no_filter` pipeline to generate the feature matrix and then use the `Snakefile_training_only` pipeline to train the models.
You do need to adapt the `Snakefile_no_filter` to your own data, especially the `DATASET_DIR` variable at the top of the file.
In addition:

#### Adjust the `filter_patients.py` script. 
Change the names of input features according to your data. This script transforms all the baseline features and metadata annotations into a standard dataframe format. 
You need the following columns: 
- `id`: Unique identifier for each patient
- `cis_id`: Unique identifier for each patient in the CIS database relating the diagnosis data to the longitudinal lab data
- `diagnosis_date`: Date of diagnosis
- `event_date`: Date of the event (e.g. death, last follow-up)
- `event`: Event type (e.g. death, alive on last follow-up), 2 = death, 0 = alive 
- `age`: Age of the patient at diagnosis
- `gender`: Gender of the patient
- `blasts`: Percentage of blasts in the bone marrow at diagnosis
- `cyto`: Cytogenetic risk group of the patient at diagnosis according to the IPSS-R (e.g. good, intermediate, poor) coded as 0-very good to 4-very poor
Optional:
- `alloHSCT`: Whether the patient received an allogeneic stem cell transplant, you need to filter them out if not done already
- `birthdate`: Date of birth of the patient, this is used to calculate the age at diagnosis if not provided

#### Adjust the `extract_ts_patient_data.py` script. 
This script extracts the longitudinal data for each patient and transforms it into a standard dataframe format. For us this involved scanning through different files.
If you already have your data as one file per patient according to the format of the webapp with the diagnosis date as the first row and the event date as the last row, you can skip this step in theory. 
Here is an example raw_data file: 
```
date,Leukozyten,Erythrozyten,Hämatokrit,Thrombozyten,Hämoglobin
1997-02-25 00:00:00,,,,, -> this is the diagnosis date
1997-04-01 00:00:00,1.3,2.2,23.5,56.0,8.1
1997-04-04 00:00:00,1.2,2.67,26.7,70.0,8.9
1997-05-11 00:00:00,0.7,2.13,22.0,61.0,7.2
1997-06-12 00:00:00,1.2,2.81,27.2,49.0,9.3
1997-07-14 00:00:00,0.9,2.83,27.3,50.0,9.3
1997-08-24,,,,, -> this is the event data
```
If you already have data at diagnosis or event date you do not need to add them as additional first or last rows. If you have multiple datapoints at a single day, use the minutes and seconds to differentiate them. The index has to be unique. 
In the end you need a single raw_data file per patient.

#### Rest of the pipeline

The rest of the pipeline should work as is. The `Snakefile_no_filter` will generate a feature matrix and the `Snakefile_training_only` will train the models on the generated feature matrix.

### Output

All output of the above pipelines will be stored inside the `DATASET_DIR` defined in the snakefiles. For the individually run `classification.py` scripts, you can also modify the output directory within the first lines of the scripts. 

### Static scripts

In the folder `static_scripts` you can find scripts that are used to generate static plots and results. These are not part of the snakemake pipeline, can be run individually but may depend on outputs from the different pipelines.

## Questions

If you want to use the code or have questions feel free to open issues or contact Jonathan Bobak (jonathan.bobak@med.uni-duesseldorf.de)
