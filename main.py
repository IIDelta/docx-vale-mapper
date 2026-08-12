import subprocess
import json
import csv
from docx import Document

def scan_document(docx_path):
    print(f"Loading document: {docx_path}")
    doc = Document(docx_path)
    all_errors = [] 
    
    for index, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if not text:
            continue
            
        print(f"Scanning Paragraph {index}...")
        
        try:
            process = subprocess.run(
                ['vale', '--ext=.md', '--output=JSON'],
                input=text,
                text=True,
                capture_output=True,
                check=False 
            )
            
            if process.stdout.strip():
                vale_results = json.loads(process.stdout)
                errors = vale_results.get("stdin", [])
                
                for error in errors:
                    error['paragraph_index'] = index 
                    error['original_text'] = text
                    all_errors.append(error)
                    print(f"  -> Found issue: {error.get('Message')}")
                    
        except FileNotFoundError:
            print("Error: The 'vale' command was not found.")
            return
            
    print(f"\nScan complete! Found {len(all_errors)} potential style issues.")
    return all_errors

# --- NEW EXPORT FUNCTION ---
def export_to_csv(errors, output_path="audit_report.csv"):
    if not errors:
        return
        
    # These are the specific columns we want in our spreadsheet
    headers = ['paragraph_index', 'Severity', 'Message', 'Match', 'original_text']
    
    print(f"Exporting results to {output_path}...")
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        # extrasaction='ignore' tells Python to drop any extra JSON data Vale sent that we don't need
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        for error in errors:
            writer.writerow(error)
    print("Export complete!")

# --- UPDATED EXECUTION BLOCK ---
if __name__ == "__main__":
    test_file = "test_clinical_doc.docx"
    # Capture the output of the scan...
    found_errors = scan_document(test_file)
    # ...and pass it to the exporter
    export_to_csv(found_errors)