import argparse
import glob
import json
import os
import shutil
import subprocess
import tarfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import nipoppy.workflow.catalog as catalog
import nipoppy.workflow.logger as my_logger
import numpy as np
import pandas as pd

#Author: nikhil153
#Date: 07-Oct-2022

fname = __file__
CWD = os.path.dirname(os.path.abspath(fname))

def find_mri(participant_ids):
    """ Finds, claims and parses MRI paths from the BIC dicom server
    """
    CMD = ["find_mri", "-claim", "-noconfir"] + participant_ids
    proc = subprocess.run(CMD,capture_output=True,text=True)
    proc_out = proc.stdout.strip().split('\n')
    dcm_download_df = pd.DataFrame(columns=["participant_dicom_dir","session_id"])
    i = 0
    for l in proc_out:
        result = l.find('found')
        if result != -1:
            dcm_file = l.strip().rsplit(" ",1)[1]
            minc_file = dcm_file.lower().find("minc")
            text_file = dcm_file.lower().find(".txt")
            if (minc_file == -1) & (text_file == -1):
                mri_index = dcm_file.lower().find("mri")
                if mri_index != -1:
                    visit_id = str(dcm_file[mri_index:].split("_",1)[0][3:])
                else:
                    visit_id = "unknown"

                dcm_download_df.loc[i] = [dcm_file, visit_id]
                i = i + 1

    return dcm_download_df

def filter_duplicate_dicoms(dicom_dir_matches,logger):
    """ Selects a single dicom dir for a participant based on number of dicoms within
    """
    n_dcm_list = []
    for dicom_dir in dicom_dir_matches:
        n_dcm = len(os.listdir(dicom_dir))
        n_dcm_list.append(n_dcm)

    n_max_dcm = np.max(n_dcm_list)
    logger.info(f"Selecting dicom dir with {n_max_dcm} dcm files")
    max_n_dicom_dir = dicom_dir_matches[np.argmax(n_dcm_list)]

    return max_n_dicom_dir

def untar_dcm(src_tar,dst_dir,tar_bkup_dir,logger):
    """ Extracts .tar and .tar.gz files and moves originals to tar backup dir
    """
    participant_dir = os.path.basename(src_tar).rsplit(".",2)[0]
    # check if untar dir exists:
    untar_dcm_dir = f"{dst_dir}/{participant_dir}/"
    if os.path.isdir(untar_dcm_dir):
        logger.warning(f"skipping untarring - extracted {untar_dcm_dir} exists")
    else:
        file = tarfile.open(src_tar)
        file.extractall(untar_dcm_dir)
        file.close()

    # Cleanup
    try:
        tar_bkup_file = f"{tar_bkup_dir}/{os.path.basename(src_tar)}"
        tar_bkup_file_exists = os.path.isfile(tar_bkup_file)
        logger.warning(f"{tar_bkup_file} exists")
        if tar_bkup_file_exists:
            os.remove(src_tar)
        else:
            _ = shutil.move(src_tar, tar_bkup_file)
    except Exception as e:
        logger.error(e)

def fetch(raw_dicom_dir,tar_bkup_dir,dcm,logger):
    """ Fetches a single dicom dir from the source
    """
    dcm_dst_name = f"{raw_dicom_dir}/{os.path.basename(dcm)}"
    logger.info(f"dcm source: {dcm}\tdcm dest: {dcm_dst_name}")

    try:
        if os.path.isdir(dcm):
            shutil.copytree(dcm, dcm_dst_name,dirs_exist_ok=False)
        else: #tar files
            dcm_untar_dir_name  = dcm_dst_name.split(".",1)[0]
            if (os.path.isfile(dcm_dst_name)) | (os.path.isdir(dcm_untar_dir_name)):
                logger.info(f"{dcm_dst_name} (tar or untar) exists")
            else:
                shutil.copyfile(dcm, dcm_dst_name)

                # Check if it's a tar (or tar.gz) file and untar it
                if "tar" in str(dcm_dst_name).rsplit("."):
                    logger.info("Untarring copied dicom")
                    untar_dcm(dcm_dst_name,raw_dicom_dir,tar_bkup_dir, logger)

    except FileExistsError as e: #this is actually a dir_exists check
        logger.warning(f"{dcm_dst_name} exists")

    except shutil.SameFileError as e:
        logger.warning(e)

