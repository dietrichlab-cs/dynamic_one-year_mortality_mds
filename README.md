## Raw code used for publication

Code on this branch is the raw code used for the publication titled "Dynamic Mortality Risk Prediction in Myelodysplastic Syndromes Using Longitudinal Clinical Data" by Bobak et al.

It is not intended to be run as is, but rather to be used as a reference for the methods and analyses described in the publication.
For cleaned and user-friendly code, please refer to the `publication` branch or test the models using the webapp described on the `webapp` branch.

### Overview

The repository is structured into 4 main parts. One code pipeline for each dataset used in the publication. So Düsseldorf for training and cross-validation, Mannheim and Heidelberg for external validation.
Additionally, there are so-called static scripts that are used to generate the static figures and tables in the publication. For the AML comparison on the Düsseldorf dataset we got two additional pipeline with the `_aml` suffix.

All code may be run using the provided snakemake pipelines. 

### Running the pipeline

Select one of the Snakefiles and run it using the `snakemake --snakefile <Snakefile> --cores <n_cpus> -R all` script. 
For the Heidelberg and Mannheim pipelines, you need the pre-trained models on the Düsseldorf dataset as pre-requisits from the `training_pipeline`.
The Heidelberg pipeline will also run the classification while all other pipelines only build the required feature matrices. 
To run classification evaluation on these pipelines, run the respective `classification.py` script manually with the desired parameters and inputs. 
The `training_pipeline` does not feature an evaluation script. 

