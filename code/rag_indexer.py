import os
import re
import json
import sqlite3
import pandas as pd
from pathlib import Path
import pypdf

class EvidenceIndexer:
    def __init__(self, dataset_dir='dataset', cache_file='code/evidence_cache.json'):
        self.dataset_dir = Path(dataset_dir)
        self.cache_file = Path(cache_file)
        self.evidence_files = pd.read_csv(self.dataset_dir / 'evidence_files.csv')
        self.cache = {}

    def parse_all(self, force_reload=False):
        if not force_reload and self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
            return self.cache

        parsed = {}
        for idx, row in self.evidence_files.iterrows():
            file_id = row['file_id']
            rel_path = row['file_path']
            origin = row['origin']
            captured_at = row['captured_at']
            full_path = self.dataset_dir / rel_path

            if not full_path.exists():
                continue

            suffix = full_path.suffix.lower()
            records = []

            if suffix == '.sql':
                records = self._parse_sql(full_path, file_id)
            elif suffix == '.json':
                records = self._parse_json(full_path, file_id)
            elif suffix == '.txt':
                records = self._parse_txt(full_path, file_id)
            elif suffix == '.log':
                records = self._parse_log(full_path, file_id)
            elif suffix == '.pdf':
                records = self._parse_pdf(full_path, file_id)

            parsed[file_id] = {
                'file_id': file_id,
                'file_path': rel_path,
                'origin': origin,
                'captured_at': captured_at,
                'records': records
            }

        self.cache = parsed
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        return parsed

    def _parse_sql(self, file_path, file_id):
        records = []
        conn = sqlite3.connect(':memory:')
        cur = conn.cursor()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                sql_content = f.read()
            cur.executescript(sql_content)
            
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [t[0] for t in cur.fetchall()]

            for t in tables:
                if t == 'snapshot_scope':
                    continue
                cur.execute(f"PRAGMA table_info('{t}');")
                cols = [c[1] for c in cur.fetchall()]
                cur.execute(f"SELECT * FROM '{t}';")
                for r in cur.fetchall():
                    row_dict = dict(zip(cols, r))
                    row_dict['table_name'] = t
                    row_dict['file_id'] = file_id
                    
                    # If any value is a JSON string, expand it
                    for k, val in list(row_dict.items()):
                        if isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                            try:
                                nested = json.loads(val)
                                if isinstance(nested, dict):
                                    for nk, nv in nested.items():
                                        if nk not in row_dict:
                                            row_dict[nk] = nv
                            except Exception:
                                pass
                    records.append(row_dict)
        except Exception:
            pass
        finally:
            conn.close()
        return records

    def _parse_json(self, file_path, file_id):
        records = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Case 1: snapshot bundle
            if 'snapshots' in data:
                for snap in data['snapshots']:
                    store = snap.get('data_store')
                    coll = snap.get('collection')
                    for rec in snap.get('records', []):
                        rec_copy = dict(rec)
                        rec_copy['data_store'] = store
                        rec_copy['collection'] = coll
                        rec_copy['file_id'] = file_id
                        records.append(rec_copy)
            # Case 2: service_resource_export
            elif 'service_exports' in data:
                for s_name, s_data in data['service_exports'].items():
                    if isinstance(s_data, dict):
                        for sub_k, sub_items in s_data.items():
                            if isinstance(sub_items, list):
                                for item in sub_items:
                                    item_copy = dict(item)
                                    item_copy['data_store'] = s_name
                                    item_copy['collection'] = sub_k
                                    item_copy['file_id'] = file_id
                                    
                                    # If search index queries with hits documents
                                    if sub_k == 'index_queries' and 'hits' in item_copy:
                                        hits_doc = item_copy.get('hits', {}).get('documents', [])
                                        for doc in hits_doc:
                                            doc_copy = dict(doc)
                                            doc_copy['data_store'] = s_name
                                            doc_copy['collection'] = 'documents'
                                            doc_copy['file_id'] = file_id
                                            doc_copy['query_resource_id'] = item_copy.get('resource_id')
                                            records.append(doc_copy)
                                    records.append(item_copy)
            # Case 3: list of objects
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        item_copy = dict(item)
                        item_copy['file_id'] = file_id
                        records.append(item_copy)
            # Case 4: generic dict
            elif isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                item_copy = dict(item)
                                item_copy['collection'] = k
                                item_copy['file_id'] = file_id
                                records.append(item_copy)
        except Exception:
            pass
        return records

    def _parse_txt(self, file_path, file_id):
        records = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('- ') and '|' in line:
                        parts = [p.strip() for p in line[2:].split('|')]
                        if len(parts) >= 6:
                            records.append({
                                'file_id': file_id,
                                'timestamp': parts[0],
                                'system_id': parts[1],
                                'resource_id': parts[2],
                                'category': parts[3],
                                'status': parts[4],
                                'lookup_key': parts[5]
                            })
        except Exception:
            pass
        return records

    def _parse_log(self, file_path, file_id):
        records = []
        traces = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = None
                    json_match = re.search(r'(\{.*\})', line)
                    if json_match:
                        try:
                            obj = json.loads(json_match.group(1))
                        except Exception:
                            pass
                    if not obj:
                        kv_pairs = re.findall(r'(\w+)=([^\s]+)', line)
                        if kv_pairs:
                            obj = dict(kv_pairs)
                    if not obj:
                        continue

                    obj['file_id'] = file_id
                    obj['raw_line'] = line

                    # Clean values
                    for k, v in list(obj.items()):
                        if isinstance(v, str):
                            obj[k] = v.strip('"\'')

                    tid = obj.get('trace_id')
                    if tid:
                        if tid not in traces:
                            traces[tid] = {}
                        # Accumulate identifiers
                        for key in ['subject_ref', 'subject_reference', 'lookup_key', 'correlation_key', 'subject_key', 'customer_email', 'customer_reference']:
                            if obj.get(key):
                                traces[tid][key] = obj[key]
                        # Inherit from trace
                        for k, v in traces[tid].items():
                            if k not in obj:
                                obj[k] = v

                    records.append(obj)
        except Exception:
            pass
        return records

    def _parse_pdf(self, file_path, file_id):
        records = []
        try:
            reader = pypdf.PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                full_text += (page.extract_text() or "") + "\n"
            records.append({
                'file_id': file_id,
                'content': full_text
            })
        except Exception:
            pass
        return records

if __name__ == '__main__':
    indexer = EvidenceIndexer()
    data = indexer.parse_all(force_reload=True)
    print(f"Indexed {len(data)} evidence files. Total records: {sum(len(d['records']) for d in data.values())}")
