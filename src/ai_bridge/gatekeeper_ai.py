import os
import json
import glob
import requests
import sys


# ---------------------------------------------------------------------------
# Report parsers — each function extracts only the fields relevant for the
# LLM prompt, discarding the verbose metadata that inflates token count.
# ---------------------------------------------------------------------------

# Fields to keep from each SonarQube issue
_SONAR_FIELDS = ['key', 'rule', 'severity', 'component', 'message', 'type', 'status']


def extract_sonarqube_summary(data: dict) -> list:
    """Returns a condensed list of SonarQube issues."""
    issues = data.get('issues', [])
    return [
        {field: issue.get(field) for field in _SONAR_FIELDS}
        for issue in issues
    ]


def extract_checkov_summary(data: dict) -> dict:
    """Returns failed checks only, with the fields useful for remediation."""
    # Checkov can wrap results in a list when multiple frameworks are scanned
    if isinstance(data, list):
        merged: list = []
        for entry in data:
            merged.extend(entry.get('results', {}).get('failed_checks', []))
        failed = merged
    else:
        failed = data.get('results', {}).get('failed_checks', [])

    summary = []
    for check in failed:
        summary.append({
            'check_id':   check.get('check_id'),
            'check_name': check.get('check', {}).get('name') if isinstance(check.get('check'), dict) else None,
            'severity':   check.get('severity'),
            'resource':   check.get('resource'),
            'file':       check.get('file_path'),
            'lines':      check.get('file_line_range'),
            'guideline':  check.get('check', {}).get('guideline') if isinstance(check.get('check'), dict) else None,
        })

    return {
        'total_failed': len(summary),
        'failed_checks': summary,
    }


def extract_trivy_summary(data: dict) -> dict:
    """Returns only the misconfigurations found by Trivy config scan."""
    results = data.get('Results', [])
    findings = []
    for result in results:
        target = result.get('Target', '')
        for m in result.get('Misconfigurations', []) or []:
            findings.append({
                'id':          m.get('ID'),
                'title':       m.get('Title'),
                'severity':    m.get('Severity'),
                'status':      m.get('Status'),
                'description': m.get('Description'),
                'resolution':  m.get('Resolution'),
                'file':        target,
            })

    return {
        'total_findings': len(findings),
        'misconfigurations': findings,
    }


# ---------------------------------------------------------------------------
# Dispatcher — maps filename patterns to the right parser
# ---------------------------------------------------------------------------

def load_reports(reports_dir: str) -> dict:
    """Reads all JSON report files and returns a condensed, LLM-friendly dict."""
    json_files = glob.glob(os.path.join(reports_dir, '*.json'))
    if not json_files:
        return {}

    combined = {}
    for filepath in json_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r') as f:
                raw = json.load(f)

            if 'sonarqube' in filename:
                combined[filename] = extract_sonarqube_summary(raw)
            elif 'checkov' in filename:
                combined[filename] = extract_checkov_summary(raw)
            elif 'trivy' in filename:
                combined[filename] = extract_trivy_summary(raw)
            else:
                combined[filename] = raw  # Unknown format — pass through as-is

        except Exception as e:
            print(f"[!] Error reading {filename}: {e}")

    return combined


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(reports: dict) -> str:
    report_text = json.dumps(reports, indent=2)
    return f"""You are an expert DevSecOps engineer specialized in cloud infrastructure security and Terraform.

Analyze the following security scan results produced by multiple CI pipeline scanners (SonarQube, Checkov, Trivy) and provide a concise review.

--- SCAN RESULTS ---
{report_text}
--- END OF RESULTS ---

Your response must include:
1. **Critical Findings**: List the most severe vulnerabilities grouped by tool, with their rule/check ID and affected resource or file.
2. **Recommendations**: For each critical finding, provide a concrete fix (Terraform snippet or configuration change if applicable).
3. **Best Practice Violations**: Any general security best practices being violated across the codebase.

Format your response in Markdown. Be concise and actionable. Prioritize HIGH and CRITICAL severity findings.
"""


# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------

def query_llm(url: str, model: str, prompt: str, timeout: int) -> str:
    """Sends the prompt to the Ollama API and returns the response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            # Limit output length to speed up response on CPU-only machines
            "num_predict": 512,
        },
    }
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json().get('response', 'No response field found.')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    reports_dir = os.environ.get('REPORTS_DIR', 'reports')
    ollama_url  = os.environ.get('OLLAMA_URL',  'http://172.17.0.11:11434/api/generate')
    llm_model   = os.environ.get('LLM_MODEL',   'qwen2.5-coder:7b')
    # Generous timeout: CPU inference at ~5 t/s needs time.
    # num_predict=512 @ 5 t/s ≈ 102s + prompt processing.
    llm_timeout = int(os.environ.get('LLM_TIMEOUT', '300'))

    print(f"[*] Starting AI Security Review — model: {llm_model} | endpoint: {ollama_url}")
    print(f"[*] Reading reports from '{reports_dir}'...")

    reports = load_reports(reports_dir)
    if not reports:
        print("[!] No JSON reports found in the reports directory. Skipping AI review.")
        sys.exit(0)

    # Print a short summary of what was loaded
    for name, content in reports.items():
        if isinstance(content, dict) and 'total_failed' in content:
            print(f"    • {name}: {content['total_failed']} failed checks")
        elif isinstance(content, dict) and 'total_findings' in content:
            print(f"    • {name}: {content['total_findings']} findings")
        elif isinstance(content, list):
            print(f"    • {name}: {len(content)} issues")
        else:
            print(f"    • {name}: loaded")

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
        print("[!] Consider increasing LLM_TIMEOUT or reducing the number of findings passed.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"[!] Failed to connect to Ollama API: {e}")
        print("[!] Please ensure the Ollama container is running and accessible from the Jenkins agent.")
        sys.exit(1)


if __name__ == "__main__":
    main()
