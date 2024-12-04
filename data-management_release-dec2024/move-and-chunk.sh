#!/bin/bash

# created by Julia, Nov 2024

# Background: QPN data could only be released by chunking participant data in multiple tars
# per modality/pipeline. This script moves folders and files into newly created folders. It
# looks in a given source directory for folders and files named in the manner of sub*-participant_id
# and then chunks the data in parcels with 13 indices per parcel. Indices are matched to
# participant_id in the participants.tsv table. Parcels will always be in the 13 range even if
# a participant is missing.

# Input files: tabular file with two rows "folder-index" and "participant_id".

# Check if the correct number of arguments is provided
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <csv-file> <destination_directory> <source_directory1> <source_directory2> ..."
  exit 1
fi

# Input variables from command line
CSV_FILE="$1"
DEST_DIR="$2"
shift 2
SOURCE_DIRS=("$@")

CHUNK_SIZE=13  # Number of indices per group

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Read the CSV file and calculate the total number of lines
total_lines=$(wc -l < "$CSV_FILE")
num_chunks=$((($total_lines + $CHUNK_SIZE - 1) / $CHUNK_SIZE))

for chunk_id in $(seq 1 $num_chunks); do
  # Calculate start and end line numbers for this chunk
  start_line=$((($chunk_id - 1) * $CHUNK_SIZE + 2))
  end_line=$(($start_line + $CHUNK_SIZE - 1))

  # Extract current chunk's rows
  chunk_rows=$(sed -n "${start_line},${end_line}p" "$CSV_FILE")

  # Get the range of folder_index values for this chunk
  start_index=$(echo "$chunk_rows" | head -n 1 | cut -d ',' -f1)
  end_index=$(echo "$chunk_rows" | tail -n 1 | cut -d ',' -f1)

  # Loop over source directories
  for source_dir in "${SOURCE_DIRS[@]}"; do
    parent_folder=$(basename "$source_dir")

    # Create the group folder (parent-folder_startIndex-endIndex)
    group_folder_name="${parent_folder}_${start_index}-${end_index}"
    group_folder_path="$DEST_DIR/$group_folder_name"
    mkdir -p "$group_folder_path"

    # Move participant files and folders
    while IFS=, read -r folder_index participant_id; do
      # Skip the header or empty lines
      if [[ "$folder_index" == "folder_index" || -z "$participant_id" ]]; then
        continue
      fi

      found=0
      items_to_move=()

      # Check for both files and folders starting with participant_id
      for item in "$source_dir"/"$participant_id"*; do
        if [ -e "$item" ]; then
          items_to_move+=("$item")
          found=1
        fi
      done

      # If files/folders were found, move them to the group folder
      if [ $found -eq 1 ]; then
        for item in "${items_to_move[@]}"; do
          mv "$item" "$group_folder_path/"
        done
        echo "Moved: $participant_id"
      else
        echo "Warning: $participant_id not found in $source_dir."
        echo "Not found: $participant_id" >> "$group_folder_path/skipped_items.txt"
      fi
    done <<< "$chunk_rows"
  done
done

echo "Move operation completed. Organized into $num_chunks folders in '$DEST_DIR'."
