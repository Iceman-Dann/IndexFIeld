import os
import re

def prepare_templates():
    os.makedirs("templates", exist_ok=True)
    
    # 1. Create base.html from dashboard.html
    with open("dashboard.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    # Find the section containing all the fragments
    # We'll look for `<div id="chat-view"...` to `<div id="manuals-view"...</div>`
    
    # Using regex to replace the fragments area with the Jinja block
    # A robust way is to replace everything between <!-- Chat View --> and </main>
    pattern = r'(<!-- Chat View -->)[\s\S]*?(</main>)'
    replacement = r'\1\n            {% block content %}{% endblock %}\n        \2'
    
    base_html = re.sub(pattern, replacement, html_content)
    
    # Update navigation to use real links instead of JS routing
    nav_replacements = [
        (r'onclick="showView\(\'chat\'\)"', r'href="/chat"'),
        (r'onclick="routeGuard\(\'insights\'\)"', r'href="/insights"'),
        (r'onclick="routeGuard\(\'manuals\'\)"', r'href="/manuals"'),
        (r'onclick="routeGuard\(\'history\'\)"', r'href="/history"'),
        (r'onclick="routeGuard\(\'assets\'\)"', r'href="/assets"'),
        (r'onclick="routeGuard\(\'telemetry\'\)"', r'href="/telemetry"'),
        (r'onclick="routeGuard\(\'prognostics\'\)"', r'href="/prognostics"'),
        (r'onclick="routeGuard\(\'loto\'\)"', r'href="/loto"'),
        (r'onclick="openVault\(\)"', r'href="/vault"')
    ]
    
    for old, new in nav_replacements:
        base_html = re.sub(rf'href="#"\s+{old}', new, base_html)
        base_html = re.sub(old, new, base_html)

    # Disable SPA fetch logic in base.html
    base_html = re.sub(
        r'async function loadDashboardFragments\(\)\s*\{[\s\S]*?\}\s*(?=// Initialize)', 
        'async function loadDashboardFragments() { console.log("MPA Mode via Jinja2."); }\n        ', 
        base_html
    )

    with open("templates/base.html", "w", encoding="utf-8") as f:
        f.write(base_html)

    # 2. Add Jinja blocks to dashboard-pages
    pages_dir = "dashboard-pages"
    fragments = [f for f in os.listdir(pages_dir) if f.endswith(".html")]
    
    for filename in fragments:
        filepath = os.path.join(pages_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        if "{% extends" not in content:
            new_content = '{% extends "base.html" %}\n{% block content %}\n' + content + '\n{% endblock %}\n'
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
                
    print("Successfully generated templates/base.html and updated dashboard-pages with Jinja2 blocks.")

if __name__ == "__main__":
    prepare_templates()
