import os
import pandas as pd
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class PDFRenamedFileDetector:
    def __init__(self, root_directory, output_file="renamed_pdf_report.xlsx"):
        """
        Initialize the detector for PDF files
        
        Args:
            root_directory: Directory to search for PDF files
            output_file: Name of the output Excel report
        """
        self.root_directory = Path(root_directory)
        self.output_file = output_file
        self.all_files = pd.DataFrame()  # Initialize empty DataFrame
        self.renamed_files = pd.DataFrame()  # Initialize empty DataFrame
        
    def calculate_file_hash(self, file_path, block_size=65536):
        """
        Calculate MD5 hash of a file for duplicate detection
        """
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                buf = f.read(block_size)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(block_size)
            return hasher.hexdigest()
        except Exception:
            return None
    
    def get_file_metadata(self, file_path):
        """
        Extract comprehensive metadata from a PDF file
        """
        file_path = Path(file_path)
        
        try:
            stat_info = os.stat(file_path)
            
            metadata = {
                'full_path': str(file_path),
                'filename': file_path.name,
                'directory': str(file_path.parent),
                'size_bytes': stat_info.st_size,
                'size_mb': round(stat_info.st_size / (1024 * 1024), 2),
                'date_created': datetime.fromtimestamp(stat_info.st_ctime),
                'date_modified': datetime.fromtimestamp(stat_info.st_mtime),
                'date_accessed': datetime.fromtimestamp(stat_info.st_atime),
                'file_hash': self.calculate_file_hash(file_path),
                'extension': file_path.suffix.lower(),
            }
            
            # Analyze filename for patterns
            filename_lower = file_path.name.lower()
            
            # Version patterns
            metadata['has_version'] = bool(re.search(r'v\d+', filename_lower))
            metadata['has_revision'] = bool(re.search(r'rev\d+|revision\d+', filename_lower))
            metadata['has_final'] = 'final' in filename_lower
            metadata['has_draft'] = 'draft' in filename_lower
            metadata['has_copy'] = 'copy' in filename_lower
            metadata['has_old'] = 'old' in filename_lower
            metadata['has_new'] = 'new' in filename_lower
            
            # Extract version number if exists
            version_match = re.search(r'v(\d+)', filename_lower, re.IGNORECASE)
            metadata['version_number'] = int(version_match.group(1)) if version_match else 0
            
            # Extract date from filename if exists
            date_match = re.search(r'(\d{4}[_-]\d{2}[_-]\d{2})|(\d{8})', filename_lower)
            metadata['filename_date'] = date_match.group() if date_match else None
            
            # Calculate time differences
            metadata['age_days'] = (datetime.now() - metadata['date_created']).days
            metadata['mod_since_create_days'] = (metadata['date_modified'] - metadata['date_created']).days
            
            # Extract clean base name (without version/date patterns)
            base_name = re.sub(r'v\d+|rev\d+|revision\d+|final|draft|copy|old|new|\d{4}[_-]\d{2}[_-]\d{2}|\d{8}', '', filename_lower)
            base_name = re.sub(r'[_\-\s]+', ' ', base_name).strip()
            metadata['base_name'] = base_name
            
            return metadata
            
        except Exception as e:
            print(f"Error reading metadata for {file_path}: {e}")
            return None
    
    def find_pdf_files(self):
        """Find all PDF files in the directory and subdirectories"""
        pdf_files = []
        for ext in ['.pdf', '.PDF']:
            try:
                pdf_files.extend(self.root_directory.rglob(f'*{ext}'))
            except Exception:
                pass
        return pdf_files
    
    def find_previous_filename(self, current_file, all_files_df):
        """
        Find the most recent previous filename for a given file
        
        Args:
            current_file: Current file metadata (row from DataFrame)
            all_files_df: DataFrame with all files' metadata
            
        Returns:
            Most recent previous filename or None
        """
        current_hash = current_file['file_hash']
        current_name = current_file['filename']
        current_date = current_file['date_created']
        current_base = current_file['base_name']
        
        # Method 1: Check for duplicate content (same hash)
        if current_hash:
            same_hash_files = all_files_df[
                (all_files_df['file_hash'] == current_hash) & 
                (all_files_df['filename'] != current_name)
            ]
            
            if not same_hash_files.empty:
                # Find the most recent one (closest creation date)
                same_hash_files = same_hash_files.copy()
                same_hash_files['date_diff'] = abs((same_hash_files['date_created'] - current_date).dt.days)
                same_hash_files = same_hash_files.sort_values('date_diff')
                
                # Get the most recent previous filename
                if not same_hash_files.empty:
                    return same_hash_files.iloc[0]['filename']
        
        # Method 2: Check for same base name with different versions
        same_base_files = all_files_df[
            (all_files_df['base_name'] == current_base) & 
            (all_files_df['filename'] != current_name) &
            (all_files_df['date_created'] < current_date)
        ]
        
        if not same_base_files.empty:
            # Sort by creation date (closest to current file)
            same_base_files = same_base_files.sort_values('date_created', ascending=False)
            
            # Check for version patterns
            for _, prev_file in same_base_files.iterrows():
                # If current has version number, check for lower version
                if current_file['version_number'] > 0:
                    if prev_file['version_number'] > 0 and prev_file['version_number'] < current_file['version_number']:
                        return prev_file['filename']
                
                # Check for "draft" -> "final" patterns
                if current_file['has_final'] and prev_file['has_draft']:
                    return prev_file['filename']
                
                # Check for "old" -> "new" patterns
                if current_file['has_new'] and prev_file['has_old']:
                    return prev_file['filename']
            
            # If no clear pattern, return the most recent file with same base name
            return same_base_files.iloc[0]['filename']
        
        # Method 3: Check for files with similar names and earlier dates
        # Look for files that might be previous versions by date comparison
        if len(current_base) > 3:  # Only if base name is meaningful
            similar_files = all_files_df[
                (all_files_df['date_created'] < current_date) &
                (all_files_df['filename'].str.contains(current_base[:min(20, len(current_base))], case=False, na=False))
            ]
            
            if not similar_files.empty:
                # Get the most recent one before current
                similar_files = similar_files.sort_values('date_created', ascending=False)
                return similar_files.iloc[0]['filename']
        
        return None
    
    def calculate_rename_probability(self, row, all_files_df):
        """Calculate probability that file was renamed"""
        score = 0
        
        # Same hash = high probability
        if row['file_hash'] and all_files_df[all_files_df['file_hash'] == row['file_hash']].shape[0] > 1:
            score += 0.6
        
        # Version patterns
        if row['has_version'] or row['has_revision']:
            score += 0.3
        
        # Status transitions
        if row['has_final'] or row['has_new']:
            score += 0.2
        
        # Time gap
        if row['mod_since_create_days'] > 7:
            score += 0.1
        
        # Cap at 1.0
        return min(score, 1.0)
    
    def detect_renamed_files(self, start_date=None, end_date=None):
        """
        Detect renamed PDF files and find their previous names
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
        """
        # Convert date strings if provided
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                start_date = None
        
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                end_date = None
        
        print(f"Scanning for PDF files in {self.root_directory}...")
        pdf_files = self.find_pdf_files()
        print(f"Found {len(pdf_files)} PDF files")
        
        if not pdf_files:
            print("No PDF files found!")
            return pd.DataFrame()
        
        # Collect metadata for all files
        all_metadata = []
        for i, file_path in enumerate(pdf_files):
            print(f"Processing file {i+1}/{len(pdf_files)}: {file_path.name[:50]}...")
            metadata = self.get_file_metadata(file_path)
            if metadata is not None:
                all_metadata.append(metadata)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_metadata)
        
        if df.empty:
            print("No metadata collected!")
            return pd.DataFrame()
        
        # Filter by date range if specified
        if start_date or end_date:
            mask = pd.Series([True] * len(df))
            if start_date:
                mask = mask & (df['date_modified'] >= start_date)
            if end_date:
                mask = mask & (df['date_modified'] <= end_date)
            df = df[mask].copy()
            print(f"After date filtering: {len(df)} files")
        
        # Store all files
        self.all_files = df.copy()
        
        # Sort by creation date for better analysis
        df = df.sort_values('date_created')
        
        print(f"Analyzing {len(df)} files for rename patterns...")
        
        # Find previous filename for each file
        print("Finding previous filenames...")
        previous_filenames = []
        detection_reasons = []
        rename_probabilities = []
        
        for idx, current_file in df.iterrows():
            previous_name = self.find_previous_filename(current_file, df)
            
            if previous_name:
                # Determine detection reason
                if df[df['file_hash'] == current_file['file_hash']].shape[0] > 1:
                    reason = "Duplicate content (same file hash)"
                elif current_file['version_number'] > 0:
                    reason = "Version number increase"
                elif current_file['has_final']:
                    reason = "Draft to Final transition"
                elif current_file['has_new']:
                    reason = "Old to New transition"
                else:
                    reason = "Similar base name with earlier date"
                
                # Calculate probability
                prob = self.calculate_rename_probability(current_file, df)
            else:
                reason = "No previous version detected"
                prob = 0.0
            
            previous_filenames.append(previous_name)
            detection_reasons.append(reason)
            rename_probabilities.append(prob)
        
        df['previous_filename'] = previous_filenames
        df['detection_reason'] = detection_reasons
        df['rename_probability'] = rename_probabilities
        
        # Filter to only include files with previous names
        renamed_files = df[df['previous_filename'].notna()].copy()
        
        # Sort by rename probability (highest first)
        renamed_files = renamed_files.sort_values('rename_probability', ascending=False)
        
        self.renamed_files = renamed_files
        
        if len(renamed_files) > 0:
            print(f"\n✅ Found {len(renamed_files)} potentially renamed PDF files!")
            return renamed_files
        else:
            print("\n✅ No renamed PDF files detected.")
            return pd.DataFrame()
    
    def generate_report(self, start_date=None, end_date=None):
        """
        Generate Excel report showing current and previous filenames
        """
        if not hasattr(self, 'renamed_files') or self.renamed_files.empty:
            print("No renamed files to report!")
            return None
        
        # Create the main report with requested columns
        report_data = []
        
        for idx, row in self.renamed_files.iterrows():
            report_entry = {
                'file_path': row['directory'],
                'current_filename': row['filename'],
                'previous_filename': row['previous_filename'],
                'date_created': row['date_created'].strftime('%Y-%m-%d %H:%M:%S'),
                'date_modified': row['date_modified'].strftime('%Y-%m-%d %H:%M:%S'),
                'rename_probability': f"{row['rename_probability']:.0%}",
                'detection_reason': row['detection_reason'],
                'file_size_mb': row['size_mb'],
                'days_since_creation': row['age_days'],
                'days_between_mod_create': row['mod_since_create_days']
            }
            report_data.append(report_entry)
        
        report_df = pd.DataFrame(report_data)
        
        # Add sequence analysis - show filename evolution
        report_df['filename_evolution'] = report_df.apply(
            lambda x: f"{x['previous_filename']} → {x['current_filename']}", axis=1
        )
        
        # Create output file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if self.output_file:
            output_path = self.root_directory / self.output_file
        else:
            output_path = self.root_directory / f"renamed_pdf_analysis_{timestamp}.xlsx"
        
        # Create Excel report with multiple sheets
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: Main report with all columns
            report_df.to_excel(writer, sheet_name='Renamed_Files_Analysis', index=False)
            
            # Sheet 2: Summary view (only key columns)
            summary_cols = ['current_filename', 'previous_filename', 'date_modified', 
                          'rename_probability', 'filename_evolution']
            summary_df = report_df[summary_cols]
            summary_df.to_excel(writer, sheet_name='Summary_View', index=False)
            
            # Sheet 3: All files analyzed (for reference)
            self.all_files.to_excel(writer, sheet_name='All_Files_Analyzed', index=False)
            
            # Sheet 4: Statistics
            high_conf = len(report_df[report_df['rename_probability'].str.rstrip('%').astype(float) >= 80])
            med_conf = len(report_df[(report_df['rename_probability'].str.rstrip('%').astype(float) >= 50) & 
                                    (report_df['rename_probability'].str.rstrip('%').astype(float) < 80)])
            low_conf = len(report_df[report_df['rename_probability'].str.rstrip('%').astype(float) < 50])
            
            stats_data = {
                'Metric': [
                    'Total PDF files analyzed',
                    'Files with detected previous names',
                    'High confidence renames (≥80% probability)',
                    'Medium confidence renames (50-79% probability)',
                    'Low confidence renames (<50% probability)',
                    'Most common detection reason',
                    'Average days between creation and modification',
                    'Largest time gap found (days)'
                ],
                'Value': [
                    len(self.all_files),
                    len(self.renamed_files),
                    high_conf,
                    med_conf,
                    low_conf,
                    report_df['detection_reason'].mode()[0] if not report_df['detection_reason'].mode().empty else 'N/A',
                    report_df['days_between_mod_create'].mean() if 'days_between_mod_create' in report_df.columns else 0,
                    report_df['days_between_mod_create'].max() if 'days_between_mod_create' in report_df.columns else 0
                ]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)
        
        # Format the Excel file
        self.format_excel_report(output_path)
        
        print(f"\n📊 Report generated: {output_path}")
        
        # Print a summary to console
        self.print_summary(report_df)
        
        return output_path
    
    def format_excel_report(self, file_path):
        """Format the Excel report for better readability"""
        try:
            from openpyxl import load_workbook
            from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
            
            wb = load_workbook(file_path)
            
            # Define styles
            header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            header_font = Font(color='FFFFFF', bold=True)
            center_alignment = Alignment(horizontal='center', vertical='center')
            thin_border = Border(left=Side(style='thin'), 
                                right=Side(style='thin'),
                                top=Side(style='thin'), 
                                bottom=Side(style='thin'))
            
            # Format each sheet
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                
                # Format header row
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = center_alignment
                    cell.border = thin_border
                
                # Adjust column widths
                for column in ws.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)
                    ws.column_dimensions[column_letter].width = adjusted_width
                
                # Apply borders to all cells
                for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
                    for cell in row:
                        cell.border = thin_border
            
            wb.save(file_path)
            
        except Exception as e:
            print(f"Note: Excel formatting skipped: {e}")
    
    def print_summary(self, report_df):
        """Print a summary of findings to console"""
        print("\n" + "="*80)
        print("📋 RENAMED PDF FILES SUMMARY")
        print("="*80)
        
        if report_df.empty:
            print("No renamed files found.")
            return
        
        # Group by confidence level
        report_df['prob_num'] = report_df['rename_probability'].str.rstrip('%').astype(float)
        
        high_conf = report_df[report_df['prob_num'] >= 80]
        med_conf = report_df[(report_df['prob_num'] >= 50) & (report_df['prob_num'] < 80)]
        low_conf = report_df[report_df['prob_num'] < 50]
        
        print(f"\n📊 Confidence Levels:")
        print(f"   🔴 High Confidence (≥80%): {len(high_conf)} files")
        print(f"   🟡 Medium Confidence (50-79%): {len(med_conf)} files")
        print(f"   🟢 Low Confidence (<50%): {len(low_conf)} files")
        
        if not high_conf.empty:
            print(f"\n🔴 TOP HIGH-CONFIDENCE RENAMES:")
            for idx, row in high_conf.head(5).iterrows():
                print(f"\n   📄 Current: {row['current_filename']}")
                print(f"      🔄 Was: {row['previous_filename']}")
                print(f"      📅 Modified: {row['date_modified']}")
                print(f"      📈 Probability: {row['rename_probability']}")
                print(f"      🔍 Reason: {row['detection_reason']}")
        
        # Show filename evolution patterns
        print(f"\n🔄 COMMON FILENAME EVOLUTION PATTERNS:")
        patterns = report_df['filename_evolution'].value_counts().head(5)
        for pattern, count in patterns.items():
            print(f"   • {pattern} ({count} files)")
        
        print("\n" + "="*80)


