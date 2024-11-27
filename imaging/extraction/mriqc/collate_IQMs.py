import json
import argparse
import json
import logging
import os
import warnings
import pandas as pd


def get_qc_series(qc_json, datatype="anat"):
    """
    Extracts the IQM from the MRIQC JSON output
    """
    qc_df = pd.read_json(qc_json, orient="columns")

    if datatype == "anat":
        qc_cols_exact = ["cjv", "cnr", "efc", "fber"]
        qc_cols_prefix = ["fwhm", "summary", "icv", "inu", "snr", "tmp"]
    elif datatype == "func":
        qc_cols_exact = ["tsnr","snr","gcor","eft","fber"]
        qc_cols_prefix = ["fwhm", "summary", "fd", "gsr", "dvars"]
    else:
        raise ValueError(f"Invalid datatype: {datatype}")

    qc_cols = qc_cols_exact + qc_cols_prefix

    # selected_qc_cols = test_qc_df.columns[[test_qc_df.columns.str.contains(col) for col in qc_cols]]
    selected_qc_cols = []
    for col in qc_cols:
        _cols = list(qc_df.columns[qc_df.columns.str.contains(col)])
        selected_qc_cols += _cols

    qc_series = qc_df.iloc[0][selected_qc_cols]

    return qc_series

def run(pipeline_dir, bids_participants, session_id, run_id, datatype, output_dir):
    """
    Run the collate IQM script
    """
    qc_df = pd.DataFrame()
    for participant in bids_participants:
        if datatype == "anat":
            qc_json = f"{pipeline_dir}/sub-{participant}/ses-{session_id}/{datatype}/sub-{participant}_ses-{session_id}_run-{run_id}_T1w.json"
        elif datatype == "func":
            qc_json = f"{pipeline_dir}/sub-{participant}/ses-{session_id}/{datatype}/sub-{participant}_ses-{session_id}_task-rest_run-{run_id}_bold.json"
        else:
            raise ValueError(f"Invalid datatype: {datatype}")

        qc_series = get_qc_series(qc_json, datatype)

        qc_df = qc_df.append(qc_series, ignore_index=True)


    qc_df.to_csv(f"{output_dir}/{datatype}_IQM.csv", index=False)
    print(f"Collated IQM for {n_bids_participants} participants to {output_dir}")

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to collate IQM from MRIQC outputs for a given participant and session and run
    """

    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument('--dataset_root', type=str, help='path to the nipoppy dataset root')
    parser.add_argument('--participants_list', default=None, help='path to participants list (csv or tsv')
    parser.add_argument('--session_id', type=str, help='session id for the participant')
    parser.add_argument('--run_id', type=str, default="1", help='run id for the participant')
    parser.add_argument('--pipeline', type=str,default="mriqc", help='specify the pipeline to run')
    parser.add_argument('--pipeline_version', type=str, default="23.1.0", help='specify the pipeline version to run')
    parser.add_argument('--datatype', type=str, default="anat", help='specify the datatype to run (anat/func)')
    parser.add_argument('--output_dir', type=str, help='specify custom output directory')

    args = parser.parse_args()

    DATASET_ROOT = args.dataset_root
    session_id = args.session_id
    run_id = args.run_id
    participants_list = args.participants_list
    pipeline = args.pipeline
    pipeline_version = args.pipeline_version
    datatype = args.datatype
    output_dir = args.output_dir

    pipeline_dir = f"{DATASET_ROOT}/derivatives/{pipeline}/{pipeline_version}/output/"
    if output_dir == None:
        output_dir = f"{DATASET_ROOT}/derivatives/{pipeline}/{pipeline_version}/IDP/ses-{session_id}/"

    if participants_list == None:
        # use doughnut
        doughnut_file = f"{DATASET_ROOT}/sourcedata/imaging//doughnut.csv"
        doughnut_df = pd.read_csv(doughnut_file)
        doughnut_df["in_bids"] = doughnut_df["in_bids"].astype(bool)
        bids_participants = doughnut_df[(doughnut_df["session_id"]==session) & (doughnut_df["in_bids"])]["participant_id"].unique()
        n_bids_participants = len(bids_participants)
        print(f"Running all {n_bids_participants} participants in doughnut with session: ses-{session_id}")
    else:
        # use custom list
        bids_participants = list(pd.read_csv(participants_list)["participant_id"])

        n_bids_participants = len(bids_participants)
        print(f"Running {n_bids_participants} participants from the list with session: ses-{session_id}")

        run(pipeline_dir, bids_participants, session_id, run_id, datatype, output_dir)
