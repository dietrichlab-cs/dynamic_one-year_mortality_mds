## Overview

This repository cotains all code for the related publication titled "Dynamic Mortality Risk Prediction in Myelodysplastic Syndromes Using Longitudinal Clinical Data" by Bobak et al. 
The "publication" branch contains all plots and code related to the generation of results for the paper. 
The "webapp" branch contains the sample application avavailable here: (https://dietrichlab.de/PythonApps/dynamic_mds_paper/)[https://dietrichlab.de/PythonApps/dynamic_mds_paper/]
NOTE: This web-application is purely for research purposes. 

### Pipeline

The pipeline is managed using snakemake. There are different pipelines for the three datasets. For the Düsseldorf dataset, there is a pipeline creating the feature matrix and all necessary data called `Snakefile_no_filter`. This was run first. Next the `Snakefile_training_only` pipeline trains the longitudinal and baseline model on the Düsseldorf dataset. 

For the Mannheim cohort we ran the `Snakefile_mannheim` pipeline
