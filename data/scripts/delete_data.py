import os
import shutil
import argparse

def cleanup_data_directories(project_dir: str, include_raw: bool = False) -> None:
    """
    Clean up the data directories to start processing from scratch.
    
    Parameters:
    project_dir (str): Root directory of the project
    include_raw (bool): Whether to delete the raw data files too (default: False)
    """
    # Setup paths
    processed_dir = os.path.join(project_dir, "data", "processed", "fine_tuning")
    raw_dir = os.path.join(project_dir, "data", "raw")
    
    # Clean up processed directory
    if os.path.exists(processed_dir):
        print(f"Removing processed data in: {processed_dir}")
        try:
            shutil.rmtree(processed_dir)
            print("✓ Successfully removed processed data")
        except Exception as e:
            print(f"Error removing processed data: {e}")
    else:
        print(f"No processed data found at: {processed_dir}")
    
    # If requested, also clean up raw data
    if include_raw:
        # Don't delete the raw directory, just its contents except .gitkeep
        if os.path.exists(raw_dir):
            print(f"Removing raw data in: {raw_dir}")
            try:
                for item in os.listdir(raw_dir):
                    # Skip .gitkeep file
                    if item == '.gitkeep':
                        continue
                    
                    item_path = os.path.join(raw_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                print("✓ Successfully removed raw data")
            except Exception as e:
                print(f"Error removing raw data: {e}")
        else:
            print(f"No raw data directory found at: {raw_dir}")
    
    # Recreate the processed directory structure
    os.makedirs(processed_dir, exist_ok=True)
    print(f"✓ Recreated directory structure")
    print("Cleanup complete! You can now run the data extraction process again.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up data directories to start processing from scratch.")
    parser.add_argument('--all', action='store_true', help='Remove both processed and raw data')
    parser.add_argument('--project-dir', type=str, default=None, 
                        help='Project root directory (default: auto-detect from script location)')
    
    args = parser.parse_args()
    
    # Determine project root
    if args.project_dir:
        project_dir = args.project_dir
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(script_dir))
    
    cleanup_data_directories(project_dir, include_raw=args.all)