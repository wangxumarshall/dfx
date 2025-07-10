import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import requests
import PyPDF2 # Will be indirectly used by PatentFileParser
import markdown as md # Used for PDF generation and in PatentFileParser
# import docx # python-docx - Handled by PatentFileParser
# from PIL import Image # For OCR with pytesseract - Handled by PatentFileParser
# import pytesseract # For OCR - Handled by PatentFileParser
import json
import time
import uuid
from flask import flash, current_app # Added current_app for factory pattern
import shutil # For operations like deleting a directory tree
from threading import Thread # For background tasks

# --- New Module Imports ---
from modules.patent_parser import PatentFileParser
from modules.clue_acquisition import ClueAcquirer
from modules.evidence_matcher import EvidenceMatcher
from modules.reliability_assessor import ReliabilityAssessor
from modules.report_generator import ReportGenerator

# --- Global dictionary to track analysis status (remains global for simplicity for now) ---
# In a more complex app, this might be managed by a service or database.
analysis_status_db = {} # report_filename -> {"status": "processing/completed/failed", "error": "...", "current_step": "...", "progress_message": "..."}


# --- Utility Functions ---
# allowed_file can use current_app.config if settings are loaded into app.config
def allowed_file(filename, app_config):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app_config['ALLOWED_EXTENSIONS']


