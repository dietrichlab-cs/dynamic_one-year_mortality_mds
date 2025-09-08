
"""
Test that no features get extracted, when only one data-point is present
"""
from datetime import datetime

import pandas as pd

from scripts_dynamic_survival.time_series_feature_extractor import Feature_Extractor


def test_case_1():
    output_csv = "output/dd_1.csv"
    extractor = Feature_Extractor(365,3,20)
    extractor.generate_subseries("dummy_data/dd_label.csv","dummy_data/dd_1_raw_data.csv", output_csv)
    result = pd.read_csv(output_csv)
    assert "Excluded" in result.columns

def test_case_2():
    output_csv = "output/dd_2.csv"
    extractor = Feature_Extractor(365,3,20)
    extractor.generate_subseries("dummy_data/dd_label.csv","dummy_data/dd_2_raw_data.csv", output_csv)
    result = pd.read_csv(output_csv, index_col="Unnamed: 0")
    assert "Excluded" not in result.columns
    assert "dd_2_raw_data.0" in result.index
    assert result.loc["dd_2_raw_data.0", "HB304_last_values"] == 3
    assert result.loc["dd_2_raw_data.0", "ERY303_last_values"] == 2
    assert result.loc["dd_2_raw_data.0", "label"] == 0
    assert result.loc["dd_2_raw_data.0", "time_to_event"] == 728
    assert result.loc["dd_2_raw_data.0", "window"] == 3

def test_case_3():
    output_csv = "output/dd_3.csv"
    extractor = Feature_Extractor(365,3,20)
    extractor.generate_subseries("dummy_data/dd_label.csv","dummy_data/dd_3_raw_data.csv", output_csv)
    result = pd.read_csv(output_csv, index_col="Unnamed: 0")
    assert "Excluded" not in result.columns
    assert all(ind in result.index for ind in ["dd_3_raw_data.0", "dd_3_raw_data.1"])
    assert result.loc["dd_3_raw_data.0", "HB304_last_values"] == 3
    assert result.loc["dd_3_raw_data.0", "ERY303_last_values"] == 2
    assert result.loc["dd_3_raw_data.0", "label"] == 0
    assert result.loc["dd_3_raw_data.0", "time_to_event"] == 728
    assert result.loc["dd_3_raw_data.0", "window_length"] == 3
    assert result.loc["dd_3_raw_data.0", "quarters"] == 1
    assert result.loc["dd_3_raw_data.1", "ERY303_last_values"] == 5
    assert result.loc["dd_3_raw_data.1", "label"] == 1
    assert result.loc["dd_3_raw_data.1", "time_to_event"] == 31
    assert result.loc["dd_3_raw_data.1", "window_length"] == 700
    assert result.loc["dd_3_raw_data.1", "quarters"] == 8

def test_case_4():
    output_csv = "output/dd_4.csv"
    extractor = Feature_Extractor(365,3,20)
    extractor.generate_subseries("dummy_data/dd_label_alive.csv","dummy_data/dd_4_raw_data.csv", output_csv)
    result = pd.read_csv(output_csv, index_col="Unnamed: 0")
    assert "Excluded" not in result.columns
    assert all(ind in result.index for ind in ["dd_4_raw_data.0"])
    assert all(ind not in result.index for ind in ["dd_4_raw_data.1"])
    assert result.loc["dd_4_raw_data.0", "HB304_last_values"] == 3
    assert result.loc["dd_4_raw_data.0", "ERY303_last_values"] == 2
    assert result.loc["dd_4_raw_data.0", "label"] == 0
    assert result.loc["dd_4_raw_data.0", "time_to_event"] == 728
    assert result.loc["dd_4_raw_data.0", "window_length"] == 3
    assert result.loc["dd_4_raw_data.0", "quarters"] == 1

def test_case_5():
    output_csv = "output/dd_5.csv"
    extractor = Feature_Extractor(365,3,20)
    extractor.generate_subseries("dummy_data/dd_label.csv","dummy_data/dd_5_raw_data.csv", output_csv)
    result = pd.read_csv(output_csv, index_col="Unnamed: 0")
    assert "Excluded" not in result.columns
    assert all(ind in result.index for ind in ["dd_5_raw_data.0", "dd_5_raw_data.1"])
    assert all(ind not in result.index for ind in [])
    assert result.loc["dd_5_raw_data.0", "HB304_last_values"] == 3
    assert result.loc["dd_5_raw_data.0", "ERY303_last_values"] == 2
    assert result.loc["dd_5_raw_data.0", "label"] == 0
    assert result.loc["dd_5_raw_data.0", "time_to_event"] == 577
    assert result.loc["dd_5_raw_data.0", "window_length"] == 154
    assert result.loc["dd_5_raw_data.0", "quarters"] == 2
    assert result.loc["dd_5_raw_data.1", "ERY303_last_values"] == 5
    assert result.loc["dd_5_raw_data.1", "label"] == 1
    assert result.loc["dd_5_raw_data.1", "time_to_event"] == 31
    assert result.loc["dd_5_raw_data.1", "window_length"] == 700
    assert result.loc["dd_5_raw_data.1", "quarters"] == 8

