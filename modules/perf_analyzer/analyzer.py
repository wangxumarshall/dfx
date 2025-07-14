import subprocess
import os
import openai

class PerfAnalyzer:
    def __init__(self, output_dir='perf_data', openai_api_key=None):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Store the path to the FlameGraph scripts
        self.flamegraph_dir = os.path.expanduser('~/FlameGraph')

        # Configure OpenAI client
        if openai_api_key:
            openai.api_key = openai_api_key
        else:
            # Attempt to get key from environment variable as a fallback
            openai.api_key = os.getenv("OPENAI_API_KEY")

        if not openai.api_key:
            print("Warning: OpenAI API key not provided. AI analysis will be disabled.")
            self.llm_enabled = False
        else:
            self.llm_enabled = True

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
        and suggest optimizations.

        Args:
            folded_stacks_path (str): The path to the folded stacks file.

        Returns:
            str: A markdown-formatted string with the AI's analysis, or an error message.
        """
        if not self.llm_enabled:
            return "AI analysis is disabled. Please provide an OpenAI API key."

        try:
            with open(folded_stacks_path, 'r') as f:
                # Read a sample of the data to avoid exceeding token limits
                # Reading the first 1000 lines is a heuristic.
                folded_data = "".join(f.readlines()[:1000])

            if not folded_data:
                return "Error: The folded stacks file is empty."

            prompt = self._build_llm_prompt(folded_data)

            print("Sending data to LLM for analysis...")
            chat_completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", # Or "gpt-4" for higher quality analysis
                messages=[
                    {"role": "system", "content": "You are an expert performance engineer. Your task is to analyze the provided `perf` data (in folded stack format) and identify performance bottlenecks. Provide a detailed analysis and actionable optimization suggestions."},
                    {"role": "user", "content": prompt}
                ]
            )

            analysis = chat_completion.choices[0].message.content
            print("LLM analysis received.")
            return analysis

        except FileNotFoundError:
            return f"Error: Folded stacks file not found at {folded_stacks_path}"
        except Exception as e:
            print(f"An error occurred during LLM analysis: {e}")
            return f"An error occurred while communicating with the AI model: {e}"

    def _build_llm_prompt(self, folded_data):
        """Builds the prompt for the LLM analysis."""

        prompt = """
Please analyze the following performance data, which is in the `perf` folded stack format. Each line represents a call stack, and the number at the end is the number of samples for that stack.

**Folded Stack Data:**
```
{data}
```

**Your Task:**

1.  **Identify the Top 3-5 Performance Bottlenecks:**
    -   Pinpoint the functions or call stacks that consume the most CPU time.
    -   Look for patterns like deep recursion, inefficient loops, or functions that are unexpectedly hot.

2.  **Provide a Root Cause Analysis for Each Bottleneck:**
    -   Explain *why* these functions are consuming so much time. Is it due to high call frequency, expensive computations, or something else?
    -   If possible, infer the likely cause (e.g., "This looks like a classic N+1 query problem," or "The high sample count in `memcpy` suggests large data copies").

3.  **Suggest Actionable Optimization Strategies:**
    -   Provide specific, concrete recommendations for how to fix each bottleneck.
    -   Suggestions could include code changes (e.g., "Consider caching the result of `expensive_calculation`"), configuration adjustments, or architectural changes.
    -   Format your response in clear, easy-to-read Markdown. Use headings, bullet points, and code blocks for clarity.

Begin your analysis now.
"""
        return prompt.format(data=folded_data)
