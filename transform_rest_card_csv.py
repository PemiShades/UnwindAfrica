#!/usr/bin/env python
"""
Script to transform Contact Information CSV to Rest Card import format.

Usage:
    python transform_rest_card_csv.py <input_csv_path> <output_csv_path>
    
Example:
    python transform_rest_card_csv.py "path/to/Contact Information.csv" "rest_cards_import.csv"
"""
import csv
import sys
import os


def transform_csv(input_path, output_path):
    """
    Transform the Contact Information CSV to Rest Card import format.
    
    Mapping:
    - Name -> Member Name
    - Email -> Member Email  
    - Phone number(Whatsapp Preferred) -> Member Phone
    - All other columns are preserved as extra data
    """
    
    # Read the original CSV
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        original_rows = list(reader)
    
    print(f"Read {len(original_rows)} rows from {input_path}")
    
    # Define the output columns that the dashboard expects
    output_columns = [
        'Member Name',
        'Member Email', 
        'Member Phone',
        'Gender',
        'Marital Status',
        'Age Range',
        'City',
        'Local Government',
        'Instagram Handle',
        'How did you hear about us',
        'Employment Status',
        'Company Name',
        'Job Title',
        'Industry',
        'Already Community Member',
        'Founders Circle Member',
        'Why Rest Card',
        'Preferred Unwind Location',
        'Wants Discounts',
        'Agreed to Updates'
    ]
    
    # Write the transformed CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_columns)
        writer.writeheader()
        
        for row in original_rows:
            output_row = {
                'Member Name': row.get('Name', '').strip(),
                'Member Email': row.get('Email', '').strip(),
                'Member Phone': row.get('Phone number(Whatsapp Preferred)', '').strip(),
                'Gender': row.get('Gender', '').strip(),
                'Marital Status': row.get('Marital Status', '').strip(),
                'Age Range': row.get('Age Range', '').strip(),
                'City': row.get('City / State of Residence', '').strip(),
                'Local Government': row.get('Local Government', '').strip(),
                'Instagram Handle': row.get('Instagram Handle', '').strip(),
                'How did you hear about us': row.get('How did you hear about Unwind Africa?(Please write their full name — we\'d love to appreciate them later.)', '').strip(),
                'Employment Status': row.get('Employment Status', '').strip(),
                'Company Name': row.get('Company / Business Name', '').strip(),
                'Job Title': row.get('Job Title / Role', '').strip(),
                'Industry': row.get('Industry / Field of Work', '').strip(),
                'Already Community Member': row.get('Are you already part of the Unwind Africa Community?', '').strip(),
                'Founders Circle Member': row.get('Are you a Founders Circle Member?', '').strip(),
                'Why Rest Card': row.get("Why would you like to have the Unwind Africa Rest Card?", '').strip(),
                'Preferred Unwind Location': row.get('Where would you most likely want to Unwind? (Choose all that apply)', '').strip(),
                'Wants Discounts': row.get('Would you like to use your Unwind Card to enjoy discounts at partner spas, resorts, and cinemas in 2026?', '').strip(),
                'Agreed to Updates': row.get("I agree to be part of the Unwind Africa community and to receive updates.", '').strip(),
            }
            writer.writerow(output_row)
    
    print(f"Successfully wrote {len(original_rows)} rows to {output_path}")
    print(f"\nNow you can import '{output_path}' into the Rest Cards dashboard.")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        
        # Check if the CSV exists in common locations
        possible_paths = [
            os.path.expanduser("~/Downloads/Contact Information.csv"),
            os.path.expanduser("~/Downloads/Contact Information.csv.zip.76b/Contact Information.csv"),
            "Contact Information.csv",
        ]
        
        # Try to find the file
        found_path = None
        for p in possible_paths:
            if os.path.exists(p):
                found_path = p
                break
        
        if found_path:
            print(f"\nFound CSV at: {found_path}")
            output_path = "rest_cards_import.csv"
            transform_csv(found_path, output_path)
        else:
            print("\nPlease provide the input and output file paths.")
            print("Example: python transform_rest_card_csv.py \"path/to/Contact Information.csv\" \"rest_cards_import.csv\"")
    else:
        input_path = sys.argv[1]
        output_path = sys.argv[2]
        transform_csv(input_path, output_path)
