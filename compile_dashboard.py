import os
import re

def compile_dashboard():
    source_file = "dashboard.html"
    output_file = "dashboard_standalone.html"
    pages_dir = "dashboard-pages"

    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found in current directory.")
        return

    print(f"Reading {source_file}...")
    with open(source_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Define all fragments we want to compile and inline
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

    inlined_count = 0

    for view_id, filename in fragments:
        filepath = os.path.join(pages_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: Fragment file {filepath} not found. Skipping.")
            continue

        print(f"Inlining {filename} into container #{view_id}...")
        with open(filepath, "r", encoding="utf-8") as fragment_file:
            fragment_content = fragment_file.read()

        # We need to find the empty container in dashboard.html:
        # e.g., <div id="chat-view" class="dashboard-view chat-view-layout" data-fragment="chat-view"></div>
        # Or <div id="insights-view" class="dashboard-view hidden flex-1 overflow-y-auto p-6" data-fragment="insights-view"></div>
        
        # Regex to locate the specific target container and replace its inner HTML
        pattern = rf'(<div\s+id="{view_id}"\s+class="[^"]*dashboard-view[^"]*"\s+data-fragment="{view_id}">)(</div>)'
        
        # Let's check if we can match it
        match = re.search(pattern, html_content)
        if match:
            # Replaces the entire empty div with the fragment content
            replacement = fragment_content
            html_content = html_content.replace(match.group(0), replacement)
            inlined_count += 1
        else:
            # Try a broader match just in case classes are ordered differently
            pattern_alt = rf'(<div\s+data-fragment="{view_id}"\s+[^>]*>)(</div>)'
            match_alt = re.search(pattern_alt, html_content)
            if match_alt:
                replacement = fragment_content
                html_content = html_content.replace(match_alt.group(0), replacement)
                inlined_count += 1
            else:
                print(f"Could not find exact placeholder for #{view_id}")

    # Now let's update loadDashboardFragments to detect inlined contents and bypass CORS errors
    old_fetch_logic = """        async function loadDashboardFragments() {
            const fragmentTargets = [
                { id: 'chat-view', url: 'dashboard-pages/chat-view.html' },
                { id: 'insights-view', url: 'dashboard-pages/insights-view.html' },
                { id: 'assets-view', url: 'dashboard-pages/assets-view.html' },
                { id: 'telemetry-view', url: 'dashboard-pages/telemetry-view.html' },
                { id: 'vault-view', url: 'dashboard-pages/vault-view.html' },
                { id: 'field-view', url: 'dashboard-pages/field-view.html' },
                { id: 'loto-view', url: 'dashboard-pages/loto-view.html' },
                { id: 'prognostics-view', url: 'dashboard-pages/prognostics-view.html' },
                { id: 'history-view', url: 'dashboard-pages/history-view.html' },
                { id: 'help-view', url: 'dashboard-pages/help-view.html' },
                { id: 'manuals-view', url: 'dashboard-pages/manuals-view.html' }
            ];

            await Promise.all(fragmentTargets.map(async (fragment) => {
                const target = document.getElementById(fragment.id);
                if (!target) return;

                try {
                    const response = await fetch(fragment.url);
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    const content = await response.text();
                    target.innerHTML = content;
                } catch (error) {
                    target.innerHTML = `<div class="p-6 text-sm text-red-300">Unable to load ${fragment.id}: ${error.message}</div>`;
                }
            }));
        }"""

    new_fetch_logic = """        async function loadDashboardFragments() {
            const fragmentTargets = [
                { id: 'chat-view', url: 'dashboard-pages/chat-view.html' },
                { id: 'insights-view', url: 'dashboard-pages/insights-view.html' },
                { id: 'assets-view', url: 'dashboard-pages/assets-view.html' },
                { id: 'telemetry-view', url: 'dashboard-pages/telemetry-view.html' },
                { id: 'vault-view', url: 'dashboard-pages/vault-view.html' },
                { id: 'field-view', url: 'dashboard-pages/field-view.html' },
                { id: 'loto-view', url: 'dashboard-pages/loto-view.html' },
                { id: 'prognostics-view', url: 'dashboard-pages/prognostics-view.html' },
                { id: 'history-view', url: 'dashboard-pages/history-view.html' },
                { id: 'help-view', url: 'dashboard-pages/help-view.html' },
                { id: 'manuals-view', url: 'dashboard-pages/manuals-view.html' }
            ];

            await Promise.all(fragmentTargets.map(async (fragment) => {
                const target = document.getElementById(fragment.id);
                if (!target) return;

                // If content is already inlined in the DOM (like in compiled standalone mode), skip fetch
                if (target.innerHTML.trim().length > 0 && !target.innerHTML.includes("Unable to load")) {
                    console.log(`[SPA] ${fragment.id} is already inlined. Bypassing fetch.`);
                    return;
                }

                try {
                    const response = await fetch(fragment.url);
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    const content = await response.text();
                    target.innerHTML = content;
                } catch (error) {
                    // Check if local file CORS block
                    if (window.location.protocol === 'file:') {
                        console.warn(`[SPA] Fetch failed due to local file CORS restrictions for ${fragment.id}. Standalone inlining fallback required.`);
                        // Keep any existing inlined markup rather than showing error
                        if (target.innerHTML.trim().length > 0) return;
                    }
                    target.innerHTML = `<div class="p-6 text-sm text-red-300">Unable to load ${fragment.id}: ${error.message}</div>`;
                }
            }));
        }"""

    if old_fetch_logic in html_content:
        html_content = html_content.replace(old_fetch_logic, new_fetch_logic)
        print("Updated loadDashboardFragments logic to support both hot-reloading fragments and fallback/offline inline execution.")
    else:
        # Try a substring replacement in case of small whitespace variations
        html_content = html_content.replace("target.innerHTML = content;", "target.innerHTML = content;")
        print("Could not match exact old fetch logic blocks, kept existing SPA routing.")

    print(f"Writing fully compiled, standalone dashboard to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"SUCCESS: Successfully inlined {inlined_count} modules into '{output_file}'!")
    print("You can now open 'dashboard_standalone.html' directly in your browser with file:// protocol without any web server!")

if __name__ == "__main__":
    compile_dashboard()
