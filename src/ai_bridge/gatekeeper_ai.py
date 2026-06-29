import os
import json
import glob
import requests
import sys


# Fields to extract from SonarQube issues to minimize prompt size
SONARQUBE_FIELDS = ['key', 'rule', 'severity', 'component', 'message', 'type', 'status']


def extract_sonarqube_summary(data: dict) -> list:
    """Extracts only the relevant fields from a SonarQube API response."""
    issues = data.get('issues', [])
    return [
        {field: issue.get(field) for field in SONARQUBE_FIELDS}
        for issue in issues
    ]


def load_reports(reports_dir: str) -> dict:
    """Reads all JSON report files and returns a condensed, LLM-friendly summary."""
    json_files = glob.glob(os.path.join(reports_dir, '*.json'))
    if not json_files:
        return {}

    combined = {}
    for filepath in json_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r') as f:
                raw = json.load(f)

            # Apply source-specific processing to reduce noise
            if 'sonarqube' in filename:
                combined[filename] = extract_sonarqube_summary(raw)
            else:
                combined[filename] = raw

        except Exception as e:
            print(f"[!] Error reading {filename}: {e}")

    return combined


def build_prompt(reports: dict) -> str:
    report_text = json.dumps(reports, indent=2)
    return f"""You are an expert DevSecOps engineer specialized in cloud infrastructure security.

Analyze the following security scan results from a CI pipeline and provide a concise review.

--- SCAN RESULTS ---
{report_text}
--- END OF RESULTS ---

Your response must include:
1. **Critical Findings**: List the most severe vulnerabilities with their rule ID and affected component.
2. **Recommendations**: For each critical finding, provide a concrete fix (code snippet or configuration change if applicable).
3. **Best Practice Violations**: Any general security best practices being violated.

Format your response in Markdown. Be concise and actionable.
"""


def query_llm(url: str, model: str, prompt: str, timeout: int) -> str:
    """Sends the prompt to the Ollama API and returns the response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            # Limit output length to speed up response on low-resource machines
            "num_predict": 512
        }
    }
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json().get('response', 'No response field found.')


def main():
    reports_dir = os.environ.get('REPORTS_DIR', 'reports')
    ollama_url = os.environ.get('OLLAMA_URL', 'http://172.17.0.11:11434/api/generate')
    llm_model = os.environ.get('LLM_MODEL', 'qwen2.5-coder:7b')
    # Generous timeout: CPU-only inference at ~5 t/s needs time.
    # num_predict=512 tokens @ 5 t/s = ~102s, plus prompt processing time.
    llm_timeout = int(os.environ.get('LLM_TIMEOUT', '300'))

    print(f"[*] Starting AI Security Review — model: {llm_model} | endpoint: {ollama_url}")
    print(f"[*] Reading reports from '{reports_dir}'...")

    reports = load_reports(reports_dir)
    if not reports:
        print("[!] No JSON reports found in the reports directory. Skipping AI review.")
        sys.exit(0)

    total_issues = sum(len(v) if isinstance(v, list) else 1 for v in reports.values())
    print(f"[*] Loaded {len(reports)} report(s) with {total_issues} finding(s) total.")

    prompt = build_prompt(reports)
    print(f"[*] Prompt size: {len(prompt)} characters. Sending to LLM (timeout: {llm_timeout}s)...")

    try:
        result = query_llm(ollama_url, llm_model, prompt, llm_timeout)

        print("\n" + "=" * 60)
        print("🤖  AI SECURITY RECOMMENDATIONS")
        print("=" * 60 + "\n")
        print(result)
        print("\n" + "=" * 60 + "\n")

    except requests.exceptions.Timeout:
        print(f"[!] LLM request timed out after {llm_timeout}s.")
        print("[!] Consider increasing the LLM_TIMEOUT environment variable or reducing the prompt size.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"[!] Failed to connect to Ollama API: {e}")
        print("[!] Please ensure the Ollama container is running and accessible from the Jenkins agent.")
        sys.exit(1)


if __name__ == "__main__":
    main()