# --- Application Factory ---
def create_app():
    app = Flask(__name__)

    # --- Configuration Loading ---
    try:
        from config import main_config as settings_module
        app.config.from_object(settings_module) # Load main_config into app.config
        # For consistency, let's alias settings_module to settings for utility functions if needed
        # However, best practice is to use app.config directly within request contexts or pass it.
    except ImportError:
        print("ERROR: config/main_config.py not found or has errors. Using fallback app configurations.")
        # Fallback configurations directly on app.config
        app.config['OPENAI_API_KEY'] = "YOUR_FALLBACK_OPENAI_KEY"
        app.config['SERP_API_KEY'] = "YOUR_FALLBACK_SERP_KEY"
        app.config['UPLOAD_FOLDER'] = 'uploads_fallback'
        app.config['REPORTS_FOLDER'] = 'reports_fallback'
        app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'md', 'txt', 'zip'}
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
        app.config['SIMULATE_LLM'] = True
        app.config['SIMULATE_LLM_DELAY'] = 2
        app.config['TESSERACT_CMD'] = 'tesseract'
        # Ensure these are also set if main_config is missing
        app.config['PATENT_PARSER_CONFIG'] = {} # Placeholder
        app.config['CLUE_ACQUISITION_CONFIG'] = {} # Placeholder
        app.config['EVIDENCE_MATCHER_CONFIG'] = {} # Placeholder
        app.config['RELIABILITY_ASSESSOR_CONFIG'] = {} # Placeholder
        app.config['REPORT_GENERATOR_CONFIG'] = {} # Placeholder

    # Load module-specific configs (can be done here or within modules if they access app.config)
    # For simplicity, modules currently load their own .py configs directly.
    # If we wanted them to use app.config, we'd load them here:
    # try:
    #     from config import patent_parser_config
    #     app.config.from_object(patent_parser_config)
    # except ImportError: print("WARN: patent_parser_config.py not found")
    # ... and so on for other module configs.
    # For now, modules' direct import of their configs is simpler and already implemented.

    app.secret_key = os.urandom(24) # Needed for flash messages

    # Ensure upload and report directories exist using app.config
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)

    # Create a session-specific uploads sub-directory parent
    # This path should also use app.config['UPLOAD_FOLDER']
    app.config['SESSION_UPLOADS_PARENT'] = os.path.join(app.config['UPLOAD_FOLDER'], 'session_data')
    os.makedirs(app.config['SESSION_UPLOADS_PARENT'], exist_ok=True)


    # --- Instantiate Core Modules ---
    # These instances can be stored on the app object if they need to be accessed across requests
    # and are configured based on app.config, or if their instantiation is costly.
    # For now, modules mostly self-configure by importing their config files.
    # If they needed app.config, we would pass it: app.patent_parser = PatentFileParser(app.config)

    # Storing on 'g' is not suitable as they are needed outside request context by the thread.
    # Making them part of the app context or simply instantiating them globally/per-call (if lightweight)
    # For the background thread, it's easier if these are accessible.
    # Let's define them here, and the background thread function will be defined within create_app
    # or receive these instances as arguments.

    # These are instantiated once when the app is created.
    # Modules currently load their own configs, which is fine for now.
    # If a module's config depends on main_config, it should import main_config.
    app.patent_parser = PatentFileParser()
    app.clue_acquirer = ClueAcquirer() # ClueAcquirer instantiates its own PatentFileParser
    app.evidence_matcher = EvidenceMatcher()
    app.reliability_assessor = ReliabilityAssessor()
    app.report_generator = ReportGenerator()

    # --- Register Blueprints (if any) ---
    # Example: from .routes import main_blueprint; app.register_blueprint(main_blueprint)

    # --- Define Routes (or import from a routes file/blueprint) ---
    # Routes need access to 'app' for decorators like @app.route
    # We can define them within create_app or ensure they use a Blueprint.
    # For simplicity in this refactor, routes will be defined here.

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/upload', methods=['POST'])
    def upload_and_analyze():
        """
        Handles file uploads (patent and evidence) and URL inputs.
        Triggers the analysis process using the new modular pipeline.
        """
        # Use current_app.config for all configurations
        config = current_app.config

        if request.method == 'POST':
            patent_file = request.files.get('patent_file')
            patent_url = request.form.get('patent_url', '').strip()
            evidence_files = request.files.getlist('evidence_files[]')

            # --- TODO: Add new fields from frontend for "Online Mining Mode" ---
            # search_target_company = request.form.get('target_company', '').strip()
            # search_excluded_companies = request.form.get('excluded_companies', '').strip() # Needs parsing if comma-separated
            # search_focus_areas = request.form.get('focus_areas', '').strip()
            # current_mode = request.form.get('analysis_mode', 'local') # 'local' or 'online_search'

            session_id = str(uuid.uuid4())
            session_upload_dir = os.path.join(config['SESSION_UPLOADS_PARENT'], session_id)
            os.makedirs(session_upload_dir, exist_ok=True)

            patent_doc_path = None
            processed_evidence_sources = [] # This will store paths for local, or search params for API

            # 1. Process Patent File/URL
            if patent_file and patent_file.filename != '' and allowed_file(patent_file.filename, config):
                filename = secure_filename(patent_file.filename)
                patent_doc_path = os.path.join(session_upload_dir, "patent_" + filename)
                patent_file.save(patent_doc_path)
            elif patent_url:
                try:
                    response = requests.get(patent_url, timeout=10)
                    response.raise_for_status()
                    url_filename = secure_filename(patent_url.split('/')[-1] or "patent_from_url.html")
                    if not any(url_filename.endswith(ext) for ext in ['.html', '.htm', '.txt', '.pdf']):
                        url_filename += ".html"
                    patent_doc_path = os.path.join(session_upload_dir, "patent_" + url_filename)
                    with open(patent_doc_path, 'wb') as f: f.write(response.content)
                except requests.RequestException as e:
                    flash(f"专利URL下载失败: {e}", "danger")
                    shutil.rmtree(session_upload_dir, ignore_errors=True)
                    return redirect(url_for('index'))
            else:
                flash("必须提供专利文件或专利URL。", "danger")
                shutil.rmtree(session_upload_dir, ignore_errors=True)
                return redirect(url_for('index'))

            # 2. Process Evidence (depends on mode - for now, still using local file evidence)
            # This part will need significant change when online search mode is fully integrated
            # For now, assume 'local' mode for evidence files.

            temp_evidence_dir = os.path.join(session_upload_dir, "evidence_files")
            os.makedirs(temp_evidence_dir, exist_ok=True)

            if evidence_files and evidence_files[0].filename != '':
                is_zip_upload = any(f.filename.lower().endswith('.zip') for f in evidence_files)
                if is_zip_upload:
                    # ... (ZIP processing logic - unchanged, but uses 'config' for allowed_file)
                    # Ensure allowed_file calls pass 'config'
                    zip_file = next((f for f in evidence_files if f.filename.lower().endswith('.zip')), None)
                    if zip_file and allowed_file(zip_file.filename, config):
                        zip_filename = secure_filename(zip_file.filename)
                        zip_path = os.path.join(session_upload_dir, zip_filename)
                        zip_file.save(zip_path)
                        try:
                            import zipfile
                            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                for member in zip_ref.namelist():
                                    if allowed_file(member, config) and not member.startswith('__MACOSX'):
                                        if not member.endswith('/'):
                                            target_path = os.path.join(temp_evidence_dir, os.path.basename(member))
                                            source = zip_ref.open(member)
                                            target_file_handle = open(target_path, "wb")
                                            with source, target_file_handle:
                                                shutil.copyfileobj(source, target_file_handle)
                                            processed_evidence_sources.append(target_path)
                            os.remove(zip_path)
                        except zipfile.BadZipFile:
                            flash("上传的侵权线索ZIP文件无效或已损坏。", "danger"); shutil.rmtree(session_upload_dir, ignore_errors=True); return redirect(url_for('index'))
                        except Exception as e:
                            flash(f"解压侵权线索ZIP文件时出错: {e}", "danger"); shutil.rmtree(session_upload_dir, ignore_errors=True); return redirect(url_for('index'))
                    else: flash("提供的侵权线索ZIP文件类型不允许。", "warning")

                if not processed_evidence_sources: # If not a zip or zip failed
                    for file_item in evidence_files:
                        if file_item and file_item.filename != '' and allowed_file(file_item.filename, config) and not file_item.filename.lower().endswith('.zip'):
                            filename = secure_filename(file_item.filename)
                            evidence_file_path = os.path.join(temp_evidence_dir, filename)
                            file_item.save(evidence_file_path)
                            processed_evidence_sources.append(evidence_file_path)

            # If no evidence files are provided for local mode, processed_evidence_sources will be empty.
            # The ClueAcquirer's local mode should handle an empty list if this means "no local files to parse".
            # Or, if ClueAcquirer expects a directory, we could pass temp_evidence_dir.
            # For now, pass the list of files. If it's empty, ClueAcquirer should return empty list of clues.

            # For 'online_search' mode, processed_evidence_sources would be a dict of search params
            # e.g., {'search_terms': '...', 'target_company': '...'}


            timestamp = time.strftime("%Y%m%d-%H%M%S")
            report_base_name = f"report_{timestamp}_{session_id[:8]}.md"
            report_filepath = os.path.join(config['REPORTS_FOLDER'], report_base_name)

            analysis_status_db[report_base_name] = {"status": "processing", "current_step": "upload", "progress_message": "文件接收完毕，准备开始分析..."}

            # Pass module instances to the thread
            # Note: if modules are not thread-safe or share state in a non-thread-safe way, this could be an issue.
            # For now, assuming their methods are re-entrant or they manage their own state appropriately per call.
            # The app context is not available in the new thread by default.
            # Pass necessary config values if modules can't access current_app.config.
            # However, our modules currently load their own configs or main_config directly.

            analysis_thread = Thread(target=run_full_analysis_pipeline,
                                     args=(current_app._get_current_object(), # Pass the app instance for context if needed by thread
                                           patent_doc_path,
                                           processed_evidence_sources, # List of file paths for local mode
                                           # current_mode, # Would determine how processed_evidence_sources is interpreted
                                           report_filepath,
                                           report_base_name,
                                           session_id,
                                           session_upload_dir # For cleanup
                                           ))
            analysis_thread.start()

            # Simplified estimated time for now
            estimated_time_seconds = 120 + len(processed_evidence_sources) * 30
            if config['SIMULATE_LLM']:
                estimated_time_seconds = config['SIMULATE_LLM_DELAY'] * (2 + len(processed_evidence_sources) if processed_evidence_sources else 2)

            return redirect(url_for('analyzing_page', report_filename=report_base_name, estimated_time=estimated_time_seconds))
        return redirect(url_for('index')) # Should not happen if POST

    # --- Analysis Pipeline (to be run in a thread) ---
    # This function needs access to the app's module instances.
    # It will be defined within create_app or receive them as arguments.
    def run_full_analysis_pipeline(app_instance, # Pass Flask app instance
                                   patent_doc_path_local,
                                   evidence_sources_local, # List of file paths for local mode
                                   # analysis_mode, # 'local' or 'online_search'
                                   output_report_filepath,
                                   report_base_name_key,
                                   session_id_local,
                                   session_upload_dir_local
                                   ):
        # Since this runs in a separate thread, use the passed app_instance to access modules
        # and app.config if necessary (though modules mostly load their own configs).
        # For modules attached to app_instance (e.g., app_instance.patent_parser):
        patent_parser_instance = app_instance.patent_parser
        clue_acquirer_instance = app_instance.clue_acquirer
        evidence_matcher_instance = app_instance.evidence_matcher
        reliability_assessor_instance = app_instance.reliability_assessor
        report_generator_instance = app_instance.report_generator

        try:
            analysis_status_db[report_base_name_key]["current_step"] = "patent_parsing"
            analysis_status_db[report_base_name_key]["progress_message"] = "正在解析专利文件..."

            raw_patent_text = patent_parser_instance.parse_file(patent_doc_path_local)
            if isinstance(raw_patent_text, str) and raw_patent_text.startswith("[") and raw_patent_text.endswith("]"): # Error from parser
                raise ValueError(f"专利文件解析失败: {raw_patent_text}")

            analysis_status_db[report_base_name_key]["current_step"] = "patent_summarization"
            analysis_status_db[report_base_name_key]["progress_message"] = "正在提取专利核心信息 (LLM)..."
            patent_summary_data = evidence_matcher_instance.summarize_patent_with_llm(raw_patent_text)
            if patent_summary_data.get("error"):
                raise ValueError(f"专利摘要提取失败 (LLM): {patent_summary_data.get('details', patent_summary_data['error'])}")

            analysis_status_db[report_base_name_key]["current_step"] = "clue_acquisition"
            analysis_status_db[report_base_name_key]["progress_message"] = "正在获取和解析侵权线索..."

            # --- TODO: Adapt clue acquisition based on analysis_mode ---
            # if analysis_mode == "local":
            # For now, assuming evidence_sources_local is a list of file paths for local mode
            acquired_clues = clue_acquirer_instance.acquire_clues(local_sources=evidence_sources_local)
            # elif analysis_mode == "online_search":
            #     acquired_clues = clue_acquirer_instance.acquire_clues(search_params=evidence_sources_local) # evidence_sources would be a dict
            # else:
            #     raise ValueError(f"Unsupported analysis mode: {analysis_mode}")

            valid_clues = [clue for clue in acquired_clues if not clue.get("error") and clue.get("parsed_text")]
            if not valid_clues and acquired_clues: # Some clues acquired but all had errors or no text
                 print(f"WARN: Pipeline: No valid clues with parsed text obtained from {len(acquired_clues)} sources.")
                 # Decide if this is a fatal error or if we can proceed to report generation with no evidence.
                 # For now, let's allow it to proceed and generate a report indicating no evidence was successfully analyzed.


            analysis_status_db[report_base_name_key]["current_step"] = "evidence_matching"
            analysis_status_db[report_base_name_key]["progress_message"] = f"准备匹配 {len(valid_clues)} 条有效线索..."

            all_evidence_analyses_results = []
            for i, clue in enumerate(valid_clues):
                analysis_status_db[report_base_name_key]["progress_message"] = f"正在匹配线索 {i+1}/{len(valid_clues)}: {clue.get('source_identifier', '未知线索')}..."
                match_result = evidence_matcher_instance.match_evidence(
                    patent_summary_data,
                    clue.get("parsed_text"),
                    clue.get("source_identifier")
                )
                if match_result.get("error"):
                    print(f"ERROR: Pipeline: Failed to match clue {clue.get('source_identifier')}: {match_result.get('details', match_result['error'])}")
                    # Add error info to results, or skip? For now, include it.
                    match_result['clue_identifier'] = clue.get('source_identifier', 'ErrorClue')
                    all_evidence_analyses_results.append(match_result) # Append error result
                    continue # Skip reliability for this one

                if reliability_assessor_instance.enabled:
                    analysis_status_db[report_base_name_key]["progress_message"] = f"评估线索 {i+1} 的分析可靠性..."
                    match_result_with_reliability = reliability_assessor_instance.assess_reliability(match_result)
                    all_evidence_analyses_results.append(match_result_with_reliability)
                else:
                    # Ensure 'reliability_assessment' key exists with disabled status if not run
                    match_result['reliability_assessment'] = {'status': 'disabled', 'message': '评估模块未启用'}
                    all_evidence_analyses_results.append(match_result)

            analysis_status_db[report_base_name_key]["current_step"] = "report_generation"
            analysis_status_db[report_base_name_key]["progress_message"] = "正在生成分析报告..."

            report_metadata_info = {
                "task_id": session_id_local,
                "generation_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            final_report_md = report_generator_instance.generate_report(
                patent_summary_data,
                all_evidence_analyses_results,
                report_metadata_info
            )

            with open(output_report_filepath, 'w', encoding='utf-8') as f:
                f.write(final_report_md)

            analysis_status_db[report_base_name_key]["status"] = "completed"
            analysis_status_db[report_base_name_key]["progress_message"] = "分析报告已生成！"

        except Exception as e:
            print(f"ERROR: Pipeline: Analysis pipeline failed for report {report_base_name_key}: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging
            analysis_status_db[report_base_name_key]["status"] = "failed"
            analysis_status_db[report_base_name_key]["error"] = f"分析流程出错: {str(e)}"
            # Optionally, write a simple error report
            try:
                with open(output_report_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# 分析失败\n\n任务ID: {session_id_local}\n错误详情: {str(e)}\n\n请检查日志获取更多信息。")
            except Exception as report_err:
                print(f"ERROR: Pipeline: Failed to write error report: {report_err}")
        finally:
            if os.path.exists(session_upload_dir_local):
                shutil.rmtree(session_upload_dir_local, ignore_errors=True)
                print(f"INFO: Pipeline: Cleaned up session directory: {session_upload_dir_local}")


    @app.route('/analyzing/<report_filename>')
    def analyzing_page(report_filename):
        estimated_time = request.args.get('estimated_time', 180)
        return render_template('analyzing.html', report_filename=report_filename, estimated_time=estimated_time)

    @app.route('/status/<report_filename>')
    def check_analysis_status(report_filename):
        status_info = analysis_status_db.get(report_filename, {"status": "unknown", "error": "Analysis ID not found."})
        return jsonify(status_info)

    @app.route('/report/<report_filename>')
    def view_report(report_filename):
        # Use current_app.config here
        report_path_md = os.path.join(current_app.config['REPORTS_FOLDER'], secure_filename(report_filename))
        try:
            with open(report_path_md, 'r', encoding='utf-8') as f:
                report_content_md = f.read()
            report_title = report_content_md.split('\n')[0].replace('#', '').strip() or "分析报告"
            return render_template('report.html',
                                   report_content_md=report_content_md,
                                   report_title=report_title,
                                   report_filename_raw=report_filename)
        except FileNotFoundError:
            return render_template('report.html', error_message=f"报告文件 {report_filename} 未找到或尚未生成。", report_filename_raw=report_filename)
        except Exception as e:
            return render_template('report.html', error_message=f"读取报告时出错: {e}", report_filename_raw=report_filename)

    @app.route('/download_report/<report_filename>')
    def download_report(report_filename):
        # Use current_app.config here
        reports_folder = current_app.config['REPORTS_FOLDER']
        report_path = os.path.join(reports_folder, secure_filename(report_filename))
        as_attachment = request.args.get('as_attachment', 'true').lower() == 'true' # Ensure boolean
        format_type = request.args.get('format', 'md').lower()

        if not os.path.exists(report_path):
            flash("请求的报告文件不存在。", "danger")
            return redirect(url_for('index'))

        if format_type == 'pdf':
            try:
                from weasyprint import HTML
                with open(report_path, 'r', encoding='utf-8') as f_md:
                    md_content = f_md.read()

                html_content_for_pdf = md.markdown(md_content, extensions=['tables', 'fenced_code'])
                # Using a more complete HTML structure for WeasyPrint
                html_string = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>
    body {{ font-family: sans-serif; line-height: 1.6; margin: 20px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; page-break-inside: auto; }}
    tr {{ page-break-inside: avoid; page-break-after: auto; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; word-wrap: break-word; }}
    th {{ background-color: #f2f2f2; }}
    pre {{ background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
    code {{ font-family: monospace; }}
    h1, h2, h3, h4, h5, h6 {{ page-break-after: avoid; }}
    </style></head><body>{html_content_for_pdf}</body></html>"""

                pdf_filename_dl = os.path.splitext(report_filename)[0] + ".pdf"

                # It's better to use BytesIO with send_file for dynamically generated files
                from io import BytesIO
                pdf_bytes_io = BytesIO()
                HTML(string=html_string, base_url=reports_folder).write_pdf(pdf_bytes_io)
                pdf_bytes_io.seek(0)

                return send_file(
                    pdf_bytes_io,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=pdf_filename_dl # Flask 2.0+ uses download_name
                )
            except ImportError:
                flash("PDF转换库 (WeasyPrint) 未安装。无法下载PDF版本。", "warning")
                return redirect(url_for('view_report', report_filename=report_filename))
            except Exception as e:
                flash(f"生成PDF报告时出错: {e}", "danger")
                print(f"ERROR: PDF Generation: {e}") # Log error
                import traceback
                traceback.print_exc()
                return redirect(url_for('view_report', report_filename=report_filename)) # Redirect to MD view on error
                # return f"Error generating PDF: {e}", 500 # For debugging

        elif format_type == 'html':
            # For HTML download, could convert MD to HTML and serve it, or just serve MD as text/html
            # For a "downloadable" HTML, it's often better to render the MD into a full HTML page
            flash("HTML直接下载格式暂未完全实现，将提供Markdown源文件。", "info")
            # Fall through to MD download with a different mimetype if desired, or just serve MD
            return send_from_directory(reports_folder, report_filename, as_attachment=True, mimetype='text/markdown')


        # Default to MD
        return send_from_directory(reports_folder, report_filename, as_attachment=as_attachment)

    # --- Helper for Simulation (to be removed or refactored if SIMULATE_LLM is False for pipeline) ---
    # This function is now largely replaced by run_full_analysis_pipeline
    # If SIMULATE_LLM is True, run_full_analysis_pipeline will use the simulation features
    # within each module. So, this specific simulate_analysis_and_create_report can be removed.
    # For now, I will comment it out. It will be removed in a subsequent step.

    # def simulate_analysis_and_create_report(patent_doc_path, evidence_docs_paths, report_md_path, report_base_name, session_id):
    #     """
    #     Simulates the analysis process and creates a dummy report.
    #     Updates status_db.
    #     """
    #     # ... (Implementation commented out as it's being replaced)


    return app # Return the app instance from the factory

if __name__ == '__main__':
    app = create_app() # Create app instance using factory
    # Check for WeasyPrint for PDF export (optional, for user info)
    try:
        import weasyprint
        print("WeasyPrint found, PDF export should be available.")
    except ImportError:
        print("WeasyPrint not found. PDF export will not be available. To enable, run: pip install weasyprint")

    app.run(debug=True, host='0.0.0.0', port=5001)
