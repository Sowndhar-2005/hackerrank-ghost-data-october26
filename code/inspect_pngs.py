import os
import pandas as pd
from PIL import Image
import pytesseract

df_evid = pd.read_csv('dataset/evidence_files.csv')
for idx, r in df_evid[df_evid['file_path'].str.endswith('.png')].iterrows():
    p = os.path.join('dataset', r['file_path'])
    try:
        img = Image.open(p)
        text = pytesseract.image_to_string(img)
        print(f"=== PNG {r['file_id']} ({r['file_path']}) ===")
        print(text[:300].strip())
        print("---")
    except Exception as e:
        print(f"Error on {r['file_id']}: {e}")
