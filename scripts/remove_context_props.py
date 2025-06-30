#!/usr/bin/env python3
"""
Script to remove <prop type="context"></prop> tags from multiple files.
Supports various file types and includes backup functionality.
"""

import os
import re
import shutil
import argparse
from pathlib import Path
from typing import List, Tuple


def find_files_with_context_props(directory: str, file_extensions: List[str] = None) -> List[str]:
    """
    Find all files that contain <prop type="context"> tags.
    
    Args:
        directory: Directory to search in
        file_extensions: List of file extensions to search (e.g., ['.tmx', '.xml', '.txt'])
    
    Returns:
        List of file paths that contain the target tags
    """
    matching_files = []
    
    if file_extensions is None:
        file_extensions = ['.tmx', '.xml', '.txt', '.html', '.htm']
    
    # Pattern to match <prop type="context"> with any content and closing </prop>
    pattern = r'<prop\s+type="context"[^>]*>.*?</prop>'
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            # Check if file extension matches or if no extensions specified
            if file_extensions and file_ext not in file_extensions:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
                        matching_files.append(file_path)
            except Exception as e:
                print(f"Warning: Could not read file {file_path}: {e}")
    
    return matching_files


def remove_context_props_from_file(file_path: str, create_backup: bool = True) -> Tuple[bool, int]:
    """
    Remove <prop type="context"></prop> tags from a single file.
    
    Args:
        file_path: Path to the file to process
        create_backup: Whether to create a backup of the original file
    
    Returns:
        Tuple of (success: bool, replacements_count: int)
    """
    try:
        # Create backup if requested
        if create_backup:
            backup_path = file_path + '.backup'
            shutil.copy2(file_path, backup_path)
        
        # Read the file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Pattern to match <prop type="context"> with any content and closing </prop>
        pattern = r'<prop\s+type="context"[^>]*>.*?</prop>'
        
        # Count matches before replacement
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        replacements_count = len(matches)
        
        # Remove the tags
        cleaned_content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Write the cleaned content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        return True, replacements_count
        
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return False, 0


def process_files(file_paths: List[str], create_backup: bool = True, dry_run: bool = False) -> dict:
    """
    Process multiple files to remove context prop tags.
    
    Args:
        file_paths: List of file paths to process
        create_backup: Whether to create backups
        dry_run: If True, only show what would be done without making changes
    
    Returns:
        Dictionary with processing results
    """
    results = {
        'total_files': len(file_paths),
        'processed_files': 0,
        'failed_files': 0,
        'total_replacements': 0,
        'file_results': []
    }
    
    for file_path in file_paths:
        print(f"Processing: {file_path}")
        
        if dry_run:
            # For dry run, just check if file contains the pattern
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                pattern = r'<prop\s+type="context"[^>]*>.*?</prop>'
                matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                replacements_count = len(matches)
                
                if replacements_count > 0:
                    print(f"  Would remove {replacements_count} context prop tags")
                    results['total_replacements'] += replacements_count
                    results['processed_files'] += 1
                else:
                    print(f"  No context prop tags found")
                    
            except Exception as e:
                print(f"  Error reading file: {e}")
                results['failed_files'] += 1
        else:
            # Actually process the file
            success, replacements_count = remove_context_props_from_file(file_path, create_backup)
            
            if success:
                print(f"  Removed {replacements_count} context prop tags")
                results['processed_files'] += 1
                results['total_replacements'] += replacements_count
                
                file_result = {
                    'file': file_path,
                    'replacements': replacements_count,
                    'status': 'success'
                }
            else:
                print(f"  Failed to process file")
                results['failed_files'] += 1
                
                file_result = {
                    'file': file_path,
                    'replacements': 0,
                    'status': 'failed'
                }
            
            results['file_results'].append(file_result)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Remove <prop type="context"></prop> tags from multiple files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all supported files in current directory
  python remove_context_props.py

  # Find and process all TMX files in current directory
  python remove_context_props.py --extensions .tmx

  # Process all files in a specific directory
  python remove_context_props.py --directory /path/to/files

  # Process specific files
  python remove_context_props.py --files file1.tmx file2.xml

  # Dry run to see what would be changed
  python remove_context_props.py --dry-run

  # Process without creating backups
  python remove_context_props.py --no-backup
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        '--directory', '-d',
        help='Directory to search for files containing context prop tags (default: current directory)'
    )
    group.add_argument(
        '--files', '-f',
        nargs='+',
        help='Specific files to process'
    )
    
    parser.add_argument(
        '--extensions', '-e',
        nargs='+',
        default=['.tmx', '.xml', '.txt', '.html', '.htm'],
        help='File extensions to search for (default: .tmx .xml .txt .html .htm)'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create backup files'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Store original working directory
    original_cwd = os.getcwd()
    
    # Determine files to process
    if args.files:
        file_paths = args.files
        # Verify files exist
        existing_files = [f for f in file_paths if os.path.exists(f)]
        if len(existing_files) != len(file_paths):
            missing_files = set(file_paths) - set(existing_files)
            print(f"Warning: Some files not found: {missing_files}")
        file_paths = existing_files
        
        # If processing specific files, change to the directory of the first file
        if file_paths:
            first_file_dir = os.path.dirname(os.path.abspath(file_paths[0]))
            if first_file_dir:
                print(f"Changing to directory: {first_file_dir}")
                os.chdir(first_file_dir)
                # Update file paths to be relative to the new working directory
                file_paths = [os.path.basename(f) for f in file_paths]
    else:
        # Determine target directory
        if args.directory:
            target_dir = os.path.abspath(args.directory)
            print(f"Changing to directory: {target_dir}")
            os.chdir(target_dir)
            search_dir = '.'
        else:
            # Use current directory
            search_dir = '.'
            print(f"Processing files in current directory: {os.getcwd()}")
        
        # Find files in directory
        print(f"Searching for files with context prop tags in: {search_dir}")
        file_paths = find_files_with_context_props(search_dir, args.extensions)
        print(f"Found {len(file_paths)} files containing context prop tags")
    
    if not file_paths:
        print("No files to process.")
        # Restore original working directory
        os.chdir(original_cwd)
        return
    
    # Process files
    print(f"\nProcessing {len(file_paths)} files...")
    if args.dry_run:
        print("DRY RUN - No changes will be made")
    
    results = process_files(
        file_paths,
        create_backup=not args.no_backup,
        dry_run=args.dry_run
    )
    
    # Print summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Total files: {results['total_files']}")
    print(f"Successfully processed: {results['processed_files']}")
    print(f"Failed: {results['failed_files']}")
    print(f"Total replacements: {results['total_replacements']}")
    
    if args.verbose and results['file_results']:
        print(f"\nDetailed results:")
        for result in results['file_results']:
            status_icon = "✓" if result['status'] == 'success' else "✗"
            print(f"  {status_icon} {result['file']}: {result['replacements']} replacements")
    
    # Restore original working directory
    print(f"\nRestoring original working directory: {original_cwd}")
    os.chdir(original_cwd)


if __name__ == "__main__":
    main() 