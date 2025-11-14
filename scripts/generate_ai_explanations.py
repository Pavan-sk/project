import os
import json
import glob
import time
import argparse

try:
    import openai
except Exception:
    openai = None

try:
    import google.generativeai as genai
except Exception:
    genai = None

PROMPT_TEMPLATE = """You are a concise security analyst. Given the following finding JSON fields, return a JSON object with keys:
- summary (one short paragraph),
- impact (one short sentence),
- detailed_explanation (3-5 sentences),
- remediation_steps (array of short actionable steps).
Only output valid JSON.

Finding:
Title: {title}
Description: {description}
Evidence: {evidence}
Recommendation: {recommendation}
CVE: {cve_id}
Severity: {severity}
Host: {host}
Port: {port}
Service: {service}
Phase: {phase}
Tool: {tool}
Timestamp: {timestamp}
"""

def generate_prompt(finding):
    return PROMPT_TEMPLATE.format(
        title=finding.get("title"),
        description=finding.get("description"),
        evidence=finding.get("evidence"),
        recommendation=finding.get("recommendation"),
        cve_id=finding.get("cve_id"),
        severity=finding.get("severity"),
        host=finding.get("host"),
        port=finding.get("port"),
        service=finding.get("service"),
        phase=finding.get("phase"),
        tool=finding.get("tool"),
        timestamp=finding.get("timestamp"),
    )

def call_mock_ai(finding):
    """Generate a mock AI explanation without external API calls"""
    title = finding.get("title", "Unknown")
    severity = finding.get("severity", "medium")
    description = finding.get("description", "")
    recommendation = finding.get("recommendation", "")
    
    return {
        "summary": f"This is a {severity}-severity finding: {title}. {description}",
        "impact": f"Potential security risk classified as {severity} severity.",
        "detailed_explanation": (
            f"The finding '{title}' has been identified in the assessment. "
            f"{description or 'Details are documented in the report.'} "
            "This requires immediate attention and proper remediation."
        ),
        "remediation_steps": [
            recommendation or "Apply security patches and updates.",
            "Review security configurations and access controls.",
            "Monitor systems for suspicious activity.",
            "Document changes and validate fixes."
        ]
    }

def call_openai(prompt, model="gpt-3.5-turbo", max_retries=3):
    if openai is None:
        raise RuntimeError("openai package not installed. Install with: pip install openai")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable not set. "
            "Set it securely (e.g. export OPENAI_API_KEY='sk-...') before running the script."
        )
    client = openai.OpenAI(api_key=api_key)
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600
            )
            return resp.choices[0].message.content
        except Exception as e:
            if attempt + 1 == max_retries:
                raise
            time.sleep(2 ** attempt)

def call_gemini(prompt, max_retries=3):
    """Call Google Gemini API (free tier available)"""
    if genai is None:
        raise RuntimeError("google-generativeai not installed. Install with: pip install google-generativeai")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable not set. "
            "Get a free key from https://makersuite.google.com/app/apikey"
        )
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")
    for attempt in range(max_retries):
        try:
            resp = model.generate_content(prompt)
            return resp.text
        except Exception as e:
            if attempt + 1 == max_retries:
                raise
            time.sleep(2 ** attempt)

def process_file(path, dry_run=False, use_mock=False, use_gemini=False):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("ai_explanation"):
        return False  # skip already processed
    
    if use_mock:
        ai_obj = call_mock_ai(data)
    else:
        prompt = generate_prompt(data)
        try:
            if use_gemini:
                raw = call_gemini(prompt)
            else:
                raw = call_openai(prompt)
        except Exception as e:
            print(f"ERROR: failed to generate for {path}: {e}")
            return False
        # Expect raw to be a JSON object; try to parse
        try:
            ai_obj = json.loads(raw)
        except Exception:
            # Fallback: wrap raw text as 'summary' if parsing fails
            ai_obj = {"summary": raw.strip()}
    
    ai_obj["generated_by"] = "script: generate_ai_explanations.py"
    ai_obj["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    data["ai_explanation"] = ai_obj
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    print(f"Processed: {path}")
    return True

def show_reports(base, pattern="**/*.json", single_file=None):
    # base: absolute directory path
    if single_file:
        pattern_path = os.path.join(base, single_file) if not os.path.isabs(single_file) else single_file
        files = [pattern_path]
    else:
        pattern_path = os.path.join(base, pattern)
        files = glob.glob(pattern_path, recursive=True)

    if not files:
        print("No files found.")
        return

    for p in files:
        if not p.endswith(".json"):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            ai = data.get("ai_explanation")
            print(f"\nFile: {p}")
            if ai:
                print(json.dumps(ai, indent=2))
            else:
                print("  (no ai_explanation present)")
        except Exception as e:
            print(f"  Error reading {p}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate AI explanations for AutoPentest results")
    parser.add_argument("--dir", "-d", default=os.path.join(os.path.dirname(__file__), "..", "results"), help="results directory")
    parser.add_argument("--dry-run", action="store_true", help="do not write changes")
    parser.add_argument("--pattern", default="**/*.json", help="glob pattern under results")
    parser.add_argument("--show", action="store_true", help="show ai_explanation fields and exit (no API calls)")
    parser.add_argument("--file", help="show only this file (path relative to --dir or absolute)")
    parser.add_argument("--use-mock", action="store_true", help="use mock AI (no API calls, no dependencies)")
    parser.add_argument("--use-gemini", action="store_true", help="use Google Gemini API instead of OpenAI")
    args = parser.parse_args()

    base = os.path.abspath(args.dir)

    if args.show:
        show_reports(base, pattern=args.pattern, single_file=args.file)
        return

    pattern = os.path.join(base, args.pattern)
    files = glob.glob(pattern, recursive=True)
    if not files:
        print("No files found.")
        return
    for p in files:
        if not p.endswith(".json"):
            continue
        try:
            process_file(p, dry_run=args.dry_run, use_mock=args.use_mock, use_gemini=args.use_gemini)
            time.sleep(0.5)
        except Exception as e:
            print(f"Skipping {p}: {e}")

if __name__ == "__main__":
    main()