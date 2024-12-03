import argparse
import numpy as np
import pandas as pd

#Author: nikhil153
#Date: 01-Dec-2024

time_col_type = "age" # change this if are not using age as time column

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to filter assessment visits based on MRI visit proximity
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument('--reference_assessment', type=str, help='path to reference assessment (typically the MRI)')
    parser.add_argument('--filter_assessment', type=str, help='path to assessment to be filtered')
    parser.add_argument('--index_columns', type=str, nargs='+', default=["participant_id", "redcap_event_name"],
                        help='index columns for reference and filter assessments')
    parser.add_argument('--reference_time_col', type=str, help='time (usuaally age) column name for reference assessment')
    parser.add_argument('--filter_time_col', type=str, help='time (usually age) column name for filter assessment')
    parser.add_argument('--output_file', type=str, default=None, help='path to output filtered csv')
    parser.add_argument('--window', type=int, help='window size in months')

    args = parser.parse_args()

    # read data
    df_A = pd.read_csv(args.reference_assessment)
    df_B = pd.read_csv(args.filter_assessment)
    index_cols = args.index_columns
    ref_time_col = args.reference_time_col
    filter_time_col = args.filter_time_col
    output_file = args.output_file
    window = args.window

    # default output file name
    if output_file is None:
        output_file = args.filter_assessment.replace(".csv", f"_filtered_{window}mo.csv")

    # Only two index columns are supported
    # Typically participant_id and visit_name
    n_index_cols = len(index_cols)
    if  n_index_cols > 2:
        print("Only up to 2 index columns are supported")
        exit()

    # filter assessment visits
    if time_col_type == "age":
        n_ref_participants = len(set(df_A[index_cols[0]]))
        n_filter_participants = len(set(df_B[index_cols[0]]))
        n_ref_visits = len(set(df_A[index_cols[1]]))
        n_filter_visits = len(set(df_B[index_cols[1]]))

        print("-"*80)
        print(f"Filtering {filter_time_col} assessment visits based on {ref_time_col} proximity")
        print(f"Reference assessment n_participants: {n_ref_participants}, n_visits: {n_ref_visits}")
        print(f"Filter assessment n_participants: {n_filter_participants}, n_visits: {n_filter_visits}")
        print(f"Using window size: {window} months")
        print("-"*60)
        df = pd.merge(df_A, df_B, on=index_cols, how='left')
        df["time_diff"] = 12 * (df[filter_time_col].astype(float) - df[ref_time_col].astype(float))
        proximal_ids_session = df[df["time_diff"].abs() <= window][index_cols].values
        n_proximal_participants = len(set(proximal_ids_session[:,0]))
        print(f"n_proximal (<={window} months) participants between {ref_time_col} <--> "
              f"{filter_time_col}: {n_proximal_participants}")
        print("-"*60)
        print(f"Saving filtered assessment visits to {output_file}")

        df_B_filtered = df_B.loc[df_B[index_cols[0]].isin(proximal_ids_session[:,0])]

        # filter again for visits
        if n_index_cols == 2:
            df_B_filtered = df_B_filtered.loc[df_B_filtered[index_cols[1]].isin(proximal_ids_session[:,1])]

        df_B_filtered.to_csv(output_file, index=False)

        print("-"*80)

    else:
        print(f"Time column type {time_col_type} not supported")
