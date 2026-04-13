import os
import pandas as pd
import glob
from tqdm import tqdm

def process_cricsheet_data(data_dir, output_dir):
    all_files = glob.glob(os.path.join(data_dir, '*.csv'))
    
    # Separate info files and delivery files
    info_files = [f for f in all_files if '_info' in f]
    delivery_files = [f for f in all_files if '_info' not in f and f.split('/')[-1].split('.')[0].isdigit()]
    
    print(f"Found {len(info_files)} info files and {len(delivery_files)} delivery files.")
    
    # Process deliveries
    deliveries_list = []
    print("Processing deliveries...")
    for f in tqdm(delivery_files):
        df = pd.read_csv(f)
        deliveries_list.append(df)
        
    deliveries_df = pd.concat(deliveries_list, ignore_index=True)
    deliveries_df.to_csv(os.path.join(output_dir, 'deliveries.csv'), index=False)
    print("Saved deliveries.csv")
    
    # Process match info
    print("Processing match info...")
    matches_list = []
    for f in tqdm(info_files):
        # The info CSVs from Cricsheet often have key-value pairs
        # We need to parse them into a single row per match
        df = pd.read_csv(f, names=['type', 'key', 'value', 'extra', 'extra2'])
        match_id = f.split('/')[-1].split('_')[0]
        
        info_dict = {'match_id': match_id}
        for _, row in df.iterrows():
            if row['key'] in ['team', 'player', 'registry']:
                continue
            if row['type'] == 'info':
                # some values have extra parts
                key = row['key']
                val = row['value']
                
                # handle teams specifically since there are two 'team' keys typically
                if key == 'team':
                    pass # Handled differently or by index if needed
                else:
                    if key not in info_dict:
                        info_dict[key] = val
                    else:
                        # Append if duplicate key (like umpire)
                        if not isinstance(info_dict[key], list):
                            info_dict[key] = [info_dict[key]]
                        info_dict[key].append(val)
        matches_list.append(info_dict)
        
    matches_df = pd.DataFrame(matches_list)
    matches_df.to_csv(os.path.join(output_dir, 'matches.csv'), index=False)
    print("Saved matches.csv")

if __name__ == "__main__":
    process_cricsheet_data('data_cricsheet', '.')
