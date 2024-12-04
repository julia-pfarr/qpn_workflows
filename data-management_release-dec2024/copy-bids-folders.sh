#!/bin/bash

# Created by Julia, Nov 2024

# Check if the correct number of arguments is provided
if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <source_directory> <destination_directory> <list_file> <goal_folders>"
  echo "Example: $0 /path/to/source /path/to/dest list.txt anat,func"
  exit 1
fi

# Assign arguments to variables
SOURCE_DIR="$1"
DEST_DIR="$2"
LIST_FILE="$3"
GOAL_FOLDERS="$4" # Comma-separated goal folders (e.g., "anat,func")

# Split goal folders into an array
IFS=',' read -r -a GOAL_FOLDERS_ARRAY <<< "$GOAL_FOLDERS"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: Source directory '$SOURCE_DIR' does not exist."
  exit 1
fi

# Check if destination directory exists; create it if not
if [ ! -d "$DEST_DIR" ]; then
  echo "Destination directory '$DEST_DIR' does not exist. Creating it..."
  mkdir -p "$DEST_DIR"
fi

# Check if list file exists
if [ ! -f "$LIST_FILE" ]; then
  echo "Error: List file '$LIST_FILE' does not exist."
  exit 1
fi

# Define output files inside the destination directory
COPIED_FILE="$DEST_DIR/copied_items.txt"
SKIPPED_FILE="$DEST_DIR/skipped_items.txt"
> "$COPIED_FILE"
> "$SKIPPED_FILE"

# Loop through each subject listed in the text file
while IFS= read -r subject_name; do
  # Skip empty lines or lines starting with #
  if [[ -z "$subject_name" || "$subject_name" == \#* ]]; then
    continue
  fi

  copied=false

  # Iterate through goal folders
  for goal_folder in "${GOAL_FOLDERS_ARRAY[@]}"; do
    SOURCE_PATH="$SOURCE_DIR/$subject_name/ses-01/$goal_folder"
    DEST_PATH="$DEST_DIR/$subject_name/ses-01/$goal_folder"

    # Check if the goal folder exists in the source directory
    if [ -d "$SOURCE_PATH" ]; then
      if [ -d "$DEST_PATH" ]; then
        echo "Skipping folder '$SOURCE_PATH' (already exists in '$DEST_PATH')."
        echo "Folder: $SOURCE_PATH" >> "$SKIPPED_FILE"
      else
        echo "Copying folder '$SOURCE_PATH' to '$DEST_PATH'..."
        mkdir -p "$(dirname "$DEST_PATH")"
        cp -r "$SOURCE_PATH" "$DEST_PATH"
        echo "Folder: $SOURCE_PATH" >> "$COPIED_FILE"
        copied=true
      fi
    else
      echo "Skipping '$SOURCE_PATH' (not found in source)."
      echo "Not found: $SOURCE_PATH" >> "$SKIPPED_FILE"
    fi
  done

  # Log if none of the goal folders were copied for this subject
  if [ "$copied" = false ]; then
    echo "No goal folders copied for '$subject_name'."
  fi

done < "$LIST_FILE"

echo "Copy operation completed."
echo "Copied items: See '$COPIED_FILE'"
echo "Skipped items: See '$SKIPPED_FILE'"