def run(global_configs, session_id, n_jobs, logger=None):
    """ Runs the dicom fetch
    """
    session = f"ses-{session_id}"

    # populate relative paths
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    raw_dicom_dir = f"{DATASET_ROOT}/scratch/raw_dicom/{session}/"
    unknown_ses_dicom_dir = f"{DATASET_ROOT}/scratch/raw_dicom/ses-unknown/" # TODO
    tar_bkup_dir = f"{DATASET_ROOT}/scratch/raw_dicom/tars/"
    participant_dicom_dir_map_file = f"{DATASET_ROOT}/scratch/raw_dicom/participant_dicom_dir_map.csv"
    log_dir = f"{DATASET_ROOT}/scratch/logs/"

    # mkdirs
    Path(raw_dicom_dir).mkdir(parents=True, exist_ok=True)
    Path(unknown_ses_dicom_dir).mkdir(parents=True, exist_ok=True)
    Path(f"{tar_bkup_dir}").mkdir(parents=True, exist_ok=True)
    Path(f"{log_dir}").mkdir(parents=True, exist_ok=True)

    manifest_file = f"{DATASET_ROOT}/tabular/manifest.csv"
    doughnut_file = f"{DATASET_ROOT}/scratch/raw_dicom/doughnut.csv"

    if logger is None:
        log_file = f"{log_dir}/dicom_fetch.log"
        logger = my_logger.get_logger(log_file)

    logger.info("-"*50)
    logger.info(f"Using DATASET_ROOT: {DATASET_ROOT}")
    logger.info(f"session: {session}")
    logger.info(f"Number of parallel jobs: {n_jobs}")

    download_df = catalog.get_new_downloads(doughnut_file, raw_dicom_dir, session_id, logger)
    download_participants = list(download_df["participant_id"].values)
    n_download_participants = len(download_participants)
    logger.info(f"Found {n_download_participants} new participants for download")

    if n_download_participants > 0:
        dcm_download_df = find_mri(download_participants)
        logger.info(f"dcm_donwload_df:\n{dcm_download_df}")

        # Filter session if possible
        logger.info(f"len dcm_download_df: {len(dcm_download_df)}")
        dcm_download_session_df = dcm_download_df[dcm_download_df["session_id"]==session_id].copy()
        n_dcm_download = len(dcm_download_session_df)

        # Filter unknown session
        dcm_download_unknown_df = dcm_download_df[dcm_download_df["session_id"]=="unknown"].copy()
        n_unknown_dcm_download = len(dcm_download_unknown_df)

        logger.info(f"n_dcms found for {session}: {n_dcm_download} (includes duplicates)")
        logger.info(f"n_dcms found for unknown session: {n_unknown_dcm_download} (includes duplicates)")

        if n_unknown_dcm_download > 0:
            logger.info(f"Copying and filtering {n_unknown_dcm_download} dicoms (unknown session) into {unknown_ses_dicom_dir}")
            if n_jobs > 1:
                logger.info(f"Processing in parallel (n_jobs = {n_jobs})")
                ## Process in parallel! (Won't write to logs)
                with ProcessPoolExecutor(n_jobs) as exe:
                    _ = [exe.submit(fetch, unknown_ses_dicom_dir,tar_bkup_dir,dcm,logger)
                         for dcm in dcm_download_unknown_df["participant_dicom_dir"].values]

            else: # Useful for debugging
                for d, dcm in enumerate(dcm_download_unknown_df["participant_dicom_dir"].values):
                    logger.info(f"starting {d} of {n_unknown_dcm_download}")
                    fetch(unknown_ses_dicom_dir,tar_bkup_dir,dcm,logger)

        if n_dcm_download > 0:
            logger.info(f"Copying and filtering {n_dcm_download} dicoms {session} into {raw_dicom_dir}")
            if n_jobs > 1:
                logger.info(f"Processing in parallel (n_jobs = {n_jobs})")
                ## Process in parallel! (Won't write to logs)
                with ProcessPoolExecutor(n_jobs) as exe:
                    _ = [exe.submit(fetch, raw_dicom_dir,tar_bkup_dir,dcm,logger)
                         for dcm in dcm_download_session_df["participant_dicom_dir"].values]

            else: # Useful for debugging
                for d, dcm in enumerate(dcm_download_session_df["participant_dicom_dir"].values):
                    logger.info(f"starting {d} of {n_dcm_download}")
                    fetch(raw_dicom_dir,tar_bkup_dir,dcm,logger)

            # Multiple dicoms per participant can be found (i.e visits, failed runs etc)
            # Need to pick one per participant and per session
            new_participant_dicom_downloads = []
            for participant_id in download_participants:
                # Check for files
                dicom_dir_matches = glob.glob(f"{raw_dicom_dir}/{participant_id}*")

                if len(dicom_dir_matches) == 0:
                    logger.warning(f"No dicom dir match found for {participant_id}")
                    new_participant_dicom_downloads.append(None)
                else:
                    if len(dicom_dir_matches) > 1:
                        logger.info(f"Found multiple ({len(dicom_dir_matches)}) dicom dirs for {participant_id}")
                        link_dicom_dir = filter_duplicate_dicoms(dicom_dir_matches,logger)
                    else:
                        link_dicom_dir = dicom_dir_matches[0]

                    new_participant_dicom_downloads.append(os.path.basename(link_dicom_dir))

            n_new_participant_dicom_downloads = len(new_participant_dicom_downloads) - new_participant_dicom_downloads.count(None)
            logger.info(f"new_participant_dicom_downloads: {n_new_participant_dicom_downloads} out of {len(download_participants)}")

            if n_new_participant_dicom_downloads > 0:
                # Add newly processed bids_id to the manifest csv
                manifest_df = pd.read_csv(manifest_file)
                participant_dicom_dir_map_df = pd.read_csv(participant_dicom_dir_map_file)

                logger.info("Updating participant_dicom_dir_map_df with dicom file names")
                df = pd.DataFrame()
                df["participant_id"] = download_participants
                df["session"] = str(session)
                df["participant_dicom_dir"] = new_participant_dicom_downloads
                participant_dicom_dir_map_df = pd.concat([participant_dicom_dir_map_df, df], axis=0)
                participant_dicom_dir_map_df.to_csv(participant_dicom_dir_map_file, index=None)

                logger.info(f"DICOMs (n={n_new_participant_dicom_downloads} of {download_participants}) are now copied into {raw_dicom_dir} and ready for dicom_reorg!")
        else:
            logger.error(f"No DICOMs were found for {session} using find_mri script")

    else:
        logger.info(f"No new participants found for dicom fetch...")


if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to copy dicom dumps into nipoppy scratch/raw_dicom dir
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)
    parser.add_argument('--global_config', type=str, help='path to global config file for your nipoppy dataset')
    parser.add_argument('--session_id', type=str, default=None, help='MRI session (i.e. visit) to process)')
    parser.add_argument('--n_jobs', type=int, default=4, help='number of parallel processes')
    args = parser.parse_args()

    # read global configs
    global_config_file = args.global_config
    with open(global_config_file, 'r') as f:
        global_configs = json.load(f)

    session_id = str(args.session_id)
    n_jobs = args.n_jobs

    run(global_configs, session_id, n_jobs)
