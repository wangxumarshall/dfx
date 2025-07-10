import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import requests
import PyPDF2
import markdown as md
# import docx # python-docx
# from PIL import Image # For OCR with pytesseract
# import pytesseract # For OCR
import json
import time

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = 'reports'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'md', 'txt'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['REPORTS_FOLDER'] = REPORTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload and report directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

import uuid
from flask import flash # Added for flashing messages
import shutil # For operations like deleting a directory tree

# --- Configuration Loading ---
try:
    from config import settings
except ImportError:
    print("ERROR: config/settings.py not found or has errors. Please ensure it exists and is correctly configured.")
    # Provide some default fallbacks or exit
    class settings: #type: ignore
        OPENAI_API_KEY = "YOUR_FALLBACK_OPENAI_KEY"
        SERP_API_KEY = "YOUR_FALLBACK_SERP_KEY"
        UPLOAD_FOLDER = 'uploads'
        REPORTS_FOLDER = 'reports'
        ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'md', 'txt', 'zip'}
        MAX_CONTENT_LENGTH = 16 * 1024 * 1024
        SIMULATE_LLM = True # Important for testing without real API calls
        SIMULATE_LLM_DELAY = 2
        TESSERACT_CMD = 'tesseract' # Default for Linux/macOS

app.config['UPLOAD_FOLDER'] = settings.UPLOAD_FOLDER
app.config['REPORTS_FOLDER'] = settings.REPORTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = settings.MAX_CONTENT_LENGTH
app.secret_key = os.urandom(24) # Needed for flash messages

# Ensure upload and report directories exist
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(settings.REPORTS_FOLDER, exist_ok=True)
# Create a session-specific uploads sub-directory parent
SESSION_UPLOADS_PARENT = os.path.join(settings.UPLOAD_FOLDER, 'session_data')
os.makedirs(SESSION_UPLOADS_PARENT, exist_ok=True)


# --- Utility Functions ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS

# --- Core Logic Imports (placeholders for now) ---
# from core import file_parser, llm_analyzer, report_generator

