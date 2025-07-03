

#if __name__ == '__main__':
#    generate_subseries("../data/output/survival2/dataset_less_params/labels/1001825_labels.csv", "../data/output/survival2/dataset_less_params/raw_data/1001825.csv", "../data/output/survival2/dataset_less_params/features/1001825_feature_matrix.csv")
from scripts_heidelberg.time_series_feature_extractor import Feature_Extractor

extractor = Feature_Extractor(snakemake.params[0], snakemake.params[1], snakemake.params[2])
extractor.generate_subseries(snakemake.input[0], snakemake.input[1], snakemake.output[0])
