import os
from flask import Flask, render_template, request, redirect, url_for, flash, current_app, json
import markdown as md
from modules.perf_analyzer.analyzer import PerfAnalyzer
import config

def create_app():
    app = Flask(__name__)

    # Load configuration from config.py
    app.config.from_object(config)
    app.secret_key = os.urandom(24)

    # Ensure necessary directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    perf_output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'perf_reports')
    os.makedirs(perf_output_dir, exist_ok=True)

    # Instantiate the PerfAnalyzer and attach it to the app
    app.perf_analyzer = PerfAnalyzer(output_dir=perf_output_dir)

    @app.route('/')
    def index():
        """Redirects to the perf analyzer page."""
        return redirect(url_for('perf_index'))

    @app.route('/perf')
    def perf_index():
        """Displays the main page for the performance analyzer."""
        return render_template('perf.html')

    @app.route('/perf/analyze', methods=['POST'])
    def perf_analyze():
        """
        Triggers the performance analysis and displays the report.
        """
        command_to_run = request.form.get('command', 'sleep 10').strip()
        duration = int(request.form.get('duration', 10))

        if not command_to_run:
            flash("Please provide a command to analyze.", "danger")
            return redirect(url_for('perf_index'))

        command_list = command_to_run.split()
        perf_analyzer = current_app.perf_analyzer

        # 1. Collect data
        perf_data_file = perf_analyzer.collect_data(command=command_list, duration=duration)
        if not perf_data_file:
            flash("Failed to collect perf data. Ensure 'perf' is installed and you have sudo privileges.", "danger")
            return redirect(url_for('perf_index'))

        # 2. Generate flame graph
        flamegraph_svg_path = perf_analyzer.generate_flamegraph(perf_data_file)
        if not flamegraph_svg_path:
            flash("Failed to generate flame graph.", "danger")
            return redirect(url_for('perf_index'))

        # 3. Analyze with LLM (now returns a dict)
        folded_stacks_file = os.path.join(perf_analyzer.output_dir, 'out.perf-folded')
        llm_analysis_dict = perf_analyzer.analyze_with_llm(folded_stacks_file)

        # Handle potential errors from the analyzer
        if 'error' in llm_analysis_dict:
            flash(f"AI analysis failed: {llm_analysis_dict['error']}", "danger")
            llm_analysis_dict = {} # Clear dict to avoid template errors

        try:
            with open(flamegraph_svg_path, 'r') as f:
                flamegraph_svg_content = f.read()
        except IOError as e:
            flash(f"Could not read flame graph file: {e}", "danger")
            flamegraph_svg_content = "<p>Error loading flame graph.</p>"

        return render_template(
            'perf_report.html',
            command=command_to_run,
            flamegraph_svg=flamegraph_svg_content,
            analysis_data=llm_analysis_dict,
            analysis_data_json=json.dumps(llm_analysis_dict) # Pass as JSON string for JS
        )

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