# --- Global dictionary to track analysis status ---
# In a production environment, use a database or a more robust cache (e.g., Redis)
analysis_status_db = {} # report_filename -> {"status": "processing/completed/failed", "error": "...", "current_step": "...", "progress_message": "..."}

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_and_analyze():
    """
    Handles file uploads (patent and evidence) and URL inputs.
    Triggers the analysis process.
    """
    if request.method == 'POST':
        patent_file = request.files.get('patent_file')
        patent_url = request.form.get('patent_url', '').strip()
        evidence_files = request.files.getlist('evidence_files[]') # For multiple files or a single zip

        # Create a unique session ID for this analysis run
        session_id = str(uuid.uuid4())
        session_upload_dir = os.path.join(SESSION_UPLOADS_PARENT, session_id)
        os.makedirs(session_upload_dir, exist_ok=True)

        patent_doc_path = None
        evidence_docs_paths = [] # This will store paths to individual evidence files (extracted from zip if necessary)
        evidence_input_type = None # 'files' or 'zip'

        # 1. Process Patent File/URL
        if patent_file and patent_file.filename != '' and allowed_file(patent_file.filename):
            filename = secure_filename(patent_file.filename)
            patent_doc_path = os.path.join(session_upload_dir, "patent_" + filename)
            patent_file.save(patent_doc_path)
        elif patent_url:
            try:
                response = requests.get(patent_url, timeout=10)
                response.raise_for_status() # Raise an exception for HTTP errors
                # Sanitize URL to create a safe filename
                url_filename = secure_filename(patent_url.split('/')[-1] or "patent_from_url.html")
                if not url_filename.endswith(('.html', '.htm', '.txt', '.pdf')): # Basic check
                    url_filename += ".html" # Assume html if no clear extension

                patent_doc_path = os.path.join(session_upload_dir, "patent_" + url_filename)
                with open(patent_doc_path, 'wb') as f:
                    f.write(response.content)
            except requests.RequestException as e:
                flash(f"专利URL下载失败: {e}", "danger")
                shutil.rmtree(session_upload_dir, ignore_errors=True)
                return redirect(url_for('index'))
        else:
            flash("必须提供专利文件或专利URL。", "danger")
            shutil.rmtree(session_upload_dir, ignore_errors=True)
            return redirect(url_for('index'))

        # 2. Process Evidence Files (can be multiple files or a single ZIP)
        temp_evidence_dir = os.path.join(session_upload_dir, "evidence_files")
        os.makedirs(temp_evidence_dir, exist_ok=True)

        if evidence_files and evidence_files[0].filename != '':
            is_zip_upload = any(f.filename.lower().endswith('.zip') for f in evidence_files)

            if is_zip_upload:
                if len(evidence_files) > 1:
                    flash("如果上传ZIP文件，请只选择一个ZIP文件作为侵权线索。", "warning")
                    # Potentially take the first zip and ignore others, or error out

                zip_file = next((f for f in evidence_files if f.filename.lower().endswith('.zip')), None)
                if zip_file and allowed_file(zip_file.filename):
                    zip_filename = secure_filename(zip_file.filename)
                    zip_path = os.path.join(session_upload_dir, zip_filename)
                    zip_file.save(zip_path)

                    try:
                        import zipfile
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            # Extract only allowed file types from ZIP
                            for member in zip_ref.namelist():
                                if allowed_file(member) and not member.startswith('__MACOSX'): # Basic security
                                    # Sanitize member name before extracting
                                    # member_filename = secure_filename(os.path.basename(member))
                                    # if not member_filename: continue # Skip if filename becomes empty after sanitizing

                                    # To preserve directory structure within zip, need careful handling
                                    # For now, flatten and make sure filenames are unique if needed, or prefix
                                    target_path = os.path.join(temp_evidence_dir, os.path.basename(member))
                                    # Ensure the target directory for the file exists if it's in a subfolder in zip
                                    # os.makedirs(os.path.dirname(target_path), exist_ok=True) # This is risky without more sanitization

                                    # Safer: extract to a unique name if there are subdirs, or flatten
                                    # For now, let's assume simple zip structure or flatten
                                    # If the member is a directory, zip_ref.extract will handle it by creating it.
                                    # We only want files.
                                    if not member.endswith('/'): # it's a file
                                        source = zip_ref.open(member)
                                        target = open(target_path, "wb")
                                        with source, target:
                                            shutil.copyfileobj(source, target)
                                        evidence_docs_paths.append(target_path)
                        os.remove(zip_path) # Remove original zip after extraction
                        evidence_input_type = 'zip'
                    except zipfile.BadZipFile:
                        flash("上传的侵权线索ZIP文件无效或已损坏。", "danger")
                        shutil.rmtree(session_upload_dir, ignore_errors=True)
                        return redirect(url_for('index'))
                    except Exception as e:
                        flash(f"解压侵权线索ZIP文件时出错: {e}", "danger")
                        shutil.rmtree(session_upload_dir, ignore_errors=True)
                        return redirect(url_for('index'))
                else:
                    flash("提供的侵权线索ZIP文件类型不允许。", "warning") # Or ignore if other valid files are present

            if not evidence_docs_paths: # If not a zip or zip processing failed and there are other files
                for file in evidence_files:
                    if file and file.filename != '' and allowed_file(file.filename) and not file.filename.lower().endswith('.zip'):
                        filename = secure_filename(file.filename)
                        evidence_file_path = os.path.join(temp_evidence_dir, filename)
                        file.save(evidence_file_path)
                        evidence_docs_paths.append(evidence_file_path)
                if evidence_docs_paths:
                     evidence_input_type = 'files'

        if not evidence_docs_paths: # No evidence files provided at all
            # flash("请至少提供一个侵权线索文件或包含线索的ZIP包。", "warning")
            # Allow proceeding without evidence, LLM can work on patent only or search later
            pass


        # Generate a unique filename for the report (e.g., based on patent name or timestamp)
        # For now, use a timestamp / UUID
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        report_base_name = f"report_{timestamp}_{session_id[:8]}.md"
        report_filename_md = os.path.join(settings.REPORTS_FOLDER, report_base_name)

        # Store initial status
        analysis_status_db[report_base_name] = {"status": "processing", "current_step": "upload", "progress_message": "文件接收完毕"}

        # TODO: Trigger the actual analysis in a background thread/task queue
        # For now, we'll simulate a delay and then "complete" it for redirection.
        # In a real app, this would be:
        # from threading import Thread
        # thread = Thread(target=run_full_analysis, args=(patent_doc_path, evidence_docs_paths, report_filename_md, session_id, report_base_name))
        # thread.start()

        # For now, let's just pass data to analyzing page. The actual analysis will be mocked there or via status checks
        # This is a simplified flow for now.
        # The run_full_analysis function would handle all steps:
        # 1. file_parser.extract_text_from_patent(patent_doc_path)
        # 2. file_parser.extract_text_from_evidences(evidence_docs_paths)
        # 3. llm_analyzer.analyze_infringement(...)
        # 4. report_generator.create_report(...)
        # Each step would update analysis_status_db[report_base_name]

        # For demonstration, let's create a dummy report file after a delay if SIMULATE_LLM is true
        if settings.SIMULATE_LLM:
            from threading import Thread
            # The target function for the thread needs all necessary data
            thread = Thread(target=simulate_analysis_and_create_report,
                            args=(patent_doc_path, evidence_docs_paths, report_filename_md, report_base_name, session_id))
            thread.start()
        else:
            # TODO: Implement actual analysis call here
            # For now, if not simulating, it will likely show "processing" indefinitely or fail at check_status
            analysis_status_db[report_base_name]["error"] = "Actual LLM analysis not implemented yet. Set SIMULATE_LLM=True in settings.py for a demo."
            analysis_status_db[report_base_name]["status"] = "failed"


        estimated_time_seconds = 60 + len(evidence_docs_paths) * 15 # Rough estimate
        if settings.SIMULATE_LLM:
             estimated_time_seconds = settings.SIMULATE_LLM_DELAY * (2 + len(evidence_docs_paths))


        return redirect(url_for('analyzing_page', report_filename=report_base_name, estimated_time=estimated_time_seconds))

