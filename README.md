## Overview

This repository cotains all code for the related publication titled "Dynamic Mortality Risk Prediction in Myelodysplastic Syndromes Using Longitudinal Clinical Data" by Bobak et al. 

The "publication" branch contains all plots and code related to the generation of results for the paper. Code in here is provided "as is" to have an accurate depiction of the code used to generate all results. We will add an additional branch in the future, containing cleaned and more user friendly code. 

The "webapp" branch contains the sample application avavailable here: https://dietrichlab.de/PythonApps/dynamic_mds_paper/
NOTE: This web-application is purely for research purposes. 


### Pipeline

The pipeline is managed using snakemake. There are different pipelines for the three datasets. For the Düsseldorf dataset, there is a pipeline creating the feature matrix and all necessary data called `Snakefile_no_filter`. This was run first. Next the `Snakefile_training_only` pipeline trains the longitudinal and baseline model on the Düsseldorf dataset. 

For the Mannheim cohort we ran the `Snakefile_mannheim` pipeline which does create the final feature matrix. To generate results. Run the `scripts_mannheim/classification.py` script.

For the Heidelberg cohort the `Snakefile_heidelberg` pipeline is an end-to-end federated approach. It does execute the `scripts_heidelberg/classification.py` already and generates all the results. 

For the cross-validation on the Düsseldorf dataset run the `scripts_no_filter/classficiation.py` script. 

### Output

All output of the above pipelines will be stored inside the `DATASET_DIR` defined in the snakefiles. For the individually run `classification.py` scripts, you can also modify the output directory within the first lines of the scripts. 

## Questions

If you want to use the code or have questions feel free to open issues or contact Jonathan Bobak (jonathan.bobak@med.uni-duesseldorf.de)
