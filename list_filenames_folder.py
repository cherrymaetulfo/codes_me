import os
import csv
from datetime import datetime

def generate_file_list_csv(root_folder, output_csv="file_list.csv"):
    """
    Generate a CSV file containing filenames, paths, extensions, and modification dates
    for all files in a folder and its subfolders.
    
    Args:
        root_folder (str): Path to the root folder to scan
        output_csv (str): Name of the output CSV file
    """
    
    # Check if the root folder exists
    if not os.path.exists(root_folder):
        print(f"Error: The folder '{root_folder}' does not exist.")
        return
    
    # CSV headers
    headers = ['Filename', 'Extension', 'File Path', 'Date Modified', 'Date Created', 'Size (Bytes)']
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        
        file_count = 0
        
        # Walk through all files and subfolders
        for root, dirs, files in os.walk(root_folder):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    # Get file statistics
                    stat_info = os.stat(file_path)
                    
                    # Split filename and extension
                    filename, extension = os.path.splitext(file)
                    
                    # Get modification and creation times
                    mod_time = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    create_time = datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Get file size
                    file_size = stat_info.st_size
                    
                    # Write to CSV
                    writer.writerow([
                        filename,
                        extension,
                        file_path,
                        mod_time,
                        create_time,
                        file_size
                    ])
                    
                    file_count += 1
                    
                except (OSError, PermissionError) as e:
                    print(f"Warning: Could not access file '{file_path}': {e}")
                    continue
        
        print(f"CSV file '{output_csv}' generated successfully!")
        print(f"Found and processed {file_count} files.")

def main():
    # Get folder path from user input
    folder_path = input("Enter the path to the folder you want to scan: ").strip()
    
    # Remove quotes if user entered path with quotes
    folder_path = folder_path.strip('"\'')
    
    # Get output filename (optional)
    output_name = input("Enter output CSV filename (press Enter for 'file_list.csv'): ").strip()
    if not output_name:
        output_name = "file_list.csv"
    elif not output_name.endswith('.csv'):
        output_name += '.csv'
    
    # Generate the CSV
    generate_file_list_csv(folder_path, output_name)

if __name__ == "__main__":
    main()