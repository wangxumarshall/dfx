import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, current_app
from modules.perf_analyzer.analyzer import PerfAnalyzer

def create_app():
    app = Flask(__name__)

    # General app configuration
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    app.secret_key = os.urandom(24)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --- Perf Analyzer Setup ---
    # The PerfAnalyzer is now configured via core.config, so we don't pass keys here.
    perf_output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'perf_reports')
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

        # 3. Analyze with LLM
        folded_stacks_file = os.path.join(perf_analyzer.output_dir, 'out.perf-folded')
        llm_analysis_json = perf_analyzer.analyze_with_llm(folded_stacks_file)

        # Handle potential errors from the LLM analysis
        if 'error' in llm_analysis_json:
            flash(f"AI analysis failed: {llm_analysis_json['error']}", "danger")
            # Proceed without AI analysis if it fails
            llm_analysis_json = {}

        try:
            with open(flamegraph_svg_path, 'r') as f:
                flamegraph_svg_content = f.read()
        except IOError as e:
            flash(f"Could not read flame graph file: {e}", "danger")
            flamegraph_svg_content = "<p>Error loading flame graph.</p>"

        # Pass the raw JSON to the template for the frontend to handle
        return render_template(
            'perf_report.html',
            command=command_to_run,
            flamegraph_svg=flamegraph_svg_content,
            llm_analysis_json=json.dumps(llm_analysis_json) # Convert dict to JSON string
        )

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