def main():
    """
    Main interactive function
    """
    print("="*80)
    print("📄 PDF RENAMED FILE DETECTOR")
    print("="*80)
    print("This tool analyzes PDF files to detect renames and shows:")
    print("• Current filename")
    print("• Previous filename (before rename)")
    print("• When it was created and modified")
    print("="*80)
    
    # Get directory to analyze
    while True:
        print("\n📁 Enter directory path (drag & drop folder or type path):")
        print("   Press Enter to use current directory")
        
        directory_input = input("\nDirectory: ").strip()
        directory_input = directory_input.strip('"\'')
        
        if not directory_input:
            directory_input = "."
            print(f"   Using: {os.getcwd()}")
        
        directory = Path(directory_input)
        
        if directory.exists():
            break
        else:
            print(f"❌ Directory not found: {directory}")
    
    # Check for PDF files
    print("\n🔍 Checking for PDF files...")
    pdf_files = list(directory.rglob('*.pdf')) + list(directory.rglob('*.PDF'))
    
    if not pdf_files:
        print("❌ No PDF files found!")
        return
    
    print(f"✅ Found {len(pdf_files)} PDF files")
    
    # Date range filter
    print("\n" + "-"*80)
    print("📅 DATE FILTER (Optional)")
    print("-"*80)
    print("Analyze only files modified within this date range.")
    print("Format: YYYY-MM-DD (e.g., 2024-01-01)")
    print("Leave empty to analyze all files.")
    
    start_date = input("\nStart date (YYYY-MM-DD): ").strip() or None
    end_date = input("End date (YYYY-MM-DD): ").strip() or None
    
    # Output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_name = f"pdf_rename_analysis_{timestamp}.xlsx"
    
    print(f"\n💾 Output will be saved as: {default_name}")
    
    # Confirm and run
    print("\n" + "="*80)
    print("READY TO ANALYZE")
    print("="*80)
    print(f"Directory: {directory}")
    print(f"Date range: {start_date or 'All dates'} to {end_date or 'All dates'}")
    print(f"PDF files: {len(pdf_files)}")
    print("="*80)
    
    confirm = input("\nStart analysis? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Analysis cancelled.")
        return
    
    print(f"\n🚀 Starting analysis...")
    print("-"*80)
    
    # Create detector and run analysis
    detector = PDFRenamedFileDetector(directory, default_name)
    
    try:
        # Detect renamed files
        renamed_files = detector.detect_renamed_files(start_date, end_date)
        
        if not renamed_files.empty:
            # Generate report
            report_path = detector.generate_report(start_date, end_date)
            
            # Final message
            print("\n" + "="*80)
            print("✅ ANALYSIS COMPLETE!")
            print("="*80)
            print(f"\n📊 Results:")
            print(f"   • Total files analyzed: {len(detector.all_files)}")
            print(f"   • Renamed files detected: {len(renamed_files)}")
            print(f"   • Report saved to: {report_path}")
            
            # Show quick preview
            print(f"\n👀 Preview of findings:")
            preview = renamed_files.head(3)
            for idx, row in preview.iterrows():
                print(f"\n   📄 {row['filename']}")
                print(f"      🔄 Was previously: {row['previous_filename']}")
            
            # Offer to open the report
            open_it = input("\n📂 Open the Excel report now? (y/n): ").strip().lower()
            if open_it == 'y':
                try:
                    os.startfile(report_path)
                except:
                    print(f"⚠️  Could not open automatically.")
                    print(f"   Please open manually: {report_path}")
        
        else:
            print("\n" + "="*80)
            print("✅ ANALYSIS COMPLETE - NO RENAMES FOUND")
            print("="*80)
            print("\nNo renamed PDF files were detected.")
            print("\nPossible reasons:")
            print("  • All files are original (no duplicates)")
            print("  • No version patterns in filenames")
            print("  • Files were genuinely created at their modification time")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def quick_mode():
    """Quick analysis of current directory"""
    print("Quick Mode: Scanning current directory for renamed PDFs...")
    
    detector = PDFRenamedFileDetector(Path("."), "quick_pdf_rename_analysis.xlsx")
    
    try:
        renamed_files = detector.detect_renamed_files()
        
        if not renamed_files.empty:
            report_path = detector.generate_report()
            
            print(f"\n✅ Found {len(renamed_files)} potentially renamed PDF files")
            print(f"📄 Report: {report_path}")
            
            # Show filename evolution
            print("\n🔄 Filename changes detected:")
            for idx, row in renamed_files.head(5).iterrows():
                print(f"  • {row['previous_filename']} → {row['current_filename']}")
        else:
            print("\n✅ No renamed PDF files detected")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Check for required packages
    try:
        import pandas as pd
    except ImportError:
        print("Pandas not found! Installing...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
        print("Please restart the script.")
        sys.exit(1)
    
    # Choose mode
    print("="*80)
    print("PDF RENAMED FILE DETECTOR")
    print("="*80)
    print("\nChoose mode:")
    print("1. Full Interactive Analysis")
    print("2. Quick Scan (Current Directory Only)")
    
    choice = input("\nSelect (1 or 2): ").strip()
    
    if choice == "2":
        quick_mode()
    else:
        main()
    
    input("\nPress Enter to exit...")