import subprocess
import os
import openai
import json
from config import (
    OPENAI_API_KEY, OPENAI_API_BASE, LLM_MODEL, LLM_TEMPERATURE,
    LLM_MAX_TOKENS, FLAMEGRAPH_DIR
)

class PerfAnalyzer:
    def __init__(self, output_dir='perf_data'):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.flamegraph_dir = FLAMEGRAPH_DIR

        # Configure OpenAI client from config.py
        self.client = None
        if OPENAI_API_KEY and OPENAI_API_KEY != 'YOUR_DEFAULT_API_KEY':
            self.client = openai.OpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_API_BASE,
            )
            self.llm_enabled = True
        else:
            print("Warning: OpenAI API key not configured in config.py or environment. AI analysis will be disabled.")
            self.llm_enabled = False

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
        Analyzes folded stack data with an LLM to identify bottlenecks and suggest optimizations.
        The method now expects a structured JSON response from the LLM.

        Args:
            folded_stacks_path (str): The path to the folded stacks file.

        Returns:
            dict: A dictionary containing the structured analysis from the LLM, or an error message.
        """
        if not self.llm_enabled or not self.client:
            return {"error": "AI analysis is disabled. Please configure your OpenAI API key."}

        try:
            with open(folded_stacks_path, 'r') as f:
                folded_data = "".join(f.readlines()[:1000])

            if not folded_data:
                return {"error": "The folded stacks file is empty."}

            prompt = self._build_structured_prompt(folded_data)

            print("Sending data to LLM for analysis...")
            chat_completion = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert performance engineer. Analyze the provided `perf` data (in folded stack format) and return your analysis in a structured JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )

            analysis_content = chat_completion.choices[0].message.content
            print("LLM analysis received.")

            # Parse the JSON string into a Python dictionary
            return json.loads(analysis_content)

        except FileNotFoundError:
            return {"error": f"Folded stacks file not found at {folded_stacks_path}"}
        except json.JSONDecodeError:
            return {"error": "Failed to decode the LLM's JSON response. The response may be malformed."}
        except Exception as e:
            print(f"An error occurred during LLM analysis: {e}")
            return {"error": f"An error occurred while communicating with the AI model: {e}"}

    def _build_structured_prompt(self, folded_data):
        """Builds a prompt that asks the LLM for a structured JSON output."""

        prompt = """
Please analyze the following performance data from a `perf` profile, presented in the folded stack format. Each line is a call stack, and the number at the end is the sample count.

**Folded Stack Data:**
```
{data}
```

**Your Task:**
Analyze the data and identify the top 3-5 performance bottlenecks. For each bottleneck, provide a detailed analysis and actionable optimization suggestions. Structure your entire response as a single JSON object with the following schema:

```json
{{
  "analysis_summary": "A brief, one-paragraph overview of the main performance characteristics observed.",
  "bottlenecks": [
    {{
      "rank": 1,
      "function": "The primary function or symbol identified as the bottleneck (e.g., `inefficient_loop` or `[kernel.kallsyms]`+`0x...`). This should be a string that can be found in the flame graph.",
      "sample_percentage": "An estimated percentage of total samples this bottleneck is responsible for.",
      "root_cause": "A detailed explanation of why this function is a bottleneck. Is it compute-bound, memory-intensive, or called too frequently? Explain the likely performance anti-pattern.",
      "optimization_suggestion": "A concrete, actionable recommendation to fix the issue. Include code examples or configuration changes where possible."
    }},
    {{
      "rank": 2,
      "function": "...",
      "sample_percentage": "...",
      "root_cause": "...",
      "optimization_suggestion": "..."
    }}
  ]
}}
```

**Instructions:**
- The `function` field MUST EXACTLY match a function name or symbol present in the provided stack data so it can be linked to a flame graph.
- Provide a concise yet thorough analysis for each field.
- Ensure the output is a valid JSON object.

Begin your analysis now.
"""
        return prompt.format(data=folded_data)
