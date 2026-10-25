import os
import re
import json
import pandas as pd
from datetime import datetime
from rag_indexer import EvidenceIndexer
from compiler import compile_steps

class DeletionAuditAgent:
    def __init__(self, dataset_dir='dataset'):
        self.dataset_dir = dataset_dir
        self.indexer = EvidenceIndexer(dataset_dir)
        self.evidence_cache = self.indexer.parse_all()
        
        self.df_users = pd.read_csv(os.path.join(dataset_dir, 'user_identities.csv'))
        self.df_audit = pd.read_csv(os.path.join(dataset_dir, 'user_audit_log.csv'))
        self.df_activity = pd.read_csv(os.path.join(dataset_dir, 'system_activity.csv'))
        self.df_evidence_files = pd.read_csv(os.path.join(dataset_dir, 'evidence_files.csv'))
        self.evidence_files_dict = self.df_evidence_files.set_index('file_id').to_dict('index')

        # Index activities by resource_id and by identifiers
        self._index_activity()

    def _index_activity(self):
        self.activity_by_res = {}
        for idx, row in self.df_activity.iterrows():
            res_id = row['resource_id']
            if pd.notna(res_id):
                if res_id not in self.activity_by_res:
                    self.activity_by_res[res_id] = []
                self.activity_by_res[res_id].append(row.to_dict())

    def resolve_identity(self, email, audit_at):
        """
        Traverses user_identities.csv and user_audit_log.csv (filtered <= audit_at)
        to build complete connected set of identifiers.
        """
        email_clean = email.strip().lower()
        u_row = self.df_users[self.df_users['email'].str.lower() == email_clean]
        user_id = None
        if not u_row.empty:
            user_id = u_row.iloc[0]['user_id']
        else:
            # Check audit log
            a_row = self.df_audit[
                (self.df_audit['field_name'] == 'email') & 
                ((self.df_audit['old_value'].str.lower() == email_clean) | 
                 (self.df_audit['new_value'].str.lower() == email_clean)) &
                (self.df_audit['event_time'] <= audit_at)
            ]
            if not a_row.empty:
                user_id = a_row.iloc[0]['user_id']
                u_row = self.df_users[self.df_users['user_id'] == user_id]

        if not user_id:
            # Fallback direct
            return {
                'user_id': None,
                'emails': {email_clean},
                'names': set(),
                'phones': set(),
                'email_hashes': set()
            }

        emails = {u_row.iloc[0]['email'].lower(), email_clean}
        names = {str(u_row.iloc[0]['name']).strip()}
        phones = {str(u_row.iloc[0]['phone']).strip()}
        hashes = {str(u_row.iloc[0]['email_hash']).strip()}

        user_audits = self.df_audit[
            (self.df_audit['user_id'] == user_id) & 
            (self.df_audit['event_time'] <= audit_at)
        ]
        for _, a in user_audits.iterrows():
            f = a['field_name']
            if f == 'email':
                if pd.notna(a['old_value']): emails.add(a['old_value'].strip().lower())
                if pd.notna(a['new_value']): emails.add(a['new_value'].strip().lower())
            elif f == 'name':
                if pd.notna(a['old_value']): names.add(a['old_value'].strip())
                if pd.notna(a['new_value']): names.add(a['new_value'].strip())
            elif f == 'phone':
                if pd.notna(a['old_value']): phones.add(a['old_value'].strip())
                if pd.notna(a['new_value']): phones.add(a['new_value'].strip())
            elif f == 'email_hash':
                if pd.notna(a['old_value']): hashes.add(a['old_value'].strip())
                if pd.notna(a['new_value']): hashes.add(a['new_value'].strip())

        return {
            'user_id': user_id,
            'emails': emails,
            'names': names,
            'phones': phones,
            'email_hashes': hashes
        }

    def is_deletion_request(self, text):
        t = text.lower()
        negatives = [
            'leave the account active', 'not asking for deletion', 'keep the account as it is',
            'do not close the account', 'without removing any of my records', 'marketing lists only',
            'not a request to erase', 'leave my profile and purchase history in place',
            'continue using the service', "please don't delete or change anything",
            "please don’t delete or change anything", 'do not delete', "don't delete", 'dont delete'
        ]
        for neg in negatives:
            if neg in t:
                return False
        return True

    def audit_case(self, case_row):
        case_id = case_row['case_id']
        email = case_row['email']
        requested_at = case_row['requested_at']
        reported_at = case_row['reported_at']
        reported_status = case_row['reported_status']
        audit_at = case_row['audit_at']
        request_text = case_row['request_text']

        # GOAL: Audit case_id at audit_at
        # PLAN: Check authorization first
        if not self.is_deletion_request(request_text):
            return {
                'case_id': case_id,
                'deletion_status': 'NOT_APPLICABLE',
                'steps_json': '[]'
            }

        # ACT: Resolve identity
        ident = self.resolve_identity(email, audit_at)
        user_id = ident['user_id']
        emails = ident['emails']
        phones = ident['phones']
        hashes = ident['email_hashes']

        # OBSERVE: Scan evidence up to audit_at
        # Filter evidence files captured <= audit_at
        valid_evid_files = {}
        for fid, finfo in self.evidence_cache.items():
            if finfo['captured_at'] <= audit_at:
                valid_evid_files[fid] = finfo

        # Scan for records
        findings = []
        verified_compliant = []
        seen_res = set()

        # Helper to check if a record matches this user
        def matches_user(rec):
            # Check user_id / customer_reference / subject_reference
            for ref_col in ['user_id', 'customer_reference', 'subject_reference', 'subject_key', 'lookup_key']:
                v = rec.get(ref_col)
                if v and isinstance(v, str):
                    if user_id and v == user_id:
                        return True
                    if v.lower() in emails:
                        return True
            for em_col in ['email', 'requester_email', 'owner_email', 'customer_email', 'lookup_key']:
                v = rec.get(em_col)
                if v and isinstance(v, str) and v.lower() in emails:
                    return True
            for ph_col in ['phone', 'requester_phone', 'owner_phone']:
                v = rec.get(ph_col)
                if v and str(v).strip() in phones:
                    return True
            for h_col in ['email_hash']:
                v = rec.get(h_col)
                if v and str(v).strip() in hashes:
                    return True
            # Check content for pdf/txt
            if 'content' in rec:
                c = rec['content']
                for em in emails:
                    if em in c.lower():
                        return True
                if user_id and user_id in c:
                    return True
            return False

        # Sort valid evidence files by captured_at descending to prioritize newest observation <= audit_at
        sorted_evids = sorted(valid_evid_files.values(), key=lambda x: x['captured_at'], reverse=True)

        for finfo in sorted_evids:
            fid = finfo['file_id']
            for rec in finfo['records']:
                if not matches_user(rec):
                    continue

                # Identify system and resource
                sys_id = rec.get('system_id') or rec.get('data_store') or finfo.get('origin')
                res_id = rec.get('resource_id')
                table = rec.get('table_name', '')
                coll = rec.get('collection', '')

                # Infer system_id if needed
                if not sys_id or sys_id in ['records_assurance_snapshot_bundle', 'central_observability_export', 'service_resource_export']:
                    if 'profile' in table or 'profile' in coll or 'account' in str(res_id):
                        sys_id = 'account_service'
                    elif 'search' in table or 'search' in coll or 'search' in str(res_id):
                        sys_id = 'search_service'
                    elif 'analytics' in table or 'analytics' in coll or 'analytics' in str(res_id):
                        sys_id = 'analytics_platform'
                    elif 'support' in table or 'support' in coll or 'support' in str(res_id):
                        sys_id = 'support_platform'
                    elif 'export' in table or 'export' in coll or 'export' in str(res_id):
                        sys_id = 'export_service'
                    elif 'connector' in table or 'data_flow' in coll or 'data_flow' in str(res_id):
                        sys_id = 'integration_service'
                    elif 'backup' in table or 'backup' in coll or 'backup' in str(res_id):
                        sys_id = 'backup_service'
                    elif 'audit' in table or 'audit' in coll or 'audit_record' in str(res_id):
                        sys_id = 'security_service'
                    elif 'tombstone' in table or 'tombstone' in coll or 'tombstone' in str(res_id):
                        sys_id = 'identity_service'

                if not res_id:
                    # Look inside content or line
                    if 'content' in rec:
                        m = re.search(r'(support_\w+|account_\w+|export_\w+)', rec['content'])
                        if m:
                            res_id = m.group(1)
                    elif 'raw_line' in rec:
                        m = re.search(r'resource_id=([^\s]+)', rec['raw_line'])
                        if m:
                            res_id = m.group(1)

                if not res_id or not sys_id:
                    continue

                # Process state & rule
                # ...
        return None
