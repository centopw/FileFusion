import os
import shutil
from tqdm import tqdm
import logging
import json
import hashlib

# Create the updated dictionary to map file extensions to folder names
extension_mapping = {
    "ai": "Design",
    "psd": "Design",
    "fig": "Design",
    "pdf": "Documents",
    "docx": "Documents",
    "doc": "Documents",
    "csv": "Documents",
    "xlsx": "Documents",
    "xls": "Documents",
    "txt": "Documents",
    "pptx": "Documents",
    "ppt": "Documents",
    "rar": "Compress",
    "7zip": "Compress",
    "zip": "Compress",
    "exe": "Executable",
    "png": "Images",
    "jpg": "Images",
    "jpeg": "Images",
    "svg": "Images",
    "ttf": "Fonts",
    # Add more extensions and folder mappings as needed
}

def hash_file(file_path):
    # Function to generate a hash for a file
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def organize_files_by_extension(target_folder, backup_folder=None, file_filter=None, skip_existing=True, exclude_folders=None, sort_files=False, dry_run=False, interactive=False, undo=False, stats=False):
    # Function to create a folder if it doesn't exist
    def create_folder_if_not_exists(folder_path):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    # Function to move unclassified files to a specified folder
    def move_unclassified_files(unclassified_folder):
        create_folder_if_not_exists(unclassified_folder)
        for root, _, files in os.walk(target_folder):
            for filename in files:
                if os.path.isfile(os.path.join(root, filename)):
                    extension = os.path.splitext(filename)[1][1:].lower()
                    if extension not in extension_mapping:
                        source = os.path.join(root, filename)
                        if not dry_run:
                            shutil.move(source, os.path.join(unclassified_folder, filename))
                        logging.info(f"Moved unclassified file '{filename}' to '{unclassified_folder}'")

    # Function to undo file movements based on backup files
    def undo_file_movements():
        if not backup_folder:
            logging.warning("Backup folder not specified. Undo not possible.")
            return

        for root, _, files in os.walk(backup_folder):
            for filename in files:
                if os.path.isfile(os.path.join(root, filename)):
                    source = os.path.join(root, filename)
                    destination = os.path.join(target_folder, filename[:-4])  # Remove ".bak" extension
                    if not dry_run:
                        shutil.move(source, destination)
                    logging.info(f"Restored backup file '{filename}' to '{destination}'")

    # Function to check for duplicate files
    def check_for_duplicates():
        hash_map = {}
        duplicate_files = []
        for root, _, files in os.walk(target_folder):
            for filename in files:
                if os.path.isfile(os.path.join(root, filename)):
                    file_path = os.path.join(root, filename)
                    file_hash = hash_file(file_path)
                    if file_hash in hash_map:
                        duplicate_files.append((file_path, hash_map[file_hash]))
                    else:
                        hash_map[file_hash] = file_path
        return duplicate_files

    # Logging configuration
    log_file = os.path.join(target_folder, "filemover.log")
    logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Perform the file organization
    total_files = 0
    file_stats = {}  # To store statistics of files moved to each folder

    # Count the total number of files to process, including subfolders
    for root, _, files in os.walk(target_folder):
        if exclude_folders and any(folder in root for folder in exclude_folders):
            continue
        for filename in files:
            if file_filter and not any(filename.endswith(ext) for ext in file_filter):
                continue
            total_files += 1

    # Move files to their corresponding folders with backup and verification
    with tqdm(total=total_files, desc="Processing Files", unit="file") as pbar:
        for root, _, files in os.walk(target_folder):
            if exclude_folders and any(folder in root for folder in exclude_folders):
                continue
            for filename in files:
                source = os.path.join(root, filename)

                if file_filter and not any(filename.endswith(ext) for ext in file_filter):
                    continue

                if os.path.isfile(source):  # Check if the source is a file
                    extension = os.path.splitext(filename)[1][1:].lower()
                    if extension in extension_mapping:
                        folder_name = extension_mapping[extension]
                        destination = os.path.join(target_folder, folder_name)

                        # Create the destination folder if it doesn't exist
                        create_folder_if_not_exists(destination)

                        # Create a backup before moving the file
                        if backup_folder:
                            backup_destination = os.path.join(backup_folder, f"{filename}.bak")
                        else:
                            backup_destination = os.path.join(root, f"{filename}.bak")

                        if not dry_run:
                            shutil.copy2(source, backup_destination)

                        if not dry_run and not interactive:
                            # Move the file to the new folder
                            if skip_existing and os.path.exists(os.path.join(destination, filename)):
                                logging.warning(f"File '{filename}' already exists in '{destination}'. Skipping.")
                            else:
                                shutil.move(source, os.path.join(destination, filename))
                                logging.info(f"Moved file '{filename}' to '{destination}'")
                        elif not dry_run and interactive:
                            move_choice = input(f"Move file '{filename}' to '{destination}'? (Y/N): ")
                            if move_choice.lower() == 'y':
                                shutil.move(source, os.path.join(destination, filename))
                                logging.info(f"Moved file '{filename}' to '{destination}'")
                            else:
                                logging.info(f"File '{filename}' was not moved.")
                    else:
                        # Handle unclassified files
                        unclassified_folder = os.path.join(target_folder, "Unclassified")
                        move_unclassified_files(unclassified_folder)
                else:
                    # Handle directories that are skipped
                    logging.info(f"Skipping directory '{filename}'")

                pbar.update(1)
                # Update file statistics
                if stats and destination:
                    file_stats[folder_name] = file_stats.get(folder_name, 0) + 1

    # File Type Cleanup
    if not dry_run and "Unclassified" in extension_mapping.values():
        unclassified_folder = os.path.join(target_folder, "Unclassified")
        move_unclassified_files(unclassified_folder)

    # Undo Functionality
    if undo and backup_folder:
        undo_file_movements()

    # File Duplication Check
    if stats:
        duplicate_files = check_for_duplicates()
        if duplicate_files:
            print("\nDuplicate Files Found:")
            for file1, file2 in duplicate_files:
                print(f"Duplicate: '{file1}' and '{file2}'")

    # Display file type statistics
    if stats:
        print("\nFile Type Statistics:")
        for folder, count in file_stats.items():
            print(f"{folder}: {count} files")

if __name__ == "__main__":
    target_folder = os.getcwd()
    backup_folder = os.path.join(target_folder, "backup")
    file_filter = [".pdf", ".docx", ".ai", ".psd", ".fig", ".doc", ".csv", ".xlsx", ".xls", ".txt", ".pptx", ".ppt", ".rar", ".7zip", ".zip", ".exe", ".png", ".jpg", ".jpeg", ".svg", ".ttf"]
    exclude_folders = ["exclude_folder1", "exclude_folder2"]
    skip_existing = True
    sort_files = False
    dry_run = False
    interactive = False
    undo = False  # Set to True to perform an undo of previous file movements
    stats = True  # Set to True to display file type statistics and check for duplicate files

    # Load custom file extension to folder name mapping from a configuration file (e.g., config.json)
    config_file = os.path.join(target_folder, "config.json")
    if os.path.exists(config_file):
        with open(config_file) as f:
            custom_mapping = json.load(f)
        extension_mapping.update(custom_mapping)

    organize_files_by_extension(target_folder, backup_folder, file_filter, skip_existing, exclude_folders, sort_files, dry_run, interactive, undo, stats)
