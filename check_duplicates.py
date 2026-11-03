import pandas as pd
import os
from datetime import datetime

def compare_csv_and_mark_duplicates(csv1_path, csv2_path):
    """
    Compare two CSV files and add duplicate indicators to a selected CSV
    without modifying the original files.
    """
    
    # Read both CSV files
    try:
        df1 = pd.read_csv(csv1_path)
        df2 = pd.read_csv(csv2_path)
        print(f"Loaded {csv1_path}: {len(df1)} files")
        print(f"Loaded {csv2_path}: {len(df2)} files")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return
    
    # Create filename with extension for comparison
    df1['Filename_With_Ext'] = df1['Filename'] + df1['Extension']
    df2['Filename_With_Ext'] = df2['Filename'] + df2['Extension']
    
    # Find duplicates
    duplicates_df1 = df1[df1['Filename_With_Ext'].isin(df2['Filename_With_Ext'])]
    duplicates_df2 = df2[df2['Filename_With_Ext'].isin(df1['Filename_With_Ext'])]
    
    print(f"\nFound {len(duplicates_df1)} duplicate filenames")
    
    if len(duplicates_df1) == 0:
        print("No duplicate filenames found!")
        return
    
    # Display duplicates summary - FIXED ITERATION
    print("\nDuplicate files found:")
    print("-" * 80)
    
    # Show first 10 duplicates
    for idx in range(min(10, len(duplicates_df1))):
        row1 = duplicates_df1.iloc[idx]
        filename = row1['Filename_With_Ext']
        matching_rows = df2[df2['Filename_With_Ext'] == filename]
        
        if len(matching_rows) > 0:
            matching_row = matching_rows.iloc[0]
            print(f"{idx + 1}. {filename}")
            print(f"   CSV1: {row1['File Path']}")
            print(f"   CSV2: {matching_row['File Path']}")
    
    if len(duplicates_df1) > 10:
        print(f"   ... and {len(duplicates_df1) - 10} more duplicates")
    
    # Ask user which CSV to mark with duplicate indicators
    print("\n" + "="*60)
    print("DUPLICATE MARKING OPTIONS")
    print("="*60)
    print(f"1. Mark duplicates in FIRST CSV: {os.path.basename(csv1_path)}")
    print(f"2. Mark duplicates in SECOND CSV: {os.path.basename(csv2_path)}")
    print("3. Mark duplicates in BOTH CSVs (separate output files)")
    
    choice = input("\nChoose an option (1-3): ").strip()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if choice == '1':
        # Mark duplicates in first CSV
        output_df = mark_duplicates_in_csv(df1, df2, csv1_path, "first", timestamp)
        print(f"\nMarked {len(duplicates_df1)} duplicates in first CSV")
        
    elif choice == '2':
        # Mark duplicates in second CSV
        output_df = mark_duplicates_in_csv(df2, df1, csv2_path, "second", timestamp)
        print(f"\nMarked {len(duplicates_df2)} duplicates in second CSV")
        
    elif choice == '3':
        # Mark duplicates in both CSVs
        output_df1 = mark_duplicates_in_csv(df1, df2, csv1_path, "first", timestamp)
        output_df2 = mark_duplicates_in_csv(df2, df1, csv2_path, "second", timestamp)
        print(f"\nMarked duplicates in both CSVs:")
        print(f"First CSV: {len(duplicates_df1)} duplicates marked")
        print(f"Second CSV: {len(duplicates_df2)} duplicates marked")
        
    else:
        print("Invalid choice. No files created.")
        return
    
    # Generate duplicate report
    generate_duplicate_report(duplicates_df1, duplicates_df2, csv1_path, csv2_path, timestamp)
    
    print("\nOriginal CSV files remain unchanged.")
    print("New files with duplicate indicators have been created.")