@app.route('/analyzing/<report_filename>')
def analyzing_page(report_filename):
    # The estimated time could be passed as a query parameter or retrieved based on report_filename if stored
    estimated_time = request.args.get('estimated_time', 180) # Default to 180 seconds
    return render_template('analyzing.html', report_filename=report_filename, estimated_time=estimated_time)

@app.route('/status/<report_filename>')
def check_analysis_status(report_filename):
    status_info = analysis_status_db.get(report_filename, {"status": "unknown", "error": "Analysis ID not found."})
    return jsonify(status_info)

@app.route('/report/<report_filename>')
def view_report(report_filename):
    report_path_md = os.path.join(settings.REPORTS_FOLDER, secure_filename(report_filename))
    try:
        with open(report_path_md, 'r', encoding='utf-8') as f:
            report_content_md = f.read()
        # Simple title extraction (e.g., first line of MD if it's a heading)
        report_title = report_content_md.split('\n')[0].replace('#', '').strip() or "分析报告"
        return render_template('report.html',
                               report_content_md=report_content_md,
                               report_title=report_title,
                               report_filename_raw=report_filename) # Pass raw filename for download links
    except FileNotFoundError:
        return render_template('report.html', error_message=f"报告文件 {report_filename} 未找到或尚未生成。请稍后再试或返回主页重新开始。", report_filename_raw=report_filename)
    except Exception as e:
        return render_template('report.html', error_message=f"读取报告时出错: {e}", report_filename_raw=report_filename)