def test_case_6():
    output_csv = "output/dd_6.csv"
    extractor = Feature_Extractor(365,3,20)
    extractor.generate_subseries("dummy_data/dd_label.csv","dummy_data/dd_6_raw_data.csv", output_csv)
    result = pd.read_csv(output_csv, index_col="Unnamed: 0")
    assert "Excluded" not in result.columns
    assert all(ind in result.index for ind in ["dd_6_raw_data.0", "dd_6_raw_data.1"])
    assert all(ind not in result.index for ind in [])
    assert result.loc["dd_6_raw_data.0", "HB304_last_values"] == 3
    assert result.loc["dd_6_raw_data.0", "ERY303_last_values"] == 2
    assert result.loc["dd_6_raw_data.0", "label"] == 0
    assert result.loc["dd_6_raw_data.0", "time_to_event"] == 549
    assert result.loc["dd_6_raw_data.0", "window_length"] == 182
    assert result.loc["dd_6_raw_data.0", "quarters"] == 3
    assert result.loc["dd_6_raw_data.1", "ERY303_last_values"] == 5
    assert result.loc["dd_6_raw_data.1", "label"] == 1
    assert result.loc["dd_6_raw_data.1", "time_to_event"] == 31
    assert result.loc["dd_6_raw_data.1", "window_length"] == 700
    assert result.loc["dd_6_raw_data.1", "quarters"] == 8

def test_case_7():
    output_csv = "output/dd_7.csv"
    index_name = "dd_7_raw_data"
    extractor = Feature_Extractor(365,3,20)
    extractor.generate_subseries("dummy_data/dd_label_alive.csv","dummy_data/" + index_name + ".csv", output_csv)
    result = pd.read_csv(output_csv, index_col="Unnamed: 0")
    assert "Excluded" not in result.columns
    assert all(ind in result.index for ind in [index_name + ".0"])
    assert all(ind not in result.index for ind in [index_name + ".1"])
    assert result.loc[index_name + ".0", "HB304_last_values"] == 3
    assert result.loc[index_name + ".0", "ERY303_last_values"] == 2
    assert result.loc[index_name + ".0", "label"] == 0
    assert result.loc[index_name + ".0", "time_to_event"] == 549
    assert result.loc[index_name + ".0", "window_length"] == 182
    assert result.loc[index_name + ".0", "quarters"] == 3


def test_case_8():
    output_csv = "output/dd_8.csv"
    index_name = "dd_8_raw_data"
    extractor = Feature_Extractor(365,3,20)
    extractor.generate_subseries("dummy_data/dd_label_long_living.csv","dummy_data/" + index_name + ".csv", output_csv)
    result = pd.read_csv(output_csv, index_col="Unnamed: 0")
    assert "Excluded" not in result.columns
    assert all(ind in result.index for ind in [index_name + ".0", index_name + ".1"])
    assert all(ind not in result.index for ind in [index_name + ".2"])
    assert result.loc[index_name + ".0", "HB304_last_values"] == 3
    assert result.loc[index_name + ".0", "ERY303_last_values"] == 2
    assert result.loc[index_name + ".0", "label"] == 0
    assert result.loc[index_name + ".0", "time_to_event"] == 11506
    assert result.loc[index_name + ".0", "window_length"] == 182
    assert result.loc[index_name + ".0", "quarters"] == 3
    assert result.loc[index_name + ".1", "HB304_last_values"] == 6
    assert result.loc[index_name + ".1", "ERY303_last_values"] == 6
    assert result.loc[index_name + ".1", "label"] == 0
    assert result.loc[index_name + ".1", "time_to_event"] == 10969
    assert result.loc[index_name + ".1", "window_length"] == 719
    assert result.loc[index_name + ".1", "quarters"] == 8

if __name__ == '__main__':
    #test_case_1()
    #test_case_2()
    #test_case_3()
    #test_case_4()
    #test_case_5()
    #test_case_6()
    #test_case_7()
    test_case_8()