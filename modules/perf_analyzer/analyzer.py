import subprocess
import os
from core import llm_analyzer
from core import prompts

class PerfAnalyzer:
    def __init__(self, output_dir='perf_data'):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Store the path to the FlameGraph scripts
        self.flamegraph_dir = os.path.expanduser('~/FlameGraph')

        # LLM client is now managed by core.llm_analyzer
        # No need to manage API keys here.

    def collect_data(self, command, duration=10, freq=99):
        """
        Collects performance data using 'perf record'.

        Args:
            command (list): The command to profile, as a list of strings.
            duration (int): The duration of the profiling in seconds.
            freq (int): The sampling frequency.

        Returns:
            str: The path to the generated perf.data file, or None on error.
        """
        output_file = os.path.join(self.output_dir, 'perf.data')
        perf_command = [
            'sudo', 'perf', 'record',
            '-F', str(freq),
            '-o', output_file,
            '-g', '--',
            'sleep', str(duration) # Default to sleeping if no command
        ]

        # If a real command is provided, profile it instead of sleep
        if command:
            perf_command = [
                'sudo', 'perf', 'record',
                '-F', str(freq),
                '-o', output_file,
                '-g', '--'
            ] + command

        try:
            print(f"Running perf command: {' '.join(perf_command)}")
            # Note: This requires the user to have sudo privileges without a password prompt
            # for the 'perf' command, or the password must be entered manually.
            # In a web app, this is a significant security consideration.
            subprocess.run(perf_command, check=True, timeout=duration + 5)

            if os.path.exists(output_file):
                print(f"Perf data collected successfully: {output_file}")
                return output_file
            else:
                print("Error: perf.data file was not created.")
                return None
        except FileNotFoundError:
            print("Error: 'perf' command not found. Please ensure it is installed and in your PATH.")
            return None
        except subprocess.CalledProcessError as e:
            print(f"Error executing perf command: {e}")
            return None
        except subprocess.TimeoutExpired:
            print("Error: perf command timed out.")
            return None

    def _check_flamegraph_scripts(self):
        """Checks if the required FlameGraph scripts exist."""
        required_scripts = ['stackcollapse-perf.pl', 'flamegraph.pl']
        for script in required_scripts:
            if not os.path.exists(os.path.join(self.flamegraph_dir, script)):
                print(f"Error: FlameGraph script not found: {script}")
                print(f"Please clone Brendan Gregg's FlameGraph repository into {self.flamegraph_dir}")
                print("git clone https://github.com/brendangregg/FlameGraph.git ~/FlameGraph")
                return False
        return True

    def generate_flamegraph(self, perf_data_path):
        """
        Generates a flame graph from a perf.data file.

        Args:
            perf_data_path (str): The path to the perf.data file.

        Returns:
            str: The path to the generated SVG file, or None on error.
        """
        if not self._check_flamegraph_scripts():
            return None

        if not os.path.exists(perf_data_path):
            print(f"Error: perf data file not found at {perf_data_path}")
            return None

        # Define file paths for intermediate and final outputs
        folded_stacks_path = os.path.join(self.output_dir, 'out.perf-folded')
        flamegraph_svg_path = os.path.join(self.output_dir, 'flamegraph.svg')

        try:
            # 1. perf script
            perf_script_cmd = ['sudo', 'perf', 'script', '-i', perf_data_path]
            with open(os.path.join(self.output_dir, 'out.perfscript'), 'w') as f:
                subprocess.run(perf_script_cmd, stdout=f, check=True)

            # 2. Stack collapse
            stackcollapse_cmd = [
                os.path.join(self.flamegraph_dir, 'stackcollapse-perf.pl'),
                os.path.join(self.output_dir, 'out.perfscript')
            ]
            with open(folded_stacks_path, 'w') as f:
                subprocess.run(stackcollapse_cmd, stdout=f, check=True, text=True)

            # 3. Flamegraph generation
            flamegraph_cmd = [
                os.path.join(self.flamegraph_dir, 'flamegraph.pl'),
                '--color=hot',
                '--title="CPU Flame Graph"',
                folded_stacks_path
            ]
            with open(flamegraph_svg_path, 'w') as f:
                subprocess.run(flamegraph_cmd, stdout=f, check=True, text=True)

            print(f"Flame graph generated successfully: {flamegraph_svg_path}")
            return flamegraph_svg_path

        except subprocess.CalledProcessError as e:
            print(f"Error during flame graph generation step: {e}")
            # Consider logging e.stdout and e.stderr for more details
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    def analyze_with_llm(self, folded_stacks_path):
        """
        Analyzes the folded stack data with an LLM to identify bottlenecks
        and suggest optimizations, requesting a structured JSON output.

        Args:
            folded_stacks_path (str): The path to the folded stacks file.

        Returns:
            dict: A dictionary containing the AI's analysis, or an error dictionary.
        """
        try:
            with open(folded_stacks_path, 'r') as f:
                # Read a sample of the data to avoid exceeding token limits
                # Reading the first 1000 lines is a heuristic.
                folded_data = "".join(f.readlines()[:1000])

            if not folded_data:
                return {"error": "The folded stacks file is empty."}

            # Use the centralized prompt from core.prompts
            prompt = prompts.PERF_ANALYSIS_JSON_PROMPT.format(data=folded_data)

            # Use the new centralized LLM function
            # Request JSON mode by setting json_mode=True
            analysis_result = llm_analyzer.get_llm_response(
                prompt,
                system_prompt="You are an expert performance engineer. Your task is to analyze the provided `perf` data (in folded stack format) and identify performance bottlenecks. Return your analysis in the specified JSON format.",
                json_mode=True
            )

            # Handle different types of responses (error string vs. success dict)
            if isinstance(analysis_result, str) and analysis_result.startswith("[LLM_ERROR"):
                print(f"LLM analysis failed: {analysis_result}")
                return {"error": analysis_result}

            if not isinstance(analysis_result, dict):
                 print(f"LLM analysis returned an unexpected type: {type(analysis_result)}")
                 return {"error": "LLM did not return a valid JSON object."}

            print("LLM JSON analysis received successfully.")
            return analysis_result

        except FileNotFoundError:
            return {"error": f"Folded stacks file not found at {folded_stacks_path}"}
        except Exception as e:
            print(f"An error occurred during LLM analysis: {e}")
            return {"error": f"An unexpected error occurred during LLM analysis: {e}"}
