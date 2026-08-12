import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import pythoncom
import win32com.client
import subprocess
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REGRESSION_TEST_RUNNER = PROJECT_ROOT / "tests" / "runregressiontests.py"

def run_regression_gate() -> None:
    """Run all approved Vale fixtures before auditing a live document."""

    command = [
        sys.executable,
        str(REGRESSION_TEST_RUNNER),
    ]

    process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    if process.returncode != 0:
        output = process.stdout.strip()
        errors = process.stderr.strip()

        details = "\n\n".join(
            value
            for value in [output, errors]
            if value
        )

        raise RuntimeError(
            "The Takeda Vale regression suite failed. "
            "The live-document audit was not started.\n\n"
            f"{details}"
        )


# --- THE CORE ENGINE ---
def run_scan_thread(docx_path, output_path, status_var, progress_var, start_btn):
    """This runs in the background so the GUI doesn't freeze."""
    # 1. We MUST initialize COM for this specific background thread
    pythoncom.CoInitialize() 

    status_var.set("Running approved rule regression tests...")
    progress_var.set(0)

    run_regression_gate()

    status_var.set("Regression tests passed. Launching Word...")
    progress_var.set(5)
    
    try:
        abs_input = os.path.abspath(docx_path)
        abs_output = os.path.abspath(output_path)
        
        status_var.set("Launching Word in the background...")
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        
        try:
            doc = word.Documents.Open(abs_input)
            
            batch_payload = ""
            line_to_para_object = {}
            current_line = 1
            total_paragraphs = doc.Paragraphs.Count
            
            status_var.set(f"Step 1/3: Extracting {total_paragraphs} paragraphs...")
            progress_var.set(0)
            
            # Extract text
            for i, paragraph in enumerate(doc.Paragraphs, start=1):
                raw_text = paragraph.Range.Text
                clean_text = raw_text.replace('\r', '').replace('\x07', '').replace('\x0b', '').replace('\n', ' ').strip()
                
                if clean_text:
                    batch_payload += clean_text + "\n\n"
                    line_to_para_object[current_line] = paragraph 
                    current_line += 2
                
                # Update the GUI progress bar (throttled to avoid freezing the UI)
                if i % 50 == 0 or i == total_paragraphs:
                    progress_var.set((i / total_paragraphs) * 33) # Takes up first 33% of the bar
                    
            status_var.set("Step 2/3: Executing Vale style scan...")
            process = subprocess.run(
                ['vale', '--ext=.md', '--output=JSON'],
                input=batch_payload,
                text=True,
                capture_output=True,
                check=False,
                encoding='utf-8'
            )
            progress_var.set(66) # Scan complete, bump bar to 66%
            
            if process.stdout.strip():
                vale_results = json.loads(process.stdout)
                errors = vale_results.get("stdin.md", [])
                
                status_var.set(f"Step 3/3: Injecting {len(errors)} comments...")
                total_errors = len(errors)
                
                if total_errors > 0:
                    for idx, error in enumerate(errors, start=1):
                        vale_line = error.get('Line')
                        target_paragraph = line_to_para_object.get(vale_line)
                        
                        if target_paragraph:
                            severity = error.get('Severity', 'suggestion').upper()
                            match_text = error.get('Match', '')
                            message = error.get('Message', '')
                            comment_text = f"Vale {severity} -> '{match_text}': {message}"
                            
                            doc.Comments.Add(Range=target_paragraph.Range, Text=comment_text)
                            
                        # Update progress for the final 33% of the bar
                        progress_var.set(66 + ((idx / total_errors) * 34))
                        
            status_var.set("Saving audited document...")
            doc.SaveAs2(abs_output)
            status_var.set("Complete! Document is ready.")
            progress_var.set(100)
            messagebox.showinfo("Success", f"Scan complete.\nSaved to:\n{abs_output}")
            
        finally:
            doc.Close(SaveChanges=False)
            word.Quit()
            
    except Exception as e:
        status_var.set("Error occurred during scan.")
        messagebox.showerror("Error", str(e))
    finally:
        # 2. We MUST uninitialize COM before the thread dies
        pythoncom.CoUninitialize()
        # Re-enable the start button
        start_btn.config(state=tk.NORMAL)

# --- THE GUI BUILDER ---
def select_input(entry_widget, output_entry_widget):
    filepath = filedialog.askopenfilename(filetypes=[("Word Documents", "*.docx")])
    if filepath:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filepath)
        
        # Auto-generate the output filepath
        directory, filename = os.path.split(filepath)
        name, ext = os.path.splitext(filename)
        out_filepath = os.path.join(directory, f"{name}_AUDITED{ext}")
        
        output_entry_widget.delete(0, tk.END)
        output_entry_widget.insert(0, out_filepath)

def select_output(entry_widget):
    filepath = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word Documents", "*.docx")])
    if filepath:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filepath)

def start_process(input_entry, output_entry, status_var, progress_var, start_btn):
    in_path = input_entry.get()
    out_path = output_entry.get()
    
    if not in_path or not out_path:
        messagebox.showwarning("Missing Files", "Please select both input and output files.")
        return
        
    if not os.path.exists(in_path):
        messagebox.showerror("File Not Found", "The selected input file does not exist.")
        return

    # Disable button to prevent multiple clicks
    start_btn.config(state=tk.DISABLED)
    status_var.set("Starting...")
    progress_var.set(0)
    
    # Launch the background thread
    thread = threading.Thread(
        target=run_scan_thread, 
        args=(in_path, out_path, status_var, progress_var, start_btn),
        daemon=True
    )
    thread.start()

def build_gui():
    root = tk.Tk()
    root.title("Medical Writer - Vale Auditor")
    root.geometry("600x300")
    root.resizable(False, False)
    
    # Padding and layout configuration
    frame = ttk.Frame(root, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Input Row
    ttk.Label(frame, text="Target Protocol (.docx):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    input_entry = ttk.Entry(frame, width=50)
    input_entry.grid(row=0, column=1, padx=10, pady=(0, 5))
    ttk.Button(frame, text="Browse", command=lambda: select_input(input_entry, output_entry)).grid(row=0, column=2, pady=(0, 5))
    
    # Output Row
    ttk.Label(frame, text="Output Audited File:").grid(row=1, column=0, sticky=tk.W, pady=10)
    output_entry = ttk.Entry(frame, width=50)
    output_entry.grid(row=1, column=1, padx=10, pady=10)
    ttk.Button(frame, text="Browse", command=lambda: select_output(output_entry)).grid(row=1, column=2, pady=10)
    
    # Progress and Status
    status_var = tk.StringVar()
    status_var.set("Ready.")
    ttk.Label(frame, textvariable=status_var).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
    
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
    progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
    
    # Action Button
    start_btn = ttk.Button(
        frame, 
        text="Run Audit", 
        command=lambda: start_process(input_entry, output_entry, status_var, progress_var, start_btn)
    )
    start_btn.grid(row=4, column=0, columnspan=3, pady=20)
    
    root.mainloop()

if __name__ == "__main__":
    build_gui()