import win32com.client
import subprocess
import json
import os
from tqdm import tqdm

def scan_with_native_comments_fast(docx_path, output_path):
    abs_input = os.path.abspath(docx_path)
    abs_output = os.path.abspath(output_path)
    
    print("Launching Word in the background...")
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    
    try:
        doc = word.Documents.Open(abs_input)
        
        batch_payload = ""
        line_to_para_object = {} # We are now storing the actual COM object, not a number!
        current_line = 1
        total_paragraphs = doc.Paragraphs.Count
        
        print("\nStep 1/3: Extracting document text (O(N) COM Enumeration)...")
        
        # --- THE FIX ---
        # Instead of range(1, Count), we iterate directly over the COM collection.
        # This completely eliminates the O(N^2) counting penalty.
        for paragraph in tqdm(doc.Paragraphs, total=total_paragraphs, desc="Reading", unit="para"):
            raw_text = paragraph.Range.Text
            clean_text = raw_text.replace('\r', '').replace('\x07', '').replace('\x0b', '').replace('\n', ' ').strip()
            
            if not clean_text:
                continue
                
            batch_payload += clean_text + "\n\n"
            
            # Map Vale's line number directly to this exact Word paragraph object
            line_to_para_object[current_line] = paragraph 
            current_line += 2
            
        print("\nStep 2/3: Executing single Vale batch scan. Please wait...")
        process = subprocess.run(
            ['vale', '--ext=.md', '--output=JSON'],
            input=batch_payload,
            text=True,
            capture_output=True,
            check=False,
            encoding='utf-8'
        )
        
        if process.stdout.strip():
            vale_results = json.loads(process.stdout)
            errors = vale_results.get("stdin.md", [])
            print(f"Found {len(errors)} issues.")
            
            print("\nStep 3/3: Injecting native Word comments...")
            
            for error in tqdm(errors, desc="Commenting", unit="tag"):
                vale_line = error.get('Line')
                
                # Retrieve the exact Word paragraph object from memory
                target_paragraph = line_to_para_object.get(vale_line)
                
                if target_paragraph:
                    severity = error.get('Severity').upper()
                    match_text = error.get('Match')
                    message = error.get('Message')
                    comment_text = f"Vale {severity} -> '{match_text}': {message}"
                    
                    # Apply the comment directly to the object's Range
                    doc.Comments.Add(Range=target_paragraph.Range, Text=comment_text)
                    
        print(f"\nSaving audited document to: {abs_output}")
        doc.SaveAs2(abs_output)
        
    finally:
        doc.Close(SaveChanges=False)
        word.Quit()

if __name__ == "__main__":
    input_file = "test_clinical_doc.docx"
    output_file = "test_clinical_doc_AUDITED.docx"
    
    scan_with_native_comments_fast(input_file, output_file)