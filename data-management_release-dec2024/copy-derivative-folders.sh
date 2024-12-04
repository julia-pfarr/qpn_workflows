#!/bin/bash

# created by Julia, Nov 2024

# This script was written for the purpose of copying folders and files from the qpn data directory
# in order to prepare the data for release. This script is supposed to look for folders and files
# in a source directory which are named according to IDs in a list file. If source directories
# and or file does not exist, ID will be recorded in a skipped-items.txt. Successfully copied
# files and folders are recorded in a copied-items.txt.

# Input files: list file with only one row.

#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <source_directory> <destination_directory> <list_file>"
  exit 1
fi

# Assign arguments to variables
SOURCE_DIR="$1"
DEST_DIR="$2"
LIST_FILE="$3"

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
> "$COPIED_FILE"  # Clear the file if it exists
> "$SKIPPED_FILE" # Clear the file if it exists

# Loop through each subject listed in the text file
while IFS= read -r subject_name; do
  if [[ -z "$subject_name" || "$subject_name" == \#* ]]; then
    continue
  fi

  copied=false

  # Check if a folder with the subject name exists
  if [ -d "$SOURCE_DIR/$subject_name" ]; then
    if [ -d "$DEST_DIR/$subject_name" ]; then
      echo "Skipping folder '$subject_name' (already exists in '$DEST_DIR')."
      echo "Folder: $subject_name" >> "$SKIPPED_FILE"
    else
      echo "Copying folder '$subject_name' from '$SOURCE_DIR' to '$DEST_DIR'..."
      cp -r "$SOURCE_DIR/$subject_name" "$DEST_DIR/"
      echo "Folder: $subject_name" >> "$COPIED_FILE"
      copied=true
    fi
  fi

  # Check for files with the subject name as a prefix (e.g., sub-001.*)
  files_found=($(find "$SOURCE_DIR" -maxdepth 1 -type f \( -name "${subject_name}" -o -name "${subject_name}_*" \)))

  if [ "${#files_found[@]}" -gt 0 ]; then
    for file in "${files_found[@]}"; do
      file_name=$(basename "$file")
      if [ -f "$DEST_DIR/$file_name" ]; then
        echo "Skipping file '$file_name' (already exists in '$DEST_DIR')."
        echo "File: $file_name" >> "$SKIPPED_FILE"
      else
        echo "Copying file '$file_name' from '$SOURCE_DIR' to '$DEST_DIR'..."
        cp "$file" "$DEST_DIR/"
        echo "File: $file_name" >> "$COPIED_FILE"
        copied=true
      fi
    done
  fi

  # Log if neither a folder nor files with extensions were found for this subject
  if [ "$copied" = false ]; then
    echo "Skipping '$subject_name' (not found in '$SOURCE_DIR')."
    echo "Not found: $subject_name" >> "$SKIPPED_FILE"
  fi

done < "$LIST_FILE"

echo "Copy operation completed."
echo "Copied items: See '$COPIED_FILE'"
echo "Skipped items: See '$SKIPPED_FILE'"
