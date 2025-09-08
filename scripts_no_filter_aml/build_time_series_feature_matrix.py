from scripts_no_filter.time_series_feature_extractor import Feature_Extractor

extractor = Feature_Extractor(snakemake.params[0], snakemake.params[1], snakemake.params[2])
extractor.generate_subseries(snakemake.input[0], snakemake.input[1], snakemake.output[0])