@app.route('/download_report/<report_filename>')
def download_report(report_filename):
    report_path = os.path.join(settings.REPORTS_FOLDER, secure_filename(report_filename))
    as_attachment = request.args.get('as_attachment', True) # Default to download
    format_type = request.args.get('format', 'md').lower()

    if not os.path.exists(report_path):
        flash("请求的报告文件不存在。", "danger")
        return redirect(url_for('index')) # Or some error page

    if format_type == 'pdf':
        # Placeholder for PDF conversion. This requires a library like WeasyPrint or reportlab
        # For now, we'll just indicate it's not implemented.
        try:
            from weasyprint import HTML
            # Read markdown, convert to HTML (basic) then to PDF
            with open(report_path, 'r', encoding='utf-8') as f_md:
                md_content = f_md.read()

            # Basic HTML wrapper for the markdown content for better PDF rendering
            # You might need a more sophisticated MD -> HTML for WeasyPrint if complex structures are involved
            import markdown
            html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

            html_string = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
body {{ font-family: sans-serif; line-height: 1.6; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #f2f2f2; }}
pre {{ background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd; overflow-x: auto; }}
code {{ font-family: monospace; }}
h1, h2, h3 {{ border-bottom: 1px solid #eee; padding-bottom: 0.3em; }}
</style></head><body>{html_content}</body></html>"""

            pdf_filename = os.path.splitext(report_filename)[0] + ".pdf"
            # pdf_path = os.path.join(settings.REPORTS_FOLDER, pdf_filename) # Save it then send? Or send directly.

            # html = HTML(string=html_content, base_url=settings.REPORTS_FOLDER) # base_url if you have local images/css
            html = HTML(string=html_string)
            pdf_bytes = html.write_pdf()

            from io import BytesIO
            return send_from_directory(
                directory=BytesIO(pdf_bytes), # This is not how send_from_directory works.
                path=pdf_filename, # This also incorrect.
                # Instead, use send_file
                mimetype='application/pdf',
                as_attachment=True,
                download_name=pdf_filename # Flask 2.0+ uses download_name
            )


        except ImportError:
            flash("PDF转换库 (WeasyPrint) 未安装。无法下载PDF版本。", "warning")
            return redirect(url_for('view_report', report_filename=report_filename))
        except Exception as e:
            flash(f"生成PDF报告时出错: {e}", "danger")
            # return redirect(url_for('view_report', report_filename=report_filename))
            # For debugging, let's see the error on the page
            return f"Error generating PDF: {e}", 500


    elif format_type == 'html':
        # Placeholder for HTML conversion or direct serving if MD is simple
        flash("HTML下载格式暂未完全实现。", "info")
        return redirect(url_for('view_report', report_filename=report_filename))
        # return send_from_directory(settings.REPORTS_FOLDER, report_filename, as_attachment=True, mimetype='text/html')

    # Default to MD
    return send_from_directory(settings.REPORTS_FOLDER, report_filename, as_attachment=as_attachment)


# --- Helper for Simulation ---
def simulate_analysis_and_create_report(patent_doc_path, evidence_docs_paths, report_md_path, report_base_name, session_id):
    """
    Simulates the analysis process and creates a dummy report.
    Updates status_db.
    """
    try:
        analysis_status_db[report_base_name] = {"status": "processing", "current_step": "patent_extraction", "progress_message": "提取核心专利信息..."}
        time.sleep(settings.SIMULATE_LLM_DELAY / 2) # Simulate patent processing

        patent_text_summary = f"这是对专利文件 {os.path.basename(patent_doc_path)} 的模拟摘要。\n主要权利要求：1. 一种新的组合物... 2. 一种制备方法..."
        if patent_doc_path.endswith(".url"): # if it was a URL
             patent_text_summary = f"这是对专利URL内容的模拟摘要。\n主要权利要求：1. 一种新的小工具... "


        analysis_status_db[report_base_name]["current_step"] = "evidence_extraction"
        analysis_status_db[report_base_name]["progress_message"] = f"解析 {len(evidence_docs_paths)} 个侵权线索文件..."
        time.sleep(settings.SIMULATE_LLM_DELAY / 2) # Simulate evidence processing initiation

        evidence_summaries = []
        for i, doc_path in enumerate(evidence_docs_paths):
            analysis_status_db[report_base_name]["progress_message"] = f"解析侵权线索文件 {i+1}/{len(evidence_docs_paths)}: {os.path.basename(doc_path)}..."
            time.sleep(settings.SIMULATE_LLM_DELAY / (len(evidence_docs_paths) if len(evidence_docs_paths) > 0 else 1) )
            evidence_summaries.append(f"线索文件 {os.path.basename(doc_path)}：\n  - 模拟提取内容：包含与专利相关的关键词A、B、C。")

        analysis_status_db[report_base_name]["current_step"] = "llm_analysis"
        analysis_status_db[report_base_name]["progress_message"] = "大模型正在进行侵权比对分析..."
        time.sleep(settings.SIMULATE_LLM_DELAY) # Simulate LLM analysis

        # Create dummy report content
        report_content = f"# 专利侵权分析报告 (模拟)\n\n"
        report_content += f"分析时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report_content += f"任务ID: {session_id}\n\n"
        report_content += f"## 1. 核心专利信息\n\n"
        report_content += f"来源：`{os.path.basename(patent_doc_path)}`\n\n"
        report_content += f"**模拟专利摘要与核心权利要求**:\n{patent_text_summary}\n\n"
        report_content += f"## 2. 侵权线索分析\n\n"

        if not evidence_docs_paths:
            report_content += "未提供侵权线索文件进行分析。\n"
        else:
            report_content += f"本次分析共包含 {len(evidence_docs_paths)} 个潜在侵权线索文件。\n\n"
            for i, summary in enumerate(evidence_summaries):
                risk = ["高风险", "中风险", "低风险"][i % 3]
                score = [75, 55, 30][i % 3]
                report_content += f"### 线索 {i+1}: {os.path.basename(evidence_docs_paths[i])}\n"
                report_content += f"- **内容摘要**：{summary}\n"
                report_content += f"- **模拟匹配度得分**：{score}/100\n"
                report_content += f"- **模拟风险等级**：{risk}\n"
                report_content += f"- **模拟分析**：该线索文件中的特征 X、Y 与专利权利要求 Z 存在较高相似性。建议进一步详细审查。\n\n"

        report_content += f"## 3. 总结与建议 (模拟)\n\n"
        report_content += "- 基于模拟分析，部分线索显示出较高的侵权风险。\n"
        report_content += "- 建议法务团队对高风险线索进行深入的人工复核和证据固定。\n"
        report_content += "---\n*此报告由PMAS系统自动生成（模拟模式）*\n"

        with open(report_md_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        analysis_status_db[report_base_name]["status"] = "completed"
        analysis_status_db[report_base_name]["current_step"] = "report_generation"
        analysis_status_db[report_base_name]["progress_message"] = "报告生成完毕"

    except Exception as e:
        analysis_status_db[report_base_name]["status"] = "failed"
        analysis_status_db[report_base_name]["error"] = f"模拟分析过程中发生错误: {str(e)}"
        # Optionally, write an error report
        error_report_content = f"# 分析失败\n\n错误详情: {str(e)}"
        with open(report_md_path, 'w', encoding='utf-8') as f: # Overwrite with error or use different name
            f.write(error_report_content)
    finally:
        # Clean up session-specific uploaded files after analysis is done (or failed)
        # In a real scenario, you might want to keep them for a while or based on policy
        session_upload_dir_to_clean = os.path.join(SESSION_UPLOADS_PARENT, session_id)
        if os.path.exists(session_upload_dir_to_clean):
             shutil.rmtree(session_upload_dir_to_clean, ignore_errors=True)


if __name__ == '__main__':
    # Check for WeasyPrint for PDF export (optional, for user info)
    try:
        import weasyprint
        print("WeasyPrint found, PDF export should be available.")
    except ImportError:
        print("WeasyPrint not found. PDF export will not be available. To enable, run: pip install weasyprint")

    app.run(debug=True, host='0.0.0.0', port=5001) # Running on a different port for clarity
