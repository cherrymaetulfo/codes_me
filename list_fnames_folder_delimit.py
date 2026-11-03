import pandas as pd
import os
import numpy as np
import shutil

def safe_string_convert(value):
    """Safely convert value to string, handling NaN and None"""
    if pd.isna(value) or value is None:
        return ''
    return str(value).strip()

def is_file_open(filepath):
    """Check if file is open in another program"""
    try:
        with open(filepath, 'a') as f:
            return False
    except PermissionError:
        return True

def compare_and_update_first_csv(csv1, csv2, indicator_column='Has_Duplicate_In_Second_File'):
    """
    Compare two CSV files and update the first CSV with duplicate indicator
    
    Args:
        csv1 (str): Path to first CSV file (will be updated)
        csv2 (str): Path to second CSV file
        indicator_column (str): Name of the new indicator column
    """
    
    try:
        # Check if first CSV file is open in another program
        if is_file_open(csv1):
            print(f"❌ Error: {csv1} is open in another program (like Excel).")
            print("Please close the file and try again.")
            return False
        
        # Read CSV files
        df1 = pd.read_csv(csv1)
        df2 = pd.read_csv(csv2)
        
        print(f"Columns in {csv1}: {list(df1.columns)}")
        print(f"Columns in {csv2}: {list(df2.columns)}")
        
        # Check if required column exists
        if 'filename_part1' not in df1.columns or 'filename_part1' not in df2.columns:
            print("Error: 'filename_part1' column not found in one or both files")
            return False
        
        # Apply safe conversion to filename_part1
        df1['filename_part1_clean'] = df1['filename_part1'].apply(safe_string_convert)
        df2['filename_part1_clean'] = df2['filename_part1'].apply(safe_string_convert)
        
        # Filter out empty strings
        valid_df1 = df1[df1['filename_part1_clean'] != '']
        valid_df2 = df2[df2['filename_part1_clean'] != '']
        
        print(f"\nFiles with valid filename_part1:")
        print(f"  {os.path.basename(csv1)}: {len(valid_df1)}/{len(df1)}")
        print(f"  {os.path.basename(csv2)}: {len(valid_df2)}/{len(df2)}")
        
        # Find duplicates
        names1 = set(valid_df1['filename_part1_clean'])
        names2 = set(valid_df2['filename_part1_clean'])
        duplicates = names1.intersection(names2)
        
        print(f"Duplicate filename_part1 values found: {len(duplicates)}")
        
        # Add indicator column to the first CSV dataframe
        df1[indicator_column] = df1['filename_part1_clean'].isin(duplicates)
        
        # Count duplicates
        duplicate_count = df1[indicator_column].sum()
        print(f"Files in {os.path.basename(csv1)} with duplicates in {os.path.basename(csv2)}: {duplicate_count}")
        
        # Create backup of original file
        backup_path = csv1.replace('.csv', '_backup.csv')
        try:
            shutil.copy2(csv1, backup_path)
            print(f"Backup created: {backup_path}")
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
        
        # Save updated first CSV to a temporary file first
        temp_file = csv1.replace('.csv', '_temp_updated.csv')
        df1_to_save = df1.drop('filename_part1_clean', axis=1)
        df1_to_save.to_csv(temp_file, index=False)
        print(f"Temporary file created: {temp_file}")
        
        # Replace original file with temporary file
        try:
            # Remove original file
            os.remove(csv1)
            # Rename temporary file to original name
            os.rename(temp_file, csv1)
            print(f"✅ Successfully updated {csv1} with '{indicator_column}' column")
        except Exception as e:
            print(f"❌ Error replacing original file: {e}")
            print(f"Your updated file is saved as: {temp_file}")
            print(f"Your original file is preserved as: {backup_path}")
            return False
        
        # Create detailed duplicates report with full path information
        if duplicates:
            print(f"\nCreating detailed duplicates report...")
            
            # Create a comprehensive report with matching file pairs
            report_data = []
            
            for dup_name in sorted(duplicates):
                # Get all files with this name from first CSV
                files_from_csv1 = df1[df1['filename_part1_clean'] == dup_name]
                # Get all files with this name from second CSV
                files_from_csv2 = df2[df2['filename_part1_clean'] == dup_name]
                
                for idx1, row1 in files_from_csv1.iterrows():
                    for idx2, row2 in files_from_csv2.iterrows():
                        report_data.append({
                            'duplicate_name': dup_name,
                            'source_file_1': os.path.basename(csv1),
                            'file_path_1': row1['full_path'],
                            'filename_part1_1': row1['filename_part1'],
                            'filename_part2_1': row1['filename_part2'],
                            'extension_1': row1['file_extension'],
                            'source_file_2': os.path.basename(csv2),
                            'file_path_2': row2['full_path'],
                            'filename_part1_2': row2['filename_part1'],
                            'filename_part2_2': row2['filename_part2'],
                            'extension_2': row2['file_extension'],
                            'modified_date_1': row1['modified_date'],
                            'modified_date_2': row2['modified_date']
                        })
            
            # Create detailed report dataframe
            detailed_report = pd.DataFrame(report_data)
            
            if len(detailed_report) > 0:
                report_file = csv1.replace('.csv', '_detailed_duplicates_report.csv')
                detailed_report.to_csv(report_file, index=False)
                print(f"✅ Detailed duplicates report: {report_file}")
                
                # Print summary to console
                print(f"\n📊 Duplicate Summary:")
                print(f"Total duplicate pairs found: {len(detailed_report)}")
                
                for dup_name in sorted(duplicates):
                    pairs = detailed_report[detailed_report['duplicate_name'] == dup_name]
                    files1 = pairs['file_path_1'].unique()
                    files2 = pairs['file_path_2'].unique()
                    
                    print(f"\n🔍 '{dup_name}':")
                    print(f"   In {os.path.basename(csv1)} ({len(files1)} files):")
                    for file_path in files1:
                        print(f"     📄 {file_path}")
                    print(f"   In {os.path.basename(csv2)} ({len(files2)} files):")
                    for file_path in files2:
                        print(f"     📄 {file_path}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Get CSV file paths from user
    csv1 = input("Enter path to first CSV file (will be updated): ").strip()
    csv2 = input("Enter path to second CSV file: ").strip()
    
    if not os.path.exists(csv1):
        print(f"Error: {csv1} does not exist.")
        return
        
    if not os.path.exists(csv2):
        print(f"Error: {csv2} does not exist.")
        return
    
    # Optional: custom indicator column name
    indicator_name = input("Enter indicator column name (default: Has_Duplicate_In_Second_File): ").strip()
    if not indicator_name:
        indicator_name = 'Has_Duplicate_In_Second_File'
    
    print(f"\nProcessing...")
    print(f"Will update: {csv1}")
    print(f"Comparing with: {csv2}")
    print(f"Adding column: '{indicator_name}'")
    
    success = compare_and_update_first_csv(csv1, csv2, indicator_name)
    
    if success:
        print(f"\n✅ Operation completed successfully!")
        print(f"✅ {csv1} has been updated with duplicate indicators")
    else:
        print(f"\n❌ Operation failed!")

if __name__ == "__main__":
    main()