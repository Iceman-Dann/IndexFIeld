import os
import re
from pathlib import Path

def generate_mpa_pages():
    source_file = "dashboard.html"
    pages_dir = "dashboard-pages"

    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found.")
        return

    with open(source_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    fragments = [
        ("chat-view", "chat-view.html"),
        ("insights-view", "insights-view.html"),
        ("assets-view", "assets-view.html"),
        ("telemetry-view", "telemetry-view.html"),
        ("vault-view", "vault-view.html"),
        ("field-view", "field-view.html"),
        ("loto-view", "loto-view.html"),
        ("prognostics-view", "prognostics-view.html"),
        ("history-view", "history-view.html"),
        ("help-view", "help-view.html"),
        ("manuals-view", "manuals-view.html")
    ]

    for target_id, filename in fragments:
        filepath = os.path.join(pages_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: Fragment {filepath} not found.")
            continue

        print(f"Generating standalone page for {filename}...")
        
        with open(filepath, "r", encoding="utf-8") as f:
            fragment_content = f.read()

        # We start with the full dashboard.html content
        page_html = html_content

        # 1. Replace the target container with the actual fragment content and make it visible
        # Target container looks like <div id="chat-view" class="dashboard-view hidden ..." data-fragment="chat-view"></div>
        # Or <div id="chat-view" class="dashboard-view chat-view-layout" data-fragment="chat-view"></div>
        target_pattern = rf'(<div\s+id="{target_id}"\s+class=")([^"]*)("\s*(?:data-fragment="{target_id}"\s*)?>)(</div>)'
        
        def replace_target(match):
            classes = match.group(2)
            # Remove 'hidden' class to make it visible by default
            classes = classes.replace('hidden', '').strip()
            return f'{match.group(1)}{classes}{match.group(3)}{fragment_content}{match.group(4)}'
            
        page_html = re.sub(target_pattern, replace_target, page_html)
        
        # Also try simpler match if it has no innerHTML
        target_pattern2 = rf'(<div\s+id="{target_id}"[^>]*>)(</div>)'
        def replace_target2(match):
            m_text = match.group(1)
            m_text = m_text.replace('hidden', '').strip()
            return f'{m_text}{fragment_content}{match.group(2)}'
        
        # If the first sub didn't change anything (because no class matching perfectly), try the fallback
        if fragment_content not in page_html:
            page_html = re.sub(target_pattern2, replace_target2, page_html)

        # 2. Remove all OTHER fragment containers
        for other_id, _ in fragments:
            if other_id != target_id:
                other_pattern = rf'<div\s+id="{other_id}"[^>]*></div>'
                page_html = re.sub(other_pattern, '', page_html)

        # 3. Update the navigation links in the sidebar to use href links instead of JS routing
        # Example: <a href="#" onclick="showView('chat')" id="nav-chat"...
        # We need to change it to <a href="/{target_id.replace('-view', '')}" id="nav-{target_id.replace('-view', '')}"
        
        # A generalized way to update sidebar navigation to use real URLs
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
            # First strip any existing href="#"
            page_html = re.sub(rf'href="#"\s+{old}', new, page_html)
            page_html = re.sub(old, new, page_html)

        # 4. Remove the SPA fetch logic `loadDashboardFragments()` to avoid fetching fragments
        page_html = re.sub(r'async function loadDashboardFragments\(\)\s*\{[^}]+\}', 'async function loadDashboardFragments() { console.log("MPA Mode: Fragments pre-rendered."); }', page_html)

        # Save the full standalone page back into dashboard-pages
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(page_html)

    print("Successfully converted dashboard-pages to standalone MPA files.")

if __name__ == "__main__":
    generate_mpa_pages()
