import pypdf
import os
import pandas as pd

df_evid = pd.read_csv('dataset/evidence_files.csv')
for idx, r in df_evid[df_evid['file_path'].str.endswith('.pdf')].iterrows():
    p = os.path.join('dataset', r['file_path'])
    reader = pypdf.PdfReader(p)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    print(f"=== PDF {r['file_id']} ({r['file_path']}) ===")
    print(text[:300].strip())
    print("---")
