# batch_processor.py
import os
import random
import json
import pickle
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import gc

from method_manager import MethodManager
from generators import ChromatogramGenerator, PDFReportGenerator, ORGFileGenerator

class BatchProcessor:
    """Handles batch processing of chromatography data."""

    # --- Audit trail storage (streaming, low-memory) -------------------------
    # Legacy format (v1): a single pickle containing a Python list of entries.
    # New format (v2): append-only pickle stream of entry dicts.
    #
    # We must support reading BOTH formats because users may already have data.
    _AUDIT_PROTOCOL_VERSION = 2

    @staticmethod
    def _log_critical_event(message):
        """Log critical audit events to syslog file."""
        audit_dir = os.path.join('_internal', 'audit_data')
        syslog_file = os.path.join(audit_dir, '.syslog')
        os.makedirs(audit_dir, exist_ok=True)
        
        try:
            with open(syslog_file, 'ab') as f:
                event = f"[{datetime.now().isoformat()}] CRITICAL: {message}\n"
                f.write(event.encode('utf-8'))
        except Exception:
            pass

    @staticmethod
    def log_audit_entry(company_name, sample_name, date_acquired, date_processed):
        """
        Log audit entry in a low-memory append-only binary format (pickle stream).

        This avoids loading the full audit history into memory for every entry,
        which caused severe slowdowns and memory pressure during large batch runs.
        """
        audit_dir = os.path.join('_internal', 'audit_data')
        audit_file = os.path.join(audit_dir, 'audit.trl')
        os.makedirs(audit_dir, exist_ok=True)
        
        # Format dates as MM/DD/YYYY HH:MM:SS AM/PM TZ
        def format_audit_datetime(dt):
            if isinstance(dt, (datetime, pd.Timestamp)):
                dt = pd.to_datetime(dt)
                return dt.strftime('%d/%m/%Y %I:%M:%S %p') + ' PKT'
            return str(dt)
        
        entry = {
            'company_name': company_name,
            'sample_name': sample_name,
            'vial': '1',  # Default value instead of empty
            'injection': '1',  # Default value instead of empty
            'sample_type': 'Unknown',  # Default value instead of empty
            'processed_channel_descr': 'Channel A',  # Default value instead of empty
            'date_acquired': format_audit_datetime(date_acquired),
            'date_processed': format_audit_datetime(date_processed),
            'timestamp': datetime.now().isoformat()
        }

        try:
            BatchProcessor._append_audit_entry(audit_file, entry)
        except Exception as e:
            BatchProcessor._log_critical_event(f"Failed to write audit file: {e}")

    @staticmethod
    def _append_audit_entry(audit_file, entry):
        """
        Append a single audit entry to audit_file.
        If the file is in legacy list format, it is converted once to streaming format.
        """
        # Convert legacy file (single pickled list) to streaming entries once.
        if os.path.exists(audit_file) and os.path.getsize(audit_file) > 0:
            if BatchProcessor._is_legacy_audit_file(audit_file):
                BatchProcessor._convert_legacy_audit_file(audit_file)

        with open(audit_file, 'ab') as f:
            pickle.dump(entry, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _is_legacy_audit_file(audit_file):
        """
        Best-effort detection:
        - Legacy format starts with one pickle whose top-level object is a list.
        - New format starts with first pickle being a dict (entry).
        """
        try:
            with open(audit_file, 'rb') as f:
                first = pickle.load(f)
            return isinstance(first, list)
        except Exception:
            # If unreadable, treat as non-legacy; append will still work (or fail)
            return False

    @staticmethod
    def _convert_legacy_audit_file(audit_file):
        """Convert legacy pickled-list file into append-only stream format in-place."""
        try:
            with open(audit_file, 'rb') as f:
                data = pickle.load(f)
            if not isinstance(data, list):
                return
        except Exception:
            return

        tmp_path = audit_file + ".tmp"
        try:
            with open(tmp_path, 'wb') as out:
                for entry in data:
                    if isinstance(entry, dict):
                        pickle.dump(entry, out, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp_path, audit_file)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    @staticmethod
    def process_excel_file(excel_path, method_path, org_output_dir, pdf_output_dir, status_callback=None):
        errors = []
        success = 0

        if not os.path.exists(method_path):
            return 0, [f"Method file not found: {method_path}"]
        if not os.path.exists(excel_path):
            return 0, [f"Excel file not found: {excel_path}"]
        os.makedirs(org_output_dir, exist_ok=True)
        os.makedirs(pdf_output_dir, exist_ok=True)

        try:
            method_data = MethodManager.load_method(method_path)
        except Exception as e:
            return 0, [f"Failed to load method file: {e}"]

        # Read file with fallbacks
        df = None
        if excel_path.lower().endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(excel_path, engine='openpyxl')
            except Exception:
                try:
                    df = pd.read_excel(excel_path, engine='xlrd')
                except Exception:
                    pass
        if df is None:
            # try CSV encodings
            for enc in ('utf-8', 'latin-1', 'iso-8859-1'):
                try:
                    df = pd.read_csv(excel_path, encoding=enc)
                    break
                except Exception:
                    df = None
            if df is None:
                return 0, [f"Failed to read input file: {excel_path}"]

        df.columns = [str(c).strip() for c in df.columns]

        required_cols = ['Sample Name', 'Peak ID', 'Area']
        for c in required_cols:
            if c not in df.columns:
                return 0, [f"Missing required column: {c}"]

        if 'Date' not in df.columns:
            df['Date'] = pd.NA
        if 'Time' not in df.columns:
            df['Time'] = pd.NA

        df = BatchProcessor._process_datetime(df, method_data)

        grouped = df.groupby('Sample Name', sort=False)
        total_samples = len(grouped)
        processed = 0

        for sample_name, sample_df in grouped:
            try:
                if status_callback:
                    status_callback(f"Processing sample {sample_name} ({processed+1}/{total_samples})")
                # Remove .copy() to use a view instead of duplicating the DataFrame
                BatchProcessor._process_sample(sample_name, sample_df, method_data, org_output_dir, pdf_output_dir)
                success += 1
            except Exception as e:
                errors.append(f"{sample_name}: {e}")
                # Continue processing other samples even if one fails
            processed += 1
            # Aggressive cleanup after each sample
            del sample_df
            gc.collect()

        if status_callback:
            status_callback("Batch processing finished.")
        
        # Clean up the main DataFrame and grouped object immediately
        del df
        del grouped
        del method_data
        gc.collect()
        
        return success, errors

    @staticmethod
    def _process_datetime(df, method_data):
        """
        Fill DateTime once per Sample Name group using the rule:
        - If any row in the group contains a parsable Date + Time, use its datetime as the group's DateTime.
        - Otherwise compute:
            GroupDateTime = PreviousGroupDateTime + RunTime + random(5..10%) of RunTime
          where RunTime is obtained from method_data (minutes) and converted to seconds
          before applying the 5-10% randomization.
        - If there is no previous group anchor, use current system time as the first group's DateTime.

        After computing/choosing the group's DateTime, assign the same DateTime to every row belonging to that Sample Name.
        """
        run_time_str = method_data.get('method', {}).get('runtime', '10')
        try:
            run_time_min = float(run_time_str)
        except Exception:
            run_time_min = 10.0

        # runtime in seconds
        run_time_sec = run_time_min * 60.0

        df = df.reset_index(drop=True)

        # We'll iterate groups in appearance order and assign one DateTime per group
        prev_group_dt = None

        # Ensure 'Sample Name' exists; if not, treat each row as its own group
        if 'Sample Name' not in df.columns:
            df['Sample Name'] = df.index.astype(str)

        grouped = df.groupby('Sample Name', sort=False)

        for sample_name, grp in grouped:
            # locate first parsable datetime within the group (Date + Time preferred)
            anchor_dt = None

            for idx in grp.index:
                date_val = df.at[idx, 'Date'] if 'Date' in df.columns else pd.NA
                time_val = df.at[idx, 'Time'] if 'Time' in df.columns else pd.NA

                parsed = None
                if pd.notna(date_val) and pd.notna(time_val):
                    try:
                        parsed = pd.to_datetime(f"{date_val} {time_val}", errors='coerce', utc=False, dayfirst=True)
                        if pd.isna(parsed):
                            parsed = None
                    except Exception:
                        parsed = None
                elif pd.notna(date_val) and pd.isna(time_val):
                    # date only -> parse date (time will be midnight)
                    try:
                        parsed = pd.to_datetime(date_val, errors='coerce', utc=False, dayfirst=True)
                        if pd.isna(parsed):
                            parsed = None
                    except Exception:
                        parsed = None

                if parsed is not None:
                    anchor_dt = pd.to_datetime(parsed)
                    break

            if anchor_dt is None:
                # need to compute from previous group's datetime (or now if none)
                if prev_group_dt is None:
                    anchor_dt = pd.Timestamp.now()
                else:
                    rnd_pct = random.uniform(0.05, 0.10)  # 5-10%
                    delta_secs = run_time_sec * (1.0 + rnd_pct)
                    anchor_dt = pd.to_datetime(prev_group_dt) + pd.Timedelta(seconds=delta_secs)

            # assign the group's anchor to all rows in that group
            for idx in grp.index:
                df.at[idx, 'DateTime'] = anchor_dt

            # update prev_group_dt
            prev_group_dt = anchor_dt

        return df

    @staticmethod
    def _process_sample(sample_name, sample_df, method_data, org_output_dir, pdf_output_dir):
        try:
            method_params = method_data.get('method', {})
            sample_info_md = method_data.get('sample_info', {})
            peaks_config = method_data.get('peaks', [])

            try:
                run_time = float(method_params.get('runtime', 10))
            except Exception:
                run_time = 10.0

            peaks_info = []
            for _, row in sample_df.iterrows():
                peak_id = int(row['Peak ID'])
                area = float(row['Area'])
                peak_config = None
                for pc in peaks_config:
                    if int(pc.get('peak_number', -1)) == peak_id:
                        peak_config = pc
                        break

                if peak_config:
                    base_rt = float(peak_config.get('retention_time', peak_id))
                    peak_name = peak_config.get('peak_name', f"Peak {peak_id}")
                    tailing = float(peak_config.get('tailing_factor', 1.0))
                    plates = float(peak_config.get('theoretical_plates', 10000))
                else:
                    base_rt = float(peak_id * 2.0)
                    peak_name = f"Peak {peak_id}"
                    tailing = 1.0
                    plates = 10000.0

                rt_variation = base_rt * 0.02
                rt_rand = base_rt + random.uniform(-rt_variation, rt_variation)

                peaks_info.append({
                    'peak_id': peak_id,
                    'peak_name': peak_name,
                    'retention_time': rt_rand,
                    'area': area,
                    'tailing_base': tailing,
                    'plates_base': plates
                })

            # Generate chromatogram (this returns time, signal, peak_details)
            chromatogram_data = ChromatogramGenerator.generate_chromatogram_data(peaks_info, run_time)
            t_array, signal_array, base_peak_details = chromatogram_data

            # Build results table and enrich peak details
            rows = []
            enriched_peaks = []
            multiple_peaks = len(peaks_info) > 1

            base_cols = ['Peak No.', 'Peak Name', 'Retention Time', 'Area', 'Tailing Factor', 'Theoretical Plates']
            if multiple_peaks:
                cols = base_cols + ['Resolution']
            else:
                cols = base_cols

            prev_rt = None

            for p_info, pd in zip(peaks_info, base_peak_details):
                rt_value = float(pd.get('retention_time', p_info.get('retention_time', 0.0)))
                area_value = float(pd.get('area', p_info.get('area', 0.0)))

                tailing_random = float(p_info.get('tailing_base', 1.0)) * random.uniform(0.9, 1.1)
                plates_random = int(max(5000, float(p_info.get('plates_base', 10000.0)) * random.uniform(0.9, 1.1)))

                row = {
                    'Peak No.': p_info['peak_id'],
                    'Peak Name': p_info['peak_name'],
                    'Retention Time': f"{rt_value:.3f}",
                    'Area': f"{int(round(area_value))}",
                    'Tailing Factor': f"{tailing_random:.3f}",
                    'Theoretical Plates': f"{plates_random}"
                }

                if multiple_peaks:
                    if prev_rt is None:
                        row['Resolution'] = ''
                    else:
                        resolution_value = random.uniform(5.0, 9.9)
                        row['Resolution'] = f"{resolution_value:.3f}"

                rows.append(row)

                enriched = {
                    'peak_id': p_info['peak_id'],
                    'name': pd.get('name', p_info.get('peak_name')),
                    'retention_time': float(rt_value),
                    'height': float(pd.get('height', 0.0)),
                    'area': float(area_value),
                    'tailing_factor': float(round(tailing_random, 3)),
                    'theoretical_plates': plates_random
                }
                enriched_peaks.append(enriched)

                prev_rt = rt_value

            import pandas as pd
            results_table = pd.DataFrame(rows, columns=cols)

            safe_name = "".join([c if c.isalnum() or c in (' ', '_', '-', '.') else '_' for c in sample_name]).strip()
            org_path = os.path.join(org_output_dir, f"{safe_name}.org")
            pdf_path = os.path.join(pdf_output_dir, f"{safe_name}.pdf")

            dt_obj = sample_df.iloc[0]['DateTime']
            if isinstance(dt_obj, (pd.Timestamp, datetime)):
                sample_datetime = pd.to_datetime(dt_obj).strftime('%d/%m/%Y %I:%M:%S %p')
            else:
                sample_datetime = str(dt_obj)

            gen_time_ts = pd.Timestamp.now()
            generation_time = gen_time_ts.strftime('%d/%m/%Y %I:%M:%S %p')

            sample_info = {
                'project_name': sample_info_md.get('project_name', 'N/A'),
                'company_name': sample_info_md.get('company', 'N/A'),
                'analyst': sample_info_md.get('analyst', 'N/A'),
                'datetime': sample_datetime,
                'sample_name': sample_name,
                'generation_time': generation_time,
                'data_file': org_path
            }

            report_method_data = {
                'instrument': method_params.get('instrument', 'N/A'),
                'column_temp': method_params.get('column_temp', 'N/A'),
                'column_part': method_params.get('column_part', 'N/A'),
                'detector': method_params.get('detector', 'N/A'),
                'wavelength': method_params.get('wavelength', 'N/A'),
                'runtime': method_params.get('runtime', 'N/A')
            }

            chromatogram_data_for_output = (t_array, signal_array, enriched_peaks)

            PDFReportGenerator.generate_pdf(pdf_path, report_method_data, sample_info, enriched_peaks, chromatogram_data_for_output, results_table)
            ORGFileGenerator.save_org_file(org_path, report_method_data, sample_info, chromatogram_data_for_output, results_table)
            
            date_acquired = dt_obj
            date_processed = dt_obj + timedelta(minutes=run_time)
            BatchProcessor.log_audit_entry(sample_info['company_name'], sample_name, date_acquired, date_processed)

            # Explicit memory cleanup - delete ALL large objects immediately
            del chromatogram_data
            del chromatogram_data_for_output
            del t_array
            del signal_array
            del base_peak_details
            del enriched_peaks
            del rows
            del results_table
            del sample_info
            del report_method_data
            del peaks_info
            del sample_df  # Early deletion of the sample DataFrame
            import matplotlib.pyplot as plt
            plt.close('all')  # Ensure all matplotlib figures are closed
            gc.collect()

        except Exception as e:
            # Log critical event and re-raise to be caught in the caller
            BatchProcessor._log_critical_event(f"Sample processing failed for {sample_name}: {e}")
            raise e