def mark_duplicates_in_csv(target_df, source_df, original_path, csv_type, timestamp):
    """
    Add duplicate indicators to a DataFrame and save as new file
    """
    # Create filename with extension if not exists
    if 'Filename_With_Ext' not in target_df.columns:
        target_df['Filename_With_Ext'] = target_df['Filename'] + target_df['Extension']
    if 'Filename_With_Ext' not in source_df.columns:
        source_df['Filename_With_Ext'] = source_df['Filename'] + source_df['Extension']
    
    # Identify duplicates
    duplicate_filenames = set(target_df['Filename_With_Ext']).intersection(set(source_df['Filename_With_Ext']))
    
    # Add duplicate indicator column
    target_df['Has_Duplicate'] = target_df['Filename_With_Ext'].isin(duplicate_filenames)
    
    # Add duplicate details column
    target_df['Duplicate_Details'] = ""
    
    # For files with duplicates, add information about where the duplicate is found
    for filename in duplicate_filenames:
        # Find matching files in source CSV
        source_matches = source_df[source_df['Filename_With_Ext'] == filename]
        if len(source_matches) > 0:
            source_match = source_matches.iloc[0]
            duplicate_info = f"Duplicate found in {('second' if csv_type == 'first' else 'first')} CSV: {source_match['File Path']}"
            
            # Update the duplicate details
            target_df.loc[target_df['Filename_With_Ext'] == filename, 'Duplicate_Details'] = duplicate_info
    
    # Remove temporary column
    if 'Filename_With_Ext' in target_df.columns:
        output_df = target_df.drop('Filename_With_Ext', axis=1)
    else:
        output_df = target_df
    
    # Save new file
    original_name = os.path.splitext(os.path.basename(original_path))[0]
    output_filename = f"{original_name}_with_duplicates_{timestamp}.csv"
    
    output_df.to_csv(output_filename, index=False)
    print(f"Created: {output_filename}")
    
    # Show summary
    duplicate_count = output_df['Has_Duplicate'].sum()
    print(f"  - Total files: {len(output_df)}")
    print(f"  - Files with duplicates: {duplicate_count}")
    print(f"  - Unique files: {len(output_df) - duplicate_count}")
    
    return output_df

def generate_duplicate_report(duplicates_df1, duplicates_df2, csv1_path, csv2_path, timestamp):
    """
    Generate a detailed report of all duplicates found - FIXED ITERATION
    """
    report_data = []
    
    # Use iloc for iteration instead of iterrows()
    for idx1 in range(len(duplicates_df1)):
        row1 = duplicates_df1.iloc[idx1]
        filename = row1['Filename_With_Ext']
        matching_rows = duplicates_df2[duplicates_df2['Filename_With_Ext'] == filename]
        
        if len(matching_rows) > 0:
            for idx2 in range(len(matching_rows)):
                row2 = matching_rows.iloc[idx2]
                report_data.append({
                    'Filename': row1['Filename'],
                    'Extension': row1['Extension'],
                    'Full_Filename': filename,
                    'Path_In_First_CSV': row1['File Path'],
                    'Date_Modified_First': row1['Date Modified'],
                    'Date_Created_First': row1.get('Date Created', 'N/A'),
                    'Size_First_Bytes': row1.get('Size (Bytes)', 'N/A'),
                    'Path_In_Second_CSV': row2['File Path'],
                    'Date_Modified_Second': row2['Date Modified'],
                    'Date_Created_Second': row2.get('Date Created', 'N/A'),
                    'Size_Second_Bytes': row2.get('Size (Bytes)', 'N/A')
                })
    
    if report_data:
        report_df = pd.DataFrame(report_data)
        report_filename = f"duplicate_detailed_report_{timestamp}.csv"
        report_df.to_csv(report_filename, index=False)
        print(f"\nDetailed duplicate report: {report_filename}")
        
        # Print summary
        print(f"\nDUPLICATE SUMMARY:")
        print(f"Total duplicate files: {len(report_data)}")
        
        # Check for files with different sizes
        if 'Size_First_Bytes' in report_df.columns and 'Size_Second_Bytes' in report_df.columns:
            try:
                size_mismatch = report_df[report_df['Size_First_Bytes'] != report_df['Size_Second_Bytes']]
                if len(size_mismatch) > 0:
                    print(f"Files with different sizes: {len(size_mismatch)}")
            except:
                pass  # Skip if there are issues with size comparison
        
        # Check for files with different modification dates
        try:
            date_mismatch = report_df[report_df['Date_Modified_First'] != report_df['Date_Modified_Second']]
            if len(date_mismatch) > 0:
                print(f"Files with different modification dates: {len(date_mismatch)}")
        except:
            pass  # Skip if there are issues with date comparison

def main():
    """Main function to run the duplicate detection"""
    print("CSV Duplicate Detection Tool")
    print("=" * 50)
    print("This tool will:")
    print("- Compare two CSV files from your folder scans")
    print("- Identify duplicate filenames")
    print("- Add duplicate indicators to your chosen CSV")
    print("- Keep original CSV files intact")
    print("- Generate detailed reports")
    print("=" * 50)
    
    # Get CSV file paths
    csv1 = input("Enter path to first CSV file: ").strip('"\'')
    csv2 = input("Enter path to second CSV file: ").strip('"\'')
    
    # Validate files exist
    if not os.path.exists(csv1):
        print(f"Error: File '{csv1}' not found.")
        return
    if not os.path.exists(csv2):
        print(f"Error: File '{csv2}' not found.")
        return
    
    # Run comparison
    compare_csv_and_mark_duplicates(csv1, csv2)

if __name__ == "__main__":
    main()