"""Create a standalone HTML report from pytest's JUnit XML (no extra packages)."""

import argparse
import base64
from collections import Counter
from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET


def generate_report(xml_path: Path, output_path: Path, expected_count=None) -> Path:
    root = ET.parse(xml_path).getroot()
    cases = list(root.iter("testcase"))
    if expected_count is not None and expected_count < len(cases):
        raise ValueError("Expected case count cannot be less than recorded results")
    incomplete = (expected_count - len(cases)) if expected_count is not None else 0
    counts = Counter()
    rows = []
    screenshot_root = xml_path.resolve().parent.parent / "screenshots"

    for case in cases:
        problem = case.find("error")
        status = "error"
        if problem is None:
            problem = case.find("failure")
            status = "failed"
        if problem is None:
            problem = case.find("skipped")
            status = "skipped"
        if problem is None:
            status = "passed"
        counts[status] += 1
        detail = ""
        if problem is not None:
            message = problem.get("message", "")
            text = problem.text or message
            detail = (
                '<details><summary>Show details</summary><pre>'
                + escape(text) + '</pre></details>'
            )
        for prop in case.findall("properties/property"):
            if prop.get("name") == "result_source":
                detail += '<p><small>Result source: ' + escape(prop.get('value', '')) + '</small></p>'
            if prop.get("name") != "screenshot":
                continue
            path = Path(prop.get("value", "")).resolve()
            # Embed only local PNGs from this project's screenshot directory.
            if path.is_relative_to(screenshot_root.resolve()) and path.suffix == ".png" and path.is_file():
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                detail += (
                    '<details><summary>Failure screenshot</summary>'
                    '<img alt="Screenshot captured at test failure" '
                    f'src="data:image/png;base64,{encoded}"></details>'
                )
        module = case.get("classname", "")
        name = case.get("name", "")
        rows.append(
            f'<tr data-status="{status}"><td><span class="badge {status}">{status.upper()}</span></td>'
            f'<td><small>{escape(module)}</small><div class="test-name">{escape(name)}</div>{detail}</td>'
            f'<td class="duration">{escape(case.get("time", "0"))}s</td></tr>'
        )

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    duration = sum(float(s.get("time", "0")) for s in suites)
    timestamp = suites[0].get("timestamp", "Not recorded") if suites else "Not recorded"
    report_type = ''
    for suite in suites:
        for prop in suite.findall('properties/property'):
            if prop.get('name') == 'report_type':
                report_type = prop.get('value', '')
    cards = ''.join(
        f'<div class="card {status}"><strong>{counts[status]}</strong><span>{status.title()}</span></div>'
        for status in ("passed", "failed", "error", "skipped")
    )
    document = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Eduport — Appium Test Report</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#172337;font:15px/1.5 system-ui,sans-serif}
main{max-width:1180px;margin:36px auto;padding:0 24px}h1{margin:0;font-size:30px}
.subtitle,small{color:#5c6b80}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:24px 0}
.card{background:white;border-radius:12px;padding:20px;border-top:4px solid}.card strong{display:block;font-size:34px}
.passed{color:#147449;border-color:#147449}.failed,.error{color:#b52c3c;border-color:#b52c3c}.skipped{color:#856000;border-color:#b88a00}
.note{background:#fff7df;padding:16px 20px;border-radius:10px;margin:20px 0;color:#604800}
.toolbar{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}input,select{padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;font:inherit}
input{flex:1;min-width:220px}.table-wrap{overflow:auto;background:white;border-radius:12px;border:1px solid #dce4ee}
table{border-collapse:collapse;width:100%}th{text-align:left;background:#eaf0f7;padding:14px}td{padding:16px 14px;border-top:1px solid #e5eaf1;vertical-align:top}
.badge{font-size:12px;font-weight:700;white-space:nowrap}.test-name{overflow-wrap:anywhere;font-weight:600}
.duration{white-space:nowrap;font-variant-numeric:tabular-nums}summary{cursor:pointer;color:#2454aa;margin-top:10px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5fa;padding:14px;border-radius:8px;font-size:12px}
img{display:block;width:auto;max-width:100%;max-height:850px;margin-top:12px;border:1px solid #cbd5e1;border-radius:8px}
footer{color:#5c6b80;font-size:13px;margin:24px 0}#empty{padding:20px;display:none}
@media(max-width:600px){main{padding:0 12px}.cards{grid-template-columns:repeat(2,1fr)}h1{font-size:24px}}
</style></head><body><main>
<h1>Eduport · Appium Test Report</h1>
'''
    document += (
        f'<p class="subtitle">Run: {escape(timestamp)} · {len(cases)} test cases · {duration:.2f} seconds</p>'
        + (f'<div class="note">{escape(report_type)}</div>' if report_type else '')
        + (f'<div class="note"><strong>PARTIAL RUN:</strong> {expected_count} cases selected; '
           f'{len(cases)} recorded results and {incomplete} cases not completed. '
           'Uncompleted cases are not passes or skips.</div>' if incomplete else '')
        +
        f'<section class="cards" aria-label="Result summary">{cards}</section>'
        '<div class="note"><strong>Coverage limits:</strong> Skipped tests were not executed and are not passes. '
        'Consult per-case details and the investigation report for OTP coverage. Failures can include automation locator, API, and expectation issues, '
        'not necessarily application defects. Each executed case used its own Appium session and app restart; '
        'app/backend cleanup details are documented in the investigation report.</div>'
        f'<p>See <a href="{escape(output_path.with_suffix(".md").name)}">the investigation report</a> for observed behavior and next corrections.</p>'
        '<div class="toolbar"><input id="search" type="search" aria-label="Search test names" placeholder="Search test cases…">'
        '<select id="status" aria-label="Filter results"><option value="all">All results</option>'
        '<option value="passed">Passed</option><option value="failed">Failed</option>'
        '<option value="error">Errors</option><option value="skipped">Skipped</option></select>'
        f'<span id="visible" aria-live="polite">{len(cases)} shown</span></div>'
        '<div class="table-wrap"><table><thead><tr><th>Result</th><th>Test case &amp; evidence</th><th>Duration</th></tr></thead>'
        '<tbody>' + ''.join(rows) + '</tbody></table><p id="empty">No matching tests.</p></div>'
        '<footer>Generated from pytest JUnit XML. Failure screenshots are embedded for offline viewing. '
        'Report generation did not rerun tests. Treat screenshots as potentially sensitive.</footer>'
    )
    document += '''</main><script>
const rows = Array.from(document.querySelectorAll('tbody tr'));
function filterRows(){
  const query=document.getElementById('search').value.toLowerCase();
  const status=document.getElementById('status').value;
  let count=0;
  rows.forEach(row=>{
    const match=(status==='all'||row.dataset.status===status)&&row.querySelector('td:nth-child(2)').textContent.toLowerCase().includes(query);
    row.hidden=!match;if(match)count++;
  });
  document.getElementById('visible').textContent=count+' shown';
  document.getElementById('empty').style.display=count?'none':'block';
}
document.getElementById('search').addEventListener('input',filterRows);
document.getElementById('status').addEventListener('change',filterRows);
</script></body></html>'''
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path.resolve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-count", type=int, default=None,
                        help="Selected test count, to identify an interrupted run")
    args = parser.parse_args()
    print(generate_report(args.xml, args.output, args.expected_count))
