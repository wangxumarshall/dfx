# prompts.py

# Prompt for analyzing performance data and identifying bottlenecks in JSON format
PERF_ANALYSIS_JSON_PROMPT = """
Analyze the following performance data, which is in the `perf` folded stack format.
Each line represents a call stack, and the number at the end is the number of samples for that stack.

**Folded Stack Data:**
```
{data}
```

**Your Task:**
Return a JSON object with two keys: "identified_bottlenecks" and "overall_summary".

1.  **"identified_bottlenecks"**: A list of JSON objects, where each object represents a significant performance bottleneck. Each object must have the following keys:
    -   `function_stack` (string): The full semicolon-separated call stack of the bottleneck.
    -   `percentage` (float): The estimated percentage of total CPU time this stack represents. You can calculate this by `(samples_for_stack / total_samples) * 100`.
    -   `analysis` (string): A concise, expert analysis of why this function is a bottleneck (e.g., "High sample count suggests expensive computation or I/O wait," "This function is called frequently," "Deep recursion observed").
    -   `optimization_suggestion` (string): A concrete, actionable optimization strategy (e.g., "Consider caching the result," "Rewrite the loop to be more efficient," "Use a faster library for this operation").

2.  **"overall_summary"**: A string providing a high-level summary of the performance profile and a concluding recommendation for the user.

**Example of expected JSON output:**
```json
{{
  "identified_bottlenecks": [
    {{
      "function_stack": "main;read_file;process_data",
      "percentage": 45.5,
      "analysis": "This function is responsible for nearly half of the execution time. The `process_data` part seems to be computationally intensive.",
      "optimization_suggestion": "Consider optimizing the `process_data` function. Possible improvements include using more efficient algorithms or parallelizing the workload."
    }},
    {{
      "function_stack": "main;write_output;format_json",
      "percentage": 22.1,
      "analysis": "Significant time is spent formatting and writing the output file. This could be due to large data volumes or inefficient serialization.",
      "optimization_suggestion": "Use a faster JSON library like orjson. If possible, stream the output instead of buffering it all in memory."
    }}
  ],
  "overall_summary": "The application is I/O bound, with major bottlenecks in data processing and output generation. Focusing on these two areas should yield significant performance improvements."
}}
```

Ensure your output is a single, valid JSON object and nothing else.
"""

# You can add other prompts for different analysis types below,
# such as the patent-related ones if they are still needed.

PATENT_SUMMARY_PROMPT = """
**Task**: Summarize the provided patent text.
**Input Patent Text**:
{patent_text}
**Output Format**:
**Patent Name**: [Name of the patent]
**Technical Field**: [Technical field]
**Core Claims**:
1. [Claim 1]
2. [Claim 2]
...
**Key Features/Innovations**:
- [Feature 1]
- [Feature 2]
"""

INFRINGEMENT_ANALYSIS_PROMPT = """
**Task**: Analyze potential infringement of a patent by a target product.
**Patent Name**: {patent_name}
**Technical Field**: {technical_field}
**Core Claims**: {core_claims}
**Key Features**: {key_features}

**Target Product Description**:
{target_product_description}

**Output Format**:
**Analysis Report**:
1.  **Feature Comparison**: [Detailed comparison of product features against patent claims]
2.  **Infringement Likelihood Assessment**: [High/Medium/Low]
3.  **Match Score**: [Score out of 100]
4.  **Rationale**: [Explanation for the assessment and score]
5.  **Conclusion & Recommendation**: [Final conclusion and recommended actions]
"""

FINAL_REPORT_GENERATION_PROMPT = """
**Task**: Generate a comprehensive infringement analysis report.
**Patent Name**: {patent_name}
**Technical Field**: {technical_field}
**Core Claims**: {core_claims}
**Key Features**: {key_features}

**Individual Analysis Summaries**:
{individual_analysis_summaries}

**Output Format**:
# Comprehensive Infringement Analysis Report
## 1. Introduction
...
## 2. Patent Overview
...
## 3. Evidence Analysis Summary
...
## 4. Overall Risk Assessment & Conclusion
...
"""
