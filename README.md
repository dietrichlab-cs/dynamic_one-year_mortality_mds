## Raw code used for publication

Code on this branch is the raw code used for the publication titled "Dynamic Mortality Risk Prediction in Myelodysplastic Syndromes Using Longitudinal Clinical Data" by Bobak et al.

It is not intended to be run as is, but rather to be used as a reference for the methods and analyses described in the publication.
For cleaned and user-friendly code, please refer to the `publication` branch or test the models using the webapp described on the `webapp` branch.

### Overview

The repository is structured into 4 main parts. One code pipeline for each dataset used in the publication. So Düsseldorf for training and cross-validation, Mannheim and Heidelberg for external validation.
Additionally, there are so-called static scripts that are used to generate the static figures and tables in the publication.

All code may be run using the provided snakemake pipelines. 
