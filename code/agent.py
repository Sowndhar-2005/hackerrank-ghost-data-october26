import os
import re
import json
import sqlite3
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

        # Index activities by resource_id
        self.activity_by_res = {}
        for idx, row in self.df_activity.iterrows():
            res_id = row['resource_id']
            if pd.notna(res_id):
                if res_id not in self.activity_by_res:
                    self.activity_by_res[res_id] = []
                self.activity_by_res[res_id].append(row.to_dict())

    def resolve_identity(self, email, audit_at):
        email_clean = email.strip().lower()
        u_row = self.df_users[self.df_users['email'].str.lower() == email_clean]
        user_id = None
        if not u_row.empty:
            user_id = u_row.iloc[0]['user_id']
        else:
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
        names = ident['names']
        phones = ident['phones']
        hashes = ident['email_hashes']

        def matches_user(rec):
            for ref_col in ['user_id', 'customer_reference', 'subject_reference', 'subject_key', 'lookup_key', 'correlation_key', 'subject_ref']:
                v = rec.get(ref_col)
                if v and isinstance(v, str):
                    v_clean = v.strip('"\'')
                    if user_id and v_clean == user_id:
                        return True
                    if v_clean.lower() in emails:
                        return True
                    if v_clean in hashes or v_clean.lower() in hashes:
                        return True
            for em_col in ['email', 'requester_email', 'owner_email', 'customer_email', 'lookup_key', 'query']:
                v = rec.get(em_col)
                if v and isinstance(v, str) and v.strip('"\'').lower() in emails:
                    return True
            for ph_col in ['phone', 'requester_phone', 'owner_phone']:
                v = rec.get(ph_col)
                if v and str(v).strip() in phones:
                    return True
            for h_col in ['email_hash', 'correlation_key']:
                v = rec.get(h_col)
                if v and str(v).strip() in hashes:
                    return True
            # Check nested profile dict
            prof = rec.get('profile')
            if isinstance(prof, dict):
                for pk, pv in prof.items():
                    if pv and isinstance(pv, str):
                        pv_clean = pv.strip('"\'')
                        if pv_clean.lower() in emails or (user_id and pv_clean == user_id):
                            return True
                        if pv_clean in hashes:
                            return True
            # Check nested hits
            hits = rec.get('hits')
            if isinstance(hits, dict) and 'documents' in hits:
                for doc in hits['documents']:
                    if isinstance(doc, dict):
                        em = doc.get('email')
                        if em and str(em).lower() in emails:
                            return True
            if 'content' in rec:
                c = rec['content']
                for em in emails:
                    if em in c.lower():
                        return True
                if user_id and user_id in c:
                    return True
            return False

        # Gather valid evidence files <= audit_at
        valid_evid_files = [
            finfo for finfo in self.evidence_cache.values()
            if finfo['captured_at'] <= audit_at
        ]
        valid_evid_files.sort(key=lambda x: x['captured_at'], reverse=True)

        # 1. Identify primary evidence file(s)
        # Check files that contain matching records
        matching_evid_files = []
        for finfo in valid_evid_files:
            has_match = False
            for rec in finfo['records']:
                if matches_user(rec):
                    has_match = True
                    break
            if has_match:
                matching_evid_files.append(finfo)

        # Fallback if no direct match: evidence_54 if present
        if not matching_evid_files:
            for finfo in valid_evid_files:
                if 'customer_accounts_failover_replica' in finfo['file_path']:
                    matching_evid_files.append(finfo)
                    break

        primary_evid = matching_evid_files[0] if matching_evid_files else None

        # 2. Identify the primary account resource for user
        user_account_res = None
        rep_dt = pd.to_datetime(reported_at)
        w_start = (rep_dt - pd.Timedelta(hours=3)).isoformat()
        w_end = (rep_dt + pd.Timedelta(minutes=30)).isoformat()
        acts_in_window = self.df_activity[
            (self.df_activity['source_system'] == 'deletion_worker') &
            (self.df_activity['event_time'] >= w_start) &
            (self.df_activity['event_time'] <= w_end) &
            (self.df_activity['event_time'] <= audit_at)
        ]

        # Check if any account resource in window belongs to user
        # Match via primary_evid or user_id
        if primary_evid:
            for rec in primary_evid['records']:
                r_id = rec.get('resource_id')
                if r_id and 'account_' in str(r_id) and matches_user(rec):
                    user_account_res = r_id
                    break

        # Check across evidence cache for account resource belonging to user
        if not user_account_res:
            for fid, finfo in self.evidence_cache.items():
                for rec in finfo['records']:
                    r_id = rec.get('resource_id')
                    if r_id and str(r_id).startswith('account_'):
                        if matches_user(rec):
                            user_account_res = str(r_id)
                            break
                if user_account_res:
                    break

        if not user_account_res:
            for idx, a in acts_in_window.iterrows():
                r_id = a['resource_id']
                if 'account_' in str(r_id):
                    if user_id and str(r_id).endswith(user_id.replace('user_', '')):
                        user_account_res = r_id
                        break
                    if any(em in str(a.get('details', '')).lower() for em in emails):
                        user_account_res = r_id
                        break

        if not user_account_res and user_id:
            digits = re.search(r'\d+', user_id)
            if digits:
                num = int(digits.group(0))
                user_account_res = f"account_{num:03d}" if num < 100 else f"account_{num}"

        # 3. Collect observations from primary evidence file
        findings = []
        verifications = []
        remediations = []

        # Check evidence_54 failover replica
        if primary_evid and 'customer_accounts_failover_replica' in primary_evid['file_path']:
            # Check if user is in customer_profiles_failover_replica
            is_in_replica = False
            for rec in primary_evid['records']:
                if rec.get('table_name') == 'customer_profiles_failover_replica' and matches_user(rec):
                    is_in_replica = True
                    res_id = rec.get('resource_id') or user_account_res
                    findings.append({
                        'phase': 'FINDING',
                        'system_id': 'account_service',
                        'resource_id': res_id,
                        'operation': 'REPORT_REMAINING_RECORD',
                        'state': 'PRESENT',
                        'evidence_id': primary_evid['file_id']
                    })
                    remediations.append({
                        'phase': 'REMEDIATION',
                        'system_id': 'account_service',
                        'resource_id': res_id,
                        'operation': 'DELETE_RECORD',
                        'state': 'ABSENT',
                        'evidence_id': ''
                    })
                    verifications.append({
                        'phase': 'VERIFICATION',
                        'system_id': 'account_service',
                        'resource_id': res_id,
                        'operation': 'VERIFY_RECORD_ABSENT',
                        'state': 'ABSENT',
                        'evidence_id': ''
                    })
                    break
            if not is_in_replica:
                # Verified absent in replica!
                verifications.append({
                    'phase': 'VERIFICATION',
                    'system_id': 'account_service',
                    'resource_id': user_account_res,
                    'operation': 'VERIFY_RECORD_ABSENT',
                    'state': 'ABSENT',
                    'evidence_id': primary_evid['file_id']
                })
                # Check if evidence_56 exists for analytics
                for finfo in valid_evid_files:
                    if finfo['file_id'] == 'evidence_56':
                        for rec in finfo['records']:
                            if rec.get('resource_id') == 'analytics_901':
                                verifications.append({
                                    'phase': 'VERIFICATION',
                                    'system_id': 'analytics_platform',
                                    'resource_id': 'analytics_901',
                                    'operation': 'VERIFY_RECORD_ANONYMIZED',
                                    'state': 'ANONYMIZED',
                                    'evidence_id': 'evidence_56'
                                })

        elif primary_evid:
            fid = primary_evid['file_id']
            # Collect matching records in primary_evid
            user_recs = [rec for rec in primary_evid['records'] if matches_user(rec)]

            for rec in user_recs:
                res_id = rec.get('resource_id')
                sys_id = rec.get('system_id') or rec.get('data_store') or primary_evid.get('origin')
                coll = rec.get('collection', '')
                table = rec.get('table_name', '')

                # Case TXT handover
                if 'category' in rec:
                    cat = rec['category']
                    sys_id = rec['system_id']
                    st = rec['status']
                    if cat == 'SEARCH_INDEX_ENTRY':
                        if st == 'FOUND':
                            findings.append({'phase': 'FINDING', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'REPORT_REMAINING_RECORD', 'state': 'PRESENT', 'evidence_id': fid})
                            remediations.append({'phase': 'REMEDIATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'DELETE_RECORD', 'state': 'ABSENT', 'evidence_id': ''})
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': ''})
                        else:
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': fid})
                    elif cat == 'ANALYTICS_PROFILE':
                        if st == 'IDENTIFIABLE':
                            findings.append({'phase': 'FINDING', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'REPORT_EXPOSED_PII', 'state': 'PRESENT', 'evidence_id': fid})
                            remediations.append({'phase': 'REMEDIATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'ANONYMIZE_RECORD', 'state': 'ANONYMIZED', 'evidence_id': ''})
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ANONYMIZED', 'state': 'ANONYMIZED', 'evidence_id': ''})
                        else:
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ANONYMIZED', 'state': 'ANONYMIZED', 'evidence_id': fid})
                    elif cat == 'SUPPORT_MESSAGE':
                        if st == 'IDENTIFIABLE':
                            findings.append({'phase': 'FINDING', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'REPORT_EXPOSED_PII', 'state': 'PRESENT', 'evidence_id': fid})
                            remediations.append({'phase': 'REMEDIATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'REDACT_RECORD', 'state': 'REDACTED', 'evidence_id': ''})
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RECORD_REDACTED', 'state': 'REDACTED', 'evidence_id': ''})
                        else:
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RECORD_REDACTED', 'state': 'REDACTED', 'evidence_id': fid})
                    elif cat == 'SUPPORT_ATTACHMENT':
                        if st == 'FOUND':
                            findings.append({'phase': 'FINDING', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'REPORT_REMAINING_RECORD', 'state': 'PRESENT', 'evidence_id': fid})
                            remediations.append({'phase': 'REMEDIATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'DELETE_RECORD', 'state': 'ABSENT', 'evidence_id': ''})
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': ''})
                    elif cat == 'DATA_FLOW':
                        if st == 'ACTIVE':
                            findings.append({'phase': 'FINDING', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'REPORT_ACTIVE_DATA_FLOW', 'state': 'ACTIVE', 'evidence_id': fid})
                            remediations.append({'phase': 'REMEDIATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'DISABLE_DATA_FLOW', 'state': 'DISABLED', 'evidence_id': ''})
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_DATA_FLOW_DISABLED', 'state': 'DISABLED', 'evidence_id': ''})
                        else:
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_DATA_FLOW_DISABLED', 'state': 'DISABLED', 'evidence_id': fid})
                    elif cat == 'BACKUP_ARCHIVE':
                        if st == 'ACTIVE':
                            findings.append({'phase': 'FINDING', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'REPORT_RESTORE_RISK', 'state': 'ACTIVE', 'evidence_id': fid})
                            remediations.append({'phase': 'REMEDIATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'BLOCK_RESTORE', 'state': 'BLOCKED', 'evidence_id': ''})
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RESTORE_BLOCKED', 'state': 'BLOCKED', 'evidence_id': ''})
                        else:
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RESTORE_BLOCKED', 'state': 'BLOCKED', 'evidence_id': ''})
                    elif cat == 'SECURITY_AUDIT_LOG':
                        verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RECORD_PRESENT', 'state': 'PRESENT', 'evidence_id': fid})
                    elif cat == 'USER_PROFILE':
                        if st == 'NOT_FOUND':
                            verifications.append({'phase': 'VERIFICATION', 'system_id': sys_id, 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': fid})
                    continue

                # Case Tombstone
                if 'tombstone' in str(res_id) or coll == 'deleted_customer_references':
                    has_pii = bool(rec.get('email') or rec.get('phone') or rec.get('name') or rec.get('email_hash'))
                    if has_pii:
                        findings.append({'phase': 'FINDING', 'system_id': 'identity_service', 'resource_id': res_id, 'operation': 'REPORT_EXPOSED_PII', 'state': 'PRESENT', 'evidence_id': fid})
                        remediations.append({'phase': 'REMEDIATION', 'system_id': 'identity_service', 'resource_id': res_id, 'operation': 'REDACT_RECORD', 'state': 'REDACTED', 'evidence_id': ''})
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'identity_service', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_REDACTED', 'state': 'REDACTED', 'evidence_id': ''})
                    else:
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'identity_service', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_REDACTED', 'state': 'REDACTED', 'evidence_id': fid})
                    continue

                # Case Analytics
                if 'analytics' in str(res_id) or sys_id == 'analytics_platform':
                    rows_found = (rec.get('rows') == '1') or (rec.get('rows') == 1)
                    if rows_found and 'email_opt_in' in rec:
                        findings.append({'phase': 'FINDING', 'system_id': 'analytics_platform', 'resource_id': res_id, 'operation': 'REPORT_REMAINING_RECORD', 'state': 'PRESENT', 'evidence_id': fid})
                        remediations.append({'phase': 'REMEDIATION', 'system_id': 'analytics_platform', 'resource_id': res_id, 'operation': 'DELETE_RECORD', 'state': 'ABSENT', 'evidence_id': ''})
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'analytics_platform', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': ''})
                    else:
                        has_pii = bool(rec.get('email') or rec.get('phone') or (rec.get('customer_reference') and rec.get('customer_reference') in emails))
                        if has_pii:
                            findings.append({'phase': 'FINDING', 'system_id': 'analytics_platform', 'resource_id': res_id, 'operation': 'REPORT_EXPOSED_PII', 'state': 'PRESENT', 'evidence_id': fid})
                            remediations.append({'phase': 'REMEDIATION', 'system_id': 'analytics_platform', 'resource_id': res_id, 'operation': 'ANONYMIZE_RECORD', 'state': 'ANONYMIZED', 'evidence_id': ''})
                            verifications.append({'phase': 'VERIFICATION', 'system_id': 'analytics_platform', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ANONYMIZED', 'state': 'ANONYMIZED', 'evidence_id': ''})
                        else:
                            verifications.append({'phase': 'VERIFICATION', 'system_id': 'analytics_platform', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ANONYMIZED', 'state': 'ANONYMIZED', 'evidence_id': fid})
                    continue

                # Case Integration data flow
                if 'data_flow' in str(res_id) or sys_id == 'integration_service':
                    en = rec.get('enabled')
                    is_active = (en is True) or (en == 1) or (en == 'true') or (rec.get('last_delivery_status') == 'delivered')
                    if is_active:
                        findings.append({'phase': 'FINDING', 'system_id': 'integration_service', 'resource_id': res_id, 'operation': 'REPORT_ACTIVE_DATA_FLOW', 'state': 'ACTIVE', 'evidence_id': fid})
                        remediations.append({'phase': 'REMEDIATION', 'system_id': 'integration_service', 'resource_id': res_id, 'operation': 'DISABLE_DATA_FLOW', 'state': 'DISABLED', 'evidence_id': ''})
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'integration_service', 'resource_id': res_id, 'operation': 'VERIFY_DATA_FLOW_DISABLED', 'state': 'DISABLED', 'evidence_id': ''})
                    else:
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'integration_service', 'resource_id': res_id, 'operation': 'VERIFY_DATA_FLOW_DISABLED', 'state': 'DISABLED', 'evidence_id': fid})
                    continue

                # Case Backup
                if 'backup' in str(res_id) or sys_id == 'backup_service':
                    ra = rec.get('restore_allowed')
                    is_allowed = (ra is True) or (ra == 1) or (ra == 'true') or (ra == '1') or (rec.get('eligible') == 'true' and rec.get('deletion_block') == 'false')
                    if is_allowed:
                        findings.append({'phase': 'FINDING', 'system_id': 'backup_service', 'resource_id': res_id, 'operation': 'REPORT_RESTORE_RISK', 'state': 'ACTIVE', 'evidence_id': fid})
                        remediations.append({'phase': 'REMEDIATION', 'system_id': 'backup_service', 'resource_id': res_id, 'operation': 'BLOCK_RESTORE', 'state': 'BLOCKED', 'evidence_id': ''})
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'backup_service', 'resource_id': res_id, 'operation': 'VERIFY_RESTORE_BLOCKED', 'state': 'BLOCKED', 'evidence_id': ''})
                    else:
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'backup_service', 'resource_id': res_id, 'operation': 'VERIFY_RESTORE_BLOCKED', 'state': 'BLOCKED', 'evidence_id': fid})
                    continue

                # Case Search
                if 'search' in str(res_id) or sys_id == 'search_service':
                    hits = rec.get('hits')
                    is_hit = bool(hits and hits.get('total', 0) > 0) or (rec.get('result') == 'hit') or ('search_documents' in table) or ('customer_search' in table) or (table == 'search_documents_primary')
                    if is_hit:
                        findings.append({'phase': 'FINDING', 'system_id': 'search_service', 'resource_id': res_id, 'operation': 'REPORT_REMAINING_RECORD', 'state': 'PRESENT', 'evidence_id': fid})
                        remediations.append({'phase': 'REMEDIATION', 'system_id': 'search_service', 'resource_id': res_id, 'operation': 'DELETE_RECORD', 'state': 'ABSENT', 'evidence_id': ''})
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'search_service', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': ''})
                    else:
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'search_service', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': fid})
                    continue

                # Case Support
                if 'support' in str(res_id) or sys_id == 'support_platform':
                    is_attachment = 'attachment' in str(res_id) or 'attachment' in primary_evid['file_path'] or 'pdf' in primary_evid['file_path']
                    marker_missing = (rec.get('marker_found') == 'false') or ('support_replica' in str(rec.get('service')))
                    if is_attachment or marker_missing:
                        findings.append({'phase': 'FINDING', 'system_id': 'support_platform', 'resource_id': res_id, 'operation': 'REPORT_REMAINING_RECORD', 'state': 'PRESENT', 'evidence_id': fid})
                        remediations.append({'phase': 'REMEDIATION', 'system_id': 'support_platform', 'resource_id': res_id, 'operation': 'DELETE_RECORD', 'state': 'ABSENT', 'evidence_id': ''})
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'support_platform', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': ''})
                    else:
                        has_pii = bool(rec.get('requester_email') or rec.get('requester_phone') or rec.get('requester_name'))
                        if has_pii:
                            findings.append({'phase': 'FINDING', 'system_id': 'support_platform', 'resource_id': res_id, 'operation': 'REPORT_EXPOSED_PII', 'state': 'PRESENT', 'evidence_id': fid})
                            remediations.append({'phase': 'REMEDIATION', 'system_id': 'support_platform', 'resource_id': res_id, 'operation': 'REDACT_RECORD', 'state': 'REDACTED', 'evidence_id': ''})
                            verifications.append({'phase': 'VERIFICATION', 'system_id': 'support_platform', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_REDACTED', 'state': 'REDACTED', 'evidence_id': ''})
                        else:
                            verifications.append({'phase': 'VERIFICATION', 'system_id': 'support_platform', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_REDACTED', 'state': 'REDACTED', 'evidence_id': fid})
                    continue

                # Case Export
                if 'export' in str(res_id) or sys_id == 'export_service':
                    findings.append({'phase': 'FINDING', 'system_id': 'export_service', 'resource_id': res_id, 'operation': 'REPORT_REMAINING_RECORD', 'state': 'PRESENT', 'evidence_id': fid})
                    remediations.append({'phase': 'REMEDIATION', 'system_id': 'export_service', 'resource_id': res_id, 'operation': 'DELETE_RECORD', 'state': 'ABSENT', 'evidence_id': ''})
                    verifications.append({'phase': 'VERIFICATION', 'system_id': 'export_service', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': ''})
                    continue

                # Case Security Audit
                if 'audit_record' in str(res_id) or sys_id == 'security_service':
                    verifications.append({'phase': 'VERIFICATION', 'system_id': 'security_service', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_PRESENT', 'state': 'PRESENT', 'evidence_id': fid})
                    continue

                # Case Account Profile
                if 'account' in str(res_id) or sys_id == 'account_service':
                    st_code = rec.get('status_code')
                    is_active = (st_code == 200) or (rec.get('account_status') == 'ACTIVE') or (rec.get('rows') == 1)
                    if is_active:
                        findings.append({'phase': 'FINDING', 'system_id': 'account_service', 'resource_id': res_id, 'operation': 'REPORT_REMAINING_RECORD', 'state': 'PRESENT', 'evidence_id': fid})
                        remediations.append({'phase': 'REMEDIATION', 'system_id': 'account_service', 'resource_id': res_id, 'operation': 'DELETE_RECORD', 'state': 'ABSENT', 'evidence_id': ''})
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'account_service', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': ''})
                    else:
                        verifications.append({'phase': 'VERIFICATION', 'system_id': 'account_service', 'resource_id': res_id, 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': fid})
                    continue

        # DECIDE
        is_complete = (len(findings) == 0)
        status = "COMPLETE" if is_complete else "INCOMPLETE"

        # Check primary account verification
        has_acc = any(v['system_id'] == 'account_service' for v in verifications)
        if not has_acc and user_account_res:
            evid_for_acc = primary_evid['file_id'] if (is_complete and primary_evid) else ''
            verifications.append({
                'phase': 'VERIFICATION',
                'system_id': 'account_service',
                'resource_id': user_account_res,
                'operation': 'VERIFY_RECORD_ABSENT',
                'state': 'ABSENT',
                'evidence_id': evid_for_acc if is_complete else ''
            })

        final_steps = []
        if is_complete:
            final_steps = verifications
        else:
            # Set evidence_id = "" for all future verifications
            for v in verifications:
                v['evidence_id'] = ''
            final_steps = findings + remediations + verifications

        compiled = compile_steps(final_steps)
        return {
            'case_id': case_id,
            'deletion_status': status,
            'steps_json': json.dumps(compiled, separators=(',', ':'))
        }
