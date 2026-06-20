// ============================================================================
// IndexField New Features JavaScript
// Handles Voice Query, Cross-Reference, Tribal Knowledge, Work Orders,
// Shift Handover, and Facility Health Score functionality
// ============================================================================

// Global Mock Data for Demo Sandbox Facility
const DEMO_ASSETS = [
    { id: "A1", name: "Hydraulic Press #3", type: "Press", location: "Zone A", last_service: "2026-05-10", next_due: "2026-07-10", health: 98, status: "OPERATIONAL" },
    { id: "A2", name: "Boiler Room Unit #2", type: "Boiler", location: "Zone B", last_service: "2026-06-01", next_due: "2026-06-25", health: 89, status: "REQUIRES INSPECTION" },
    { id: "A3", name: "Main Turbine #1", type: "Turbine", location: "Zone C", last_service: "2026-04-15", next_due: "2026-07-15", health: 95, status: "OPERATIONAL" },
    { id: "A4", name: "Fuel Valve V-102", type: "Valve", location: "Zone B", last_service: "2026-05-20", next_due: "2026-06-20", health: 76, status: "WARNING" },
    { id: "A5", name: "Water Pump 3-A", type: "Pump", location: "Zone A", last_service: "2026-06-18", next_due: "2026-08-18", health: 92, status: "OPERATIONAL" },
    { id: "A6", name: "Air Compressor AC-4", type: "Compressor", location: "Zone D", last_service: "2026-03-10", next_due: "2026-06-10", health: 64, status: "WARNING" },
    { id: "A7", name: "Reciprocating Compressor RC-1", type: "Compressor", location: "Zone D", last_service: "2026-05-05", next_due: "2026-08-05", health: 94, status: "OPERATIONAL" },
    { id: "A8", name: "Boiler Room Unit #1", type: "Boiler", location: "Zone B", last_service: "2026-01-10", next_due: "2026-07-10", health: 97, status: "OPERATIONAL" },
    { id: "A9", name: "Water Pump 3-B", type: "Pump", location: "Zone A", last_service: "2026-06-12", next_due: "2026-08-12", health: 99, status: "OPERATIONAL" },
    { id: "A10", name: "Fuel Valve V-101", type: "Valve", location: "Zone B", last_service: "2026-05-18", next_due: "2026-08-18", health: 96, status: "OPERATIONAL" },
    { id: "A11", name: "Turbine Generator #2", type: "Generator", location: "Zone C", last_service: "2026-02-28", next_due: "2026-08-28", health: 93, status: "OPERATIONAL" },
    { id: "A12", name: "Cooling Tower Pump", type: "Pump", location: "Zone E", last_service: "2026-06-10", next_due: "2026-09-10", health: 91, status: "OPERATIONAL" },
    { id: "A13", name: "Condenser C-102", type: "Condenser", location: "Zone C", last_service: "2026-04-01", next_due: "2026-10-01", health: 88, status: "OPERATIONAL" },
    { id: "A14", name: "Deaerator Tank DA-1", type: "Tank", location: "Zone B", last_service: "2026-03-15", next_due: "2026-09-15", health: 95, status: "OPERATIONAL" },
    { id: "A15", name: "Nitrogen Purge Valve", type: "Valve", location: "Zone D", last_service: "2026-05-12", next_due: "2026-11-12", health: 97, status: "OPERATIONAL" }
];

const DEMO_MANUALS = [
    { id: "M1", filename: "Hydraulic Press Operating Manual Rev 4.pdf", page_count: 94, chunk_count: 320 },
    { id: "M2", filename: "Boiler Unit 2 OEM Specification.pdf", page_count: 145, chunk_count: 512 },
    { id: "M3", filename: "Main Turbine 1 Maintenance Guide.pdf", page_count: 210, chunk_count: 780 },
    { id: "M4", filename: "Industrial Valve Safety & Clearances SOP.pdf", page_count: 48, chunk_count: 180 },
    { id: "M5", filename: "Water Pump 3 Series Operation Manual.pdf", page_count: 86, chunk_count: 290 },
    { id: "M6", filename: "Air Compressor AC-4 Service Manual.pdf", page_count: 74, chunk_count: 240 },
    { id: "M7", filename: "Reciprocating Compressor Specs.pdf", page_count: 112, chunk_count: 410 },
    { id: "M8", filename: "General Plant Safety & LOTO Guidelines.pdf", page_count: 35, chunk_count: 120 }
];

const DEMO_WORK_ORDERS = [
    { id: "W1", work_order_id: "WO-1031", title: "IMP-03: Realign impeller shaft on Water Pump 3-A", asset_id: "A5", asset_name: "Water Pump 3-A", assigned_to: "Alex Rivers", priority: "CRITICAL", status: "OPEN", due_date: new Date().toISOString().split('T')[0], estimated_hours: 4.5, ai_briefed: true, description: "Check shaft deflection, align coupling using laser toolkit, replace motor-side sleeve bearings if wear > 0.05mm." },
    { id: "W2", work_order_id: "WO-1032", title: "BOI-02: Calibrate pressure transducer on Boiler #2", asset_id: "A2", asset_name: "Boiler Room Unit #2", assigned_to: "Sarah Connor", priority: "CRITICAL", status: "OPEN", due_date: new Date().toISOString().split('T')[0], estimated_hours: 2.0, ai_briefed: true, description: "Calibrate pressure transmitter PT-202. Loop verify to DCS panel. Record span calibration deviations." },
    { id: "W3", work_order_id: "WO-1033", title: "VAL-102: Replace seals on Fuel Valve V-102", asset_id: "A4", asset_name: "Fuel Valve V-102", assigned_to: "Sarah Connor", priority: "HIGH", status: "IN_PROGRESS", due_date: new Date(Date.now() + 86400000).toISOString().split('T')[0], estimated_hours: 6.0, ai_briefed: true, description: "Isolate gas line, vent section. Replace PTFE seals on stem. Check LOTO protocol before starting." },
    { id: "W4", work_order_id: "WO-1034", title: "TUR-01: Vibration analysis on Turbine #1 casing", asset_id: "A3", asset_name: "Main Turbine #1", assigned_to: "John Smith", priority: "HIGH", status: "OPEN", due_date: new Date(Date.now() + 86400000 * 2).toISOString().split('T')[0], estimated_hours: 3.5, ai_briefed: true, description: "Measure bearing vibration levels across spectra. Log raw readings and compare with baseline." },
    { id: "W5", work_order_id: "WO-1035", title: "COMP-04: Replace intake air filter AC-4", asset_id: "A6", asset_name: "Air Compressor AC-4", assigned_to: "Alex Rivers", priority: "MEDIUM", status: "OPEN", due_date: new Date(Date.now() + 86400000 * 5).toISOString().split('T')[0], estimated_hours: 1.5, ai_briefed: false, description: "Swap out filter panel F-401. Vacuum housing interior. Record differential pressure." },
    { id: "W6", work_order_id: "WO-1036", title: "HYD-03: Annual oil flushing on Press #3", asset_id: "A1", asset_name: "Hydraulic Press #3", assigned_to: "John Smith", priority: "MEDIUM", status: "IN_PROGRESS", due_date: new Date(Date.now() + 86400000 * 10).toISOString().split('T')[0], estimated_hours: 8.0, ai_briefed: true, description: "Flush hydraulic fluid tank. Replace suction filter. Verify fluid cleanliness is ISO 4406 16/14/11 or better." },
    { id: "W7", work_order_id: "WO-1037", title: "PLT-01: Compliance check on safety relief valves", asset_id: "A15", asset_name: "Nitrogen Purge Valve", assigned_to: "Alex Rivers", priority: "LOW", status: "OPEN", due_date: new Date(Date.now() + 86400000 * 14).toISOString().split('T')[0], estimated_hours: 3.0, ai_briefed: false, description: "Verify safety pop-off valves. Confirm tag details and verification history." },
    { id: "W8", work_order_id: "WO-1038", title: "TUR-02: Inspect generator stator cooling system", asset_id: "A11", asset_name: "Turbine Generator #2", assigned_to: "John Smith", priority: "LOW", status: "OPEN", due_date: new Date(Date.now() + 86400000 * 30).toISOString().split('T')[0], estimated_hours: 5.0, ai_briefed: false, description: "Perform check on stator cooling fluid conductivity and pressure drops." },
    { id: "W9", work_order_id: "WO-1039", title: "BOI-01: Annual combustion analysis Boiler #1", asset_id: "A8", asset_name: "Boiler Room Unit #1", assigned_to: "Alex Rivers", priority: "MEDIUM", status: "COMPLETE", due_date: new Date(Date.now() - 86400000 * 5).toISOString().split('T')[0], estimated_hours: 4.0, ai_briefed: true, completed_at: new Date(Date.now() - 86400000 * 5).toISOString(), description: "DCS emissions verification, adjust gas-to-air ratio. Completed with CO2 at 9.4%." },
    { id: "W10", work_order_id: "WO-1040", title: "PMP-02: General service of Cooling Tower Pump", asset_id: "A12", asset_name: "Cooling Tower Pump", assigned_to: "Sarah Connor", priority: "LOW", status: "COMPLETE", due_date: new Date(Date.now() - 86400000 * 2).toISOString().split('T')[0], estimated_hours: 2.5, ai_briefed: false, completed_at: new Date(Date.now() - 86400000 * 2).toISOString(), description: "Grease bearings and tighten packing glands." },
    { id: "W11", work_order_id: "WO-1041", title: "VAL-101: Test safety interlock on Fuel Valve V-101", asset_id: "A10", asset_name: "Fuel Valve V-101", assigned_to: "Sarah Connor", priority: "HIGH", status: "COMPLETE", due_date: new Date(Date.now() - 86400000).toISOString().split('T')[0], estimated_hours: 2.0, ai_briefed: true, completed_at: new Date(Date.now() - 86400000).toISOString(), description: "Verify ESD trigger loops. Confirmed response in 1.4 seconds (limit 2.0s)." },
    { id: "W12", work_order_id: "WO-1042", title: "COMP-05: Inspect RC-1 compressor discharge valves", asset_id: "A7", asset_name: "Reciprocating Compressor RC-1", assigned_to: "John Smith", priority: "MEDIUM", status: "CANCELLED", due_date: new Date(Date.now() - 86400000 * 8).toISOString().split('T')[0], estimated_hours: 3.0, description: "Inspected earlier during preventive shift overhaul." }
];

const DEMO_LOTO_PERMITS = [
    { id: "L1", asset_id: "A2", asset_name: "Boiler Room Unit #2", status: "ACTIVE", initiated_by: "Sarah Connor", initiated_at: new Date(Date.now() - 3600000 * 2).toISOString(), procedure_source: "Boiler Unit 2 OEM Specification.pdf", steps_completed: { "pre-1": true, "iso-1": true, "iso-2": true }, procedure_content: { "pre-lockout": [{ id: "pre-1", text: "Notify Zone B operators of Boiler Room Unit #2 shutdown." }], "energy-isolation": [{ id: "iso-1", text: "Close gas inlet valve GV-202 and apply padlock." }, { id: "iso-2", text: "Open electrical breaker CB-202 and apply lockout tag." }], "verification": [{ id: "ver-1", text: "Verify local pressure indicator reads 0 PSI." }] } },
    { id: "L2", asset_id: "A4", asset_name: "Fuel Valve V-102", status: "ACTIVE", initiated_by: "Sarah Connor", initiated_at: new Date(Date.now() - 3600000 * 5).toISOString(), procedure_source: "Industrial Valve Safety & Clearances SOP.pdf", steps_completed: { "pre-1": true, "iso-1": true }, procedure_content: { "pre-lockout": [{ id: "pre-1", text: "Coordinate with control room to bypass ESD system." }], "energy-isolation": [{ id: "iso-1", text: "Chain and lock fuel line block valve V-102-B." }], "verification": [{ id: "ver-1", text: "Drain lines and verify no residual product remains." }] } },
    { id: "L3", asset_id: "A6", asset_name: "Air Compressor AC-4", status: "ACTIVE", initiated_by: "Alex Rivers", initiated_at: new Date(Date.now() - 3600000 * 12).toISOString(), procedure_source: "Air Compressor AC-4 Service Manual.pdf", steps_completed: { "pre-1": true, "iso-1": true, "ver-1": true }, procedure_content: { "pre-lockout": [{ id: "pre-1", text: "Notify pneumatic tool stations of pressure drop." }], "energy-isolation": [{ id: "iso-1", text: "Lock out breaker panel panel-AC4." }], "verification": [{ id: "ver-1", text: "Bleed air receiver tank to atmosphere." }] } }
];

const DEMO_SHIFT_LOGS = [
    { id: "S1", event_type: "OBSERVATION", description: "Water Pump 3-A bearing housing running hot (68C). Oil level checked OK. Monitor closely.", asset_id: "A5", asset_name: "Water Pump 3-A", user_name: "Alex Rivers", time: "11:20", date: new Date().toISOString().split('T')[0], risk_level: "MEDIUM", ai_analyzed: true, ai_analysis: { cause: "High shaft misalignment or coupling wear", action: "Perform laser alignment on next shift", source: "Water Pump 3 Series Operation Manual.pdf" } },
    { id: "S2", event_type: "SAFETY", description: "Completed isolation of Boiler #2 for calibration work order. Confirmed LOTO permit active.", asset_id: "A2", asset_name: "Boiler Room Unit #2", user_name: "Sarah Connor", time: "10:15", date: new Date().toISOString().split('T')[0], risk_level: "LOW" },
    { id: "S3", event_type: "EQUIPMENT_ISSUE", description: "Fuel Valve V-102 packing gland showing minor leak of gas product. Ingressed high priority WO.", asset_id: "A4", asset_name: "Fuel Valve V-102", user_name: "Sarah Connor", time: "08:45", date: new Date().toISOString().split('T')[0], risk_level: "HIGH", ai_analyzed: true, ai_analysis: { cause: "Teflon seal degradation", action: "Isolate and replace valve seals ASAP", source: "Industrial Valve Safety & Clearances SOP.pdf" } }
];

// Fetch Interceptor for Demo Mode
(function() {
    const originalFetch = window.fetch;
    window.fetch = async function(resource, init) {
        if (localStorage.getItem("indexfield_demo_loaded") !== "true") {
            return originalFetch.apply(this, arguments);
        }

        const url = typeof resource === "string" ? resource : resource.url;
        console.log(`[Demo Fetch Interceptor] Intercepted: ${url}`);

        if (url.includes("/api/assets")) {
            return new Response(JSON.stringify(DEMO_ASSETS), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/workorders/stats")) {
            const stats = { critical_open: 2, high_priority: 2, due_today: 2, completed_this_week: 3 };
            return new Response(JSON.stringify(stats), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/workorders")) {
            return new Response(JSON.stringify(DEMO_WORK_ORDERS), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/loto/permit")) {
            return new Response(JSON.stringify(DEMO_LOTO_PERMITS), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/loto/procedure")) {
            // Return a realistic mock procedure for any requested asset ID
            const body = init && init.body ? JSON.parse(init.body) : {};
            const asset = DEMO_ASSETS.find(a => a.id === body.asset_id) || { name: "Boiler Room Unit #2" };
            const proc = {
                asset_name: asset.name,
                procedure_source: "Boiler Unit 2 OEM Specification.pdf",
                procedure_content: {
                    "pre-lockout": [{ id: "pre-1", text: `Notify operators of ${asset.name} shutdown.` }],
                    "energy-isolation": [
                        { id: "iso-1", text: "Close inlet fuel isolation valve and apply lockout lock." },
                        { id: "iso-2", text: "Turn breaker switch to OFF position and apply tag." }
                    ],
                    "verification": [{ id: "ver-1", text: "Verify that pressure gauge reads 0 and rotation has stopped." }]
                }
            };
            return new Response(JSON.stringify(proc), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/ai/recent-answers")) {
            // Mock recent AI answers based on shift logs for demo purposes
            const answers = DEMO_SHIFT_LOGS.map(log => ({
                time: log.time,
                user_name: log.user_name,
                answer: `AI suggestion for ${log.asset_name}: ${log.description}`
            }));
            return new Response(JSON.stringify({answers}), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/facility/pulse")) {
            const parsed = new URL(url, window.location.origin);
            if (parsed.searchParams.get("users")) {
                return new Response(JSON.stringify({
                    active_users: [
                        { name: "John Smith", role: "Plant Manager", last_action: "Viewed Main Turbine #1", last_active: "5m ago" },
                        { name: "Sarah Connor", role: "Supervisor", last_action: "Initiated permit for V-102", last_active: "12m ago" },
                        { name: "Alex Rivers", role: "Technician", last_action: "Logged observation on Pump 3-A", last_active: "22m ago" }
                    ]
                }), { status: 200, headers: { "Content-Type": "application/json" } });
            }
            if (parsed.searchParams.get("feed")) {
                const activityFeed = [
                    { time: "11:20", user_name: "Alex Rivers", description: "Logged observation on Water Pump 3-A", asset: "Water Pump 3-A" },
                    { time: "10:15", user_name: "Sarah Connor", description: "Activated LOTO permit for Boiler Unit #2", asset: "Boiler Room Unit #2" },
                    { time: "08:45", user_name: "Sarah Connor", description: "Logged leak observation on V-102", asset: "Fuel Valve V-102" }
                ];
                return new Response(JSON.stringify({ activity_feed: activityFeed }), { status: 200, headers: { "Content-Type": "application/json" } });
            }
            if (parsed.searchParams.get("observations")) {
                return new Response(JSON.stringify({ recent_observations: DEMO_SHIFT_LOGS }), { status: 200, headers: { "Content-Type": "application/json" } });
            }
            return new Response(JSON.stringify({ active_users_today: 3, observations_today: 3, work_orders_touched: 12, queries_this_shift: 18 }), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/shift/briefing")) {
            const brief = {
                id: "B1",
                user_name: "John Smith",
                last_shift_summary: "Day shift completed with V-102 leak identified and tagged. Water Pump 3-A runs warm.",
                priorities: [
                    { level: "CRITICAL", title: "Water Pump 3-A Alignment", subtitle: "Alex Rivers reported housing at 68C. Laser realign required." },
                    { level: "CRITICAL", title: "Calibrate pressure transducer Boiler #2", subtitle: "Calibrate transmitter PT-202. Loop verify." },
                    { level: "HIGH", title: "Replace seals V-102", subtitle: "Gas product leak detected at packing gland." }
                ],
                acknowledged_at: null
            };
            return new Response(JSON.stringify(brief), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/maintenance/items")) {
            const maint = [
                { id: "Maint1", asset_name: "Main Turbine #1", task_name: "Vibration Analysis", interval: "3 months", next_due_date: new Date(Date.now() + 86400000 * 5).toISOString().split('T')[0], status: "SCHEDULED", compliance_standard: "API 612" },
                { id: "Maint2", asset_name: "Boiler Room Unit #2", task_name: "Safety Valve Pop Test", interval: "6 months", next_due_date: new Date(Date.now() - 86400000).toISOString().split('T')[0], status: "OVERDUE", compliance_standard: "ASME Sec I" },
                { id: "Maint3", asset_name: "Hydraulic Press #3", task_name: "Fluid Cleanliness Test", interval: "1 month", next_due_date: new Date(Date.now() + 86400000 * 20).toISOString().split('T')[0], status: "SCHEDULED", compliance_standard: "ISO 4406" }
            ];
            return new Response(JSON.stringify(maint), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/maintenance/priorities")) {
            return new Response(JSON.stringify({
                priorities: [
                    { level: "CRITICAL", asset: "Boiler Room Unit #2", task: "Safety Valve Pop Test", reason: "Mandatory pop test 1 day overdue. High compliance pressure.", compliance: "ASME Sec I" },
                    { level: "HIGH", asset: "Main Turbine #1", task: "Vibration Analysis", reason: "Scheduled vibration log due in 5 days.", compliance: "API 612" }
                ]
            }), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/query")) {
            // Custom mock responses for standard queries in O&G
            const body = init && init.body ? JSON.parse(init.body) : {};
            const query = body.query ? body.query.toLowerCase() : "";
            let responseText = "Based on Harwick Processing facility manuals, safety guidelines and standard operating procedures: ";
            if (query.includes("turbine") || query.includes("vibration")) {
                responseText += "Turbine vibration levels should be monitored at bearing housing 1 and 2. Maximum allowable velocity is 2.8 mm/s RMS under API 612 standards. If readings exceed 4.0 mm/s RMS, initiate emergency shutdown procedure immediately.";
            } else if (query.includes("boiler") || query.includes("valve")) {
                responseText += "Boiler unit safety relief valves (ASME Section I) must pop-test at 150 PSI (+/- 2%). Manual lifting levers must only be operated above 75% of full set pressure to prevent seat damage.";
            } else {
                responseText += "The requested spec or standard requires verified documentation. Please consult the Water Pump 3 Series Operation Manual or LOTO safety procedures for Zone B equipment.";
            }
            return new Response(responseText, { status: 200 });
        }
        if (url.includes("/api/voice/transcribe")) {
            return new Response(JSON.stringify({ success: true, text: "Show LOTO isolation steps for Fuel Valve V-102" }), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/handover/history")) {
            return new Response(JSON.stringify([
                { id: "H1", created_at: new Date(Date.now() - 86400000).toISOString(), overall_status: "AMBER", critical_items: ["V-102 Valve Gland Leak"], acknowledged_by: "John Smith", acknowledged_at: new Date(Date.now() - 86400000 + 1800000).toISOString() },
                { id: "H2", created_at: new Date(Date.now() - 86400000 * 2).toISOString(), overall_status: "GREEN", critical_items: [], acknowledged_by: "Sarah Connor", acknowledged_at: new Date(Date.now() - 86400000 * 2 + 1800000).toISOString() }
            ]), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.includes("/api/manuals")) {
            return new Response(JSON.stringify(DEMO_MANUALS), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        return originalFetch.apply(this, arguments);
    };
})();

// Action helper to load demo data
window.loadDemoFacilityData = function() {
    localStorage.setItem("indexfield_demo_loaded", "true");
    localStorage.setItem("indexfield_demo_assets", JSON.stringify(DEMO_ASSETS));
    localStorage.setItem("indexfield_demo_manuals", JSON.stringify(DEMO_MANUALS));
    localStorage.setItem("indexfield_demo_work_orders", JSON.stringify(DEMO_WORK_ORDERS));
    localStorage.setItem("indexfield_demo_loto_permits", JSON.stringify(DEMO_LOTO_PERMITS));
    localStorage.setItem("indexfield_demo_shift_logs", JSON.stringify(DEMO_SHIFT_LOGS));
    
    // Update local variables in memory if page is active
    if (typeof manuals !== "undefined") manuals = DEMO_MANUALS;
    if (typeof currentWorkOrders !== "undefined") currentWorkOrders = DEMO_WORK_ORDERS;
    if (typeof assets !== "undefined") assets = DEMO_ASSETS;
    if (typeof updateChatPanels !== "undefined") updateChatPanels();

    // Reload UI state
    if (window.showToast) {
        window.showToast("Demo Facility Loaded Successfully!", "brand");
    } else {
        alert("Demo Facility Loaded Successfully!");
    }
    
    // Refresh page state and update UI
    setTimeout(() => {
        window.location.reload();
    }, 1000);
};

window.clearDemoFacilityData = function() {
    localStorage.removeItem("indexfield_demo_loaded");
    localStorage.removeItem("indexfield_demo_assets");
    localStorage.removeItem("indexfield_demo_manuals");
    localStorage.removeItem("indexfield_demo_work_orders");
    localStorage.removeItem("indexfield_demo_loto_permits");
    localStorage.removeItem("indexfield_demo_shift_logs");
    window.location.reload();
};

let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

async function toggleVoiceRecording() {
    const micIcon = document.getElementById('mic-icon');
    const scanMicIcon = document.getElementById('scan-mic-icon');
    
    if (isRecording) {
        stopRecording();
        if (micIcon) micIcon.classList.remove('text-red-500', 'animate-pulse');
        if (scanMicIcon) scanMicIcon.classList.remove('text-red-500', 'animate-pulse');
    } else {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            startRecording(stream);
            if (micIcon) micIcon.classList.add('text-red-500', 'animate-pulse');
            if (scanMicIcon) scanMicIcon.classList.add('text-red-500', 'animate-pulse');
        } catch (err) {
            console.error('Microphone access denied:', err);
            alert('Microphone access is required for voice input. Please enable it in your browser settings.');
        }
    }
}

function startRecording(stream) {
    isRecording = true;
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    
    mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
    };
    
    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        await transcribeAudio(audioBlob);
    };
    
    mediaRecorder.start();
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        isRecording = false;
    }
}

async function transcribeAudio(audioBlob) {
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');
    
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/voice/transcribe`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            const chatInput = document.getElementById('chat-input');
            const scanInput = document.getElementById('query-input');
            
            if (chatInput) {
                chatInput.value = result.text;
                chatInput.dispatchEvent(new Event('input'));
            }
            if (scanInput) {
                scanInput.value = result.text;
            }
            
            // Text-to-speech playback
            speakText(result.text);
        } else {
            console.error('Transcription failed:', result.error);
            alert('Transcription failed: ' + (result.error || 'Unknown error'));
        }
    } catch (err) {
        console.error('Transcription error:', err);
        alert('Transcription failed. Please check your connection and try again.');
    }
}

function speakText(text) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1;
        utterance.pitch = 1;
        window.speechSynthesis.speak(utterance);
    }
}

// ============================================================================
// FEATURE 3: Cross-Reference Toggle
// ============================================================================

let searchMode = 'this'; // 'this' or 'all'

function setSearchMode(mode) {
    searchMode = mode;
    const thisBtn = document.getElementById('search-this-manual-btn');
    const allBtn = document.getElementById('search-all-manuals-btn');
    
    if (mode === 'this') {
        thisBtn.classList.add('bg-[#F97316]/20', 'border-[#F97316]/50', 'text-[#F97316]');
        thisBtn.classList.remove('bg-white/5', 'border-white/20', 'text-white/70');
        allBtn.classList.remove('bg-[#F97316]/20', 'border-[#F97316]/50', 'text-[#F97316]');
        allBtn.classList.add('bg-white/5', 'border-white/20', 'text-white/70');
    } else {
        allBtn.classList.add('bg-[#F97316]/20', 'border-[#F97316]/50', 'text-[#F97316]');
        allBtn.classList.remove('bg-white/5', 'border-white/20', 'text-white/70');
        thisBtn.classList.remove('bg-[#F97316]/20', 'border-[#F97316]/50', 'text-[#F97316]');
        thisBtn.classList.add('bg-white/5', 'border-white/20', 'text-white/70');
    }
}

// ============================================================================
// FEATURE 4: Tribal Knowledge - Field Notes
// ============================================================================

function showFieldNoteForm() {
    const form = document.getElementById('field-note-form');
    if (form) form.classList.remove('hidden');
}

function markAnswerComplete() {
    // User confirmed answer is accurate
    console.log('Answer marked as complete');
    // Could send analytics or update UI
}

async function saveFieldNote() {
    const noteInput = document.getElementById('field-note-input');
    const nameInput = document.getElementById('field-note-name');
    
    if (!noteInput.value || !nameInput.value) {
        alert('Please fill in both the note and your name');
        return;
    }
    
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/tribal/add`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                technician_note: noteInput.value,
                added_by_name: nameInput.value,
                voice_query: false
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Field note saved successfully!');
            noteInput.value = '';
            nameInput.value = '';
            document.getElementById('field-note-form').classList.add('hidden');
        } else {
            alert('Failed to save field note: ' + (result.error || 'Unknown error'));
        }
    } catch (err) {
        console.error('Save field note error:', err);
        alert('Failed to save field note. Please try again.');
    }
}

// ============================================================================
// FEATURE 5: Work Orders
// ============================================================================

let currentNewWOPriority = 'MEDIUM';
let currentWorkOrders = [];
let currentWorkOrderId = null;
let currentFilter = 'all';
let currentAssetFilter = '';
let currentStatusFilter = '';
let currentSearchFilter = '';
let selectedPriorities = new Set(['all']);
let searchDebounceTimer = null;

// ---------------------------------------------------------------------------
// Helper: Update onboarding vs live feed panels based on manuals availability
function updateChatPanels() {
    const manuals = JSON.parse(localStorage.getItem('indexfield_demo_manuals') || '[]');
    const onboarding = document.getElementById('chat-onboarding-checklist');
    const liveFeed = document.getElementById('chat-live-feed');
    const docViewer = document.getElementById('chat-doc-viewer');
    if (manuals.length > 0) {
        if (onboarding) onboarding.classList.add('hidden');
        if (liveFeed) liveFeed.classList.remove('hidden');
        if (docViewer) docViewer.classList.remove('hidden');
    } else {
        if (onboarding) onboarding.classList.remove('hidden');
        if (liveFeed) liveFeed.classList.add('hidden');
        if (docViewer) docViewer.classList.add('hidden');
    }
}

// Load Recent AI Answers into the sidebar panel
async function loadRecentAIAnswers() {
    const container = document.getElementById('recent-ai-answers-list');
    if (!container) return;
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/ai/recent-answers`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        container.innerHTML = '';
        data.answers.forEach(item => {
            const div = document.createElement('div');
            div.className = 'p-2 bg-white/5 rounded border border-white/10';
            div.innerHTML = `<div class="text-xs text-slate-400">${item.time} – ${item.user_name}</div>`+
                `<div class="text-sm text-white">${item.answer}</div>`;
            container.appendChild(div);
        });
    } catch (e) {
        console.error('Failed to load recent AI answers', e);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateChatPanels();
    loadRecentAIAnswers();
});

// Priority selection
function setNewWOPriority(priority) {
    currentNewWOPriority = priority;
    document.querySelectorAll('.new-wo-priority-btn').forEach(btn => {
        btn.classList.remove('bg-[#F97316]/20', 'border-[#F97316]/50', 'text-[#F97316]', 'bg-[#EF4444]/20', 'border-[#EF4444]/50', 'text-[#EF4444]', 'bg-[#64748B]/20', 'border-[#64748B]/50', 'text-[#64748B]');
        btn.classList.add('bg-black/30', 'border-white/20', 'text-white');
    });
    
    const colors = {
        'CRITICAL': ['bg-[#EF4444]/20', 'border-[#EF4444]/50', 'text-[#EF4444]'],
        'HIGH': ['bg-[#F97316]/20', 'border-[#F97316]/50', 'text-[#F97316]'],
        'MEDIUM': ['bg-[#FACC15]/20', 'border-[#FACC15]/50', 'text-[#FACC15]'],
        'LOW': ['bg-[#64748B]/20', 'border-[#64748B]/50', 'text-[#64748B]']
    };
    
    if (event && event.target) {
        event.target.classList.remove('bg-black/30', 'border-white/20', 'text-white');
        event.target.classList.add(...colors[priority]);
    }
}

// Modal controls
function openCreateWorkOrderModal() {
    const modal = document.getElementById('create-wo-modal');
    if (modal) {
        modal.classList.remove('hidden');
        loadAssetsDropdown('new-wo-asset');
    }
}

function closeCreateWorkOrderModal() {
    const modal = document.getElementById('create-wo-modal');
    if (modal) modal.classList.add('hidden');
    resetCreateForm();
}

function resetCreateForm() {
    document.getElementById('new-wo-title').value = '';
    document.getElementById('new-wo-asset').value = '';
    document.getElementById('new-wo-description').value = '';
    document.getElementById('new-wo-assign').value = '';
    document.getElementById('new-wo-due-date').value = '';
    document.getElementById('new-wo-hours').value = '';
    document.getElementById('procedure-steps-container').innerHTML = `
        <div class="flex gap-2">
            <input type="text" class="procedure-step-input flex-1 px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-sm text-white placeholder-slate-400 focus:border-[#F97316]/50 focus:outline-none" placeholder="Step 1">
            <button type="button" onclick="addProcedureStep()" class="px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-xs text-white hover:bg-white/20 transition-all">+ ADD STEP</button>
        </div>
    `;
    setNewWOPriority('MEDIUM');
}

// Procedure steps
function addProcedureStep() {
    const container = document.getElementById('procedure-steps-container');
    const stepCount = container.querySelectorAll('.procedure-step-input').length + 1;
    const stepDiv = document.createElement('div');
    stepDiv.className = 'flex gap-2';
    stepDiv.innerHTML = `
        <input type="text" class="procedure-step-input flex-1 px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-sm text-white placeholder-slate-400 focus:border-[#F97316]/50 focus:outline-none" placeholder="Step ${stepCount}">
        <button type="button" onclick="this.parentElement.remove()" class="px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-500 hover:bg-red-500/20 transition-all">Remove</button>
    `;
    container.appendChild(stepDiv);
}

function getProcedureSteps() {
    const inputs = document.querySelectorAll('.procedure-step-input');
    return Array.from(inputs).map(input => input.value).filter(val => val.trim() !== '');
}

// Create work order
async function createNewWorkOrder() {
    const title = document.getElementById('new-wo-title').value;
    const assetSelect = document.getElementById('new-wo-asset');
    const assetName = assetSelect.options[assetSelect.selectedIndex]?.text || 'Unknown Asset';
    const assetId = assetSelect.value || null;
    const description = document.getElementById('new-wo-description').value;
    const assign = document.getElementById('new-wo-assign').value;
    const dueDate = document.getElementById('new-wo-due-date').value;
    const hours = document.getElementById('new-wo-hours').value;
    const procedureSteps = getProcedureSteps();
    
    if (!title) {
        alert('Please fill in title');
        return;
    }
    
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/workorders/create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                asset_id: assetId,
                asset_name: assetName,
                title: title,
                description: description,
                priority: currentNewWOPriority,
                assigned_to: assign,
                estimated_hours: hours ? parseFloat(hours) : null,
                due_date: dueDate || null,
                procedure_steps: procedureSteps,
                created_from: 'MANUAL'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Save guest work order to localStorage
            if (result.message && result.message.includes('local-only')) {
                const guestWorkOrders = JSON.parse(localStorage.getItem('guest_work_orders') || '[]');
                guestWorkOrders.push(result);
                localStorage.setItem('guest_work_orders', JSON.stringify(guestWorkOrders));
            }
            
            showToast('Work order created successfully', 'brand');
            closeCreateWorkOrderModal();
            loadWorkOrders();
        } else if (response.status === 402) {
            // Paywall trigger
            alert('Sandbox limit reached: Maximum 2 work orders allowed. Upgrade to continue.');
        } else {
            alert('Failed to create work order: ' + (result.detail || 'Unknown error'));
        }
    } catch (err) {
        console.error('Create work order error:', err);
        alert('Failed to create work order. Please try again.');
    }
}

async function createNewWorkOrderWithAI() {
    // First create the work order
    const title = document.getElementById('new-wo-title').value;
    const assetSelect = document.getElementById('new-wo-asset');
    const assetName = assetSelect.options[assetSelect.selectedIndex]?.text || 'Unknown Asset';
    const assetId = assetSelect.value || null;
    const description = document.getElementById('new-wo-description').value;
    const assign = document.getElementById('new-wo-assign').value;
    const dueDate = document.getElementById('new-wo-due-date').value;
    const hours = document.getElementById('new-wo-hours').value;
    const procedureSteps = getProcedureSteps();
    
    // Get modal content for error handling
    const modalContent = document.querySelector('#create-wo-modal .glass-card');
    const originalContent = modalContent ? modalContent.innerHTML : '';
    
    if (!title) {
        alert('Please fill in title');
        return;
    }
    
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/workorders/create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                asset_id: assetId,
                asset_name: assetName,
                title: title,
                description: description,
                priority: currentNewWOPriority,
                assigned_to: assign,
                estimated_hours: hours ? parseFloat(hours) : null,
                due_date: dueDate || null,
                procedure_steps: procedureSteps,
                created_from: 'MANUAL'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Show terminal animation in modal
            if (modalContent) {
                modalContent.innerHTML = `
                    <div class="terminal-thinking font-mono text-sm space-y-2 py-8">
                        <div class="text-slate-400 hidden">[▸] SEARCHING YOUR MANUALS...</div>
                        <div class="text-slate-400 hidden">[▸] EXTRACTING RELEVANT PROCEDURES...</div>
                        <div class="text-slate-400 hidden">[▸] ATTACHING SAFETY REQUIREMENTS...</div>
                        <div class="text-[#22C55E] font-bold hidden">[✓] BRIEFING COMPLETE</div>
                    </div>
                `;
            }
            // Animate lines
            if (modalContent) {
                const lines = modalContent.querySelectorAll('.terminal-thinking > div');
                for (let i = 0; i < lines.length; i++) {
                    await new Promise(resolve => setTimeout(resolve, 500));
                    lines[i].classList.remove('hidden');
                }
            }
            
            // Generate AI briefing
            await generateAIBriefingForWO(result.work_order_id);
            
            showToast('Work order created with AI briefing', 'brand');
            closeCreateWorkOrderModal();
            loadWorkOrders();
            updateKPIFromCurrentData();
        } else if (response.status === 402) {
            // Paywall trigger
            alert('Sandbox limit reached: Maximum 2 work orders allowed. Upgrade to continue.');
            closeCreateWorkOrderModal();
        } else {
            alert('Failed to create work order: ' + (result.detail || 'Unknown error'));
            if (modalContent) {
                modalContent.innerHTML = originalContent;
            }
        }
    } catch (err) {
        console.error('Create work order error:', err);
        alert('Failed to create work order. Please try again.');
    }
}

// Load work orders
async function loadWorkOrders() {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        let url = `${API_URL}/api/workorders`;
        const params = [];
        
        if (currentFilter !== 'all') params.push(`priority_filter=${currentFilter}`);
        if (currentStatusFilter) params.push(`status_filter=${currentStatusFilter}`);
        if (currentAssetFilter) params.push(`asset_id_filter=${currentAssetFilter}`);
        
        if (params.length > 0) url += '?' + params.join('&');
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        currentWorkOrders = Array.isArray(data) ? data : [];
        
        // Load guest work orders from localStorage
        const guestWorkOrders = JSON.parse(localStorage.getItem('guest_work_orders') || '[]');
        if (guestWorkOrders.length > 0) {
            currentWorkOrders = [...currentWorkOrders, ...guestWorkOrders];
        }
        
        // Populate assets dropdown
        loadAssetsDropdown('new-wo-asset');
        loadAssetsDropdown('asset-filter');
        
        renderWorkOrdersTable();
        updateEmptyState();
        updateKPIFromCurrentData();
    } catch (err) {
        console.error('Load work orders error:', err);
    }
}

// Load work order stats
async function loadWorkOrderStats() {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/workorders/stats`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const stats = await response.json();
        
        document.getElementById('kpi-critical-open').textContent = stats.critical_open;
        document.getElementById('kpi-high-priority').textContent = stats.high_priority;
        
        const dueTodayEl = document.getElementById('kpi-due-today');
        dueTodayEl.textContent = stats.due_today;
        dueTodayEl.className = `text-2xl font-bold ${stats.due_today > 0 ? 'text-[#F97316]' : 'text-slate-400'}`;
        
        document.getElementById('kpi-completed-week').textContent = stats.completed_this_week;
    } catch (err) {
        console.error('Load work order stats error:', err);
    }
}

// Update KPI cards from current table data (no API call)
function updateKPIFromCurrentData() {
    const criticalOpen = currentWorkOrders.filter(wo => 
        wo.priority === 'CRITICAL' && wo.status === 'OPEN'
    ).length;
    
    const highPriority = currentWorkOrders.filter(wo => 
        wo.priority === 'HIGH' && (wo.status === 'OPEN' || wo.status === 'IN_PROGRESS')
    ).length;
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dueToday = currentWorkOrders.filter(wo => {
        if (!wo.due_date || wo.status === 'COMPLETE' || wo.status === 'CANCELLED') return false;
        const dueDate = new Date(wo.due_date);
        dueDate.setHours(0, 0, 0, 0);
        return dueDate.getTime() === today.getTime() || dueDate < today;
    }).length;
    
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    const completedThisWeek = currentWorkOrders.filter(wo => {
        if (!wo.completed_at || wo.status !== 'COMPLETE') return false;
        const completedDate = new Date(wo.completed_at);
        return completedDate >= weekAgo;
    }).length;
    
    document.getElementById('kpi-critical-open').textContent = criticalOpen;
    document.getElementById('kpi-high-priority').textContent = highPriority;
    
    const dueTodayEl = document.getElementById('kpi-due-today');
    dueTodayEl.textContent = dueToday;
    dueTodayEl.className = `text-2xl font-bold ${dueToday > 0 ? 'text-[#F97316]' : 'text-slate-400'}`;
    
    document.getElementById('kpi-completed-week').textContent = completedThisWeek;
}

// Render work orders table
function renderWorkOrdersTable() {
    const tbody = document.getElementById('work-orders-table-body');
    if (!tbody) return;
    
    let filteredOrders = [...currentWorkOrders];
    
    // Apply priority filter (multi-select)
    if (!selectedPriorities.has('all')) {
        filteredOrders = filteredOrders.filter(wo => selectedPriorities.has(wo.priority.toLowerCase()));
    }
    
    // Apply status filter
    if (currentStatusFilter) {
        filteredOrders = filteredOrders.filter(wo => wo.status === currentStatusFilter);
    }
    
    // Apply asset filter
    if (currentAssetFilter) {
        filteredOrders = filteredOrders.filter(wo => wo.asset_id === currentAssetFilter);
    }
    
    // Apply search filter (title, asset name, assigned to, WO ID)
    if (currentSearchFilter) {
        const searchLower = currentSearchFilter.toLowerCase();
        filteredOrders = filteredOrders.filter(wo => {
            const woId = generateWOId(wo.id).toLowerCase();
            return wo.title.toLowerCase().includes(searchLower) ||
                   (wo.asset_name && wo.asset_name.toLowerCase().includes(searchLower)) ||
                   (wo.assigned_to && wo.assigned_to.toLowerCase().includes(searchLower)) ||
                   woId.includes(searchLower);
        });
    }
    
    // Sort: CRITICAL+OVERDUE absolute top, CRITICAL OPEN next, HIGH OVERDUE next, then by due date
    filteredOrders.sort((a, b) => {
        const priorityOrder = { 'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3 };
        const aPriority = priorityOrder[a.priority] || 99;
        const bPriority = priorityOrder[b.priority] || 99;
        
        // CRITICAL + OVERDUE at top
        const aCriticalOverdue = a.priority === 'CRITICAL' && (a.status === 'OVERDUE' || isOverdue(a));
        const bCriticalOverdue = b.priority === 'CRITICAL' && (b.status === 'OVERDUE' || isOverdue(b));
        
        if (aCriticalOverdue && !bCriticalOverdue) return -1;
        if (!aCriticalOverdue && bCriticalOverdue) return 1;
        
        // CRITICAL OPEN next
        const aCriticalOpen = a.priority === 'CRITICAL' && a.status === 'OPEN';
        const bCriticalOpen = b.priority === 'CRITICAL' && b.status === 'OPEN';
        
        if (aCriticalOpen && !bCriticalOpen) return -1;
        if (!aCriticalOpen && bCriticalOpen) return 1;
        
        // HIGH OVERDUE next
        const aHighOverdue = a.priority === 'HIGH' && (a.status === 'OVERDUE' || isOverdue(a));
        const bHighOverdue = b.priority === 'HIGH' && (b.status === 'OVERDUE' || isOverdue(b));
        
        if (aHighOverdue && !bHighOverdue) return -1;
        if (!aHighOverdue && bHighOverdue) return 1;
        
        // Then by priority
        if (aPriority !== bPriority) return aPriority - bPriority;
        
        // Then by due date (ascending)
        if (a.due_date && b.due_date) {
            return new Date(a.due_date) - new Date(b.due_date);
        }
        if (a.due_date && !b.due_date) return -1;
        if (!a.due_date && b.due_date) return 1;
        
        return 0;
    });
    
    if (filteredOrders.length === 0) {
        tbody.innerHTML = '';
        return;
    }
    
    tbody.innerHTML = filteredOrders.map(wo => {
        const woId = generateWOId(wo.id);
        const priorityDot = getPriorityDot(wo.priority);
        const dueDateDisplay = getDueDateDisplay(wo.due_date, wo.status);
        const aiBriefedDisplay = wo.ai_briefed 
            ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#F97316]/20 text-[#F97316] border border-[#F97316]/30">AI</span>'
            : `<a href="#" onclick="event.stopPropagation(); generateAIBriefingForWO('${wo.id}')" class="text-[10px] text-[#F97316] hover:underline">[BRIEF →]</a>`;
        
        return `
            <tr class="hover:bg-white/5 cursor-pointer" onclick="openWorkOrderDetail('${wo.id}')">
                <td class="px-4 py-3">${priorityDot}</td>
                <td class="px-4 py-3 font-mono text-xs text-slate-400">${woId}</td>
                <td class="px-4 py-3 text-sm truncate max-w-[200px]">${wo.title}</td>
                <td class="px-4 py-3 text-sm">${wo.asset_name || '<span class="text-slate-500">UNLINKED</span>'}</td>
                <td class="px-4 py-3 text-sm ${wo.assigned_to ? '' : 'text-[#F97316]'}">${wo.assigned_to || 'UNASSIGNED'}</td>
                <td class="px-4 py-3 text-sm">${dueDateDisplay}</td>
                <td class="px-4 py-3">${aiBriefedDisplay}</td>
                <td class="px-4 py-3">${getStatusBadge(wo.status)}</td>
                <td class="px-4 py-3">
                    <div class="relative">
                        <button onclick="event.stopPropagation(); toggleWODropdown('${wo.id}')" class="text-slate-400 hover:text-white">
                            <i class="fas fa-ellipsis-h"></i>
                        </button>
                        <div id="wo-dropdown-${wo.id}" class="hidden absolute right-0 mt-2 w-48 bg-[#1F2937] border border-white/10 rounded-lg shadow-xl z-10">
                            <a href="#" onclick="event.stopPropagation(); openWorkOrderDetail('${wo.id}')" class="block px-4 py-2 text-sm text-white hover:bg-white/10">Open Detail</a>
                            <a href="#" onclick="event.stopPropagation(); showInlineAssignModal('${wo.id}')" class="block px-4 py-2 text-sm text-white hover:bg-white/10">Assign</a>
                            <a href="#" onclick="event.stopPropagation(); markWorkOrderComplete('${wo.id}')" class="block px-4 py-2 text-sm text-white hover:bg-white/10">Mark Complete</a>
                            <a href="#" onclick="event.stopPropagation(); cancelWorkOrder('${wo.id}')" class="block px-4 py-2 text-sm text-white hover:bg-white/10">Cancel</a>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function isOverdue(wo) {
    if (!wo.due_date || wo.status === 'COMPLETE' || wo.status === 'CANCELLED') return false;
    const dueDate = new Date(wo.due_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dueDateOnly = new Date(dueDate);
    dueDateOnly.setHours(0, 0, 0, 0);
    return dueDateOnly < today;
}

function generateWOId(id) {
    // Generate WO-XXXX format from ID
    const num = parseInt(id.slice(0, 8), 16) % 10000;
    return `WO-${String(num).padStart(4, '0')}`;
}

function getPriorityDot(priority) {
    const colors = {
        'CRITICAL': 'bg-[#EF4444]',
        'HIGH': 'bg-[#F97316]',
        'MEDIUM': 'bg-[#FACC15]',
        'LOW': 'bg-[#64748B]'
    };
    return `<div class="w-3 h-3 rounded-full ${colors[priority] || 'bg-slate-500'}"></div>`;
}

function getDueDateDisplay(dueDate, status) {
    if (!dueDate) return '--';
    
    const due = new Date(dueDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dueDateOnly = new Date(due);
    dueDateOnly.setHours(0, 0, 0, 0);
    
    const diffDays = Math.floor((dueDateOnly - today) / (1000 * 60 * 60 * 24));
    
    if (status === 'OVERDUE' || diffDays < 0) {
        return `<span class="text-[#EF4444]">${due.toLocaleDateString()}</span> <span class="ml-1 px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#EF4444]/20 text-[#EF4444] border border-[#EF4444]/30">OVERDUE</span>`;
    } else if (diffDays === 0) {
        return `<span class="text-[#F97316]">${due.toLocaleDateString()}</span> <span class="ml-1 px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#F97316]/20 text-[#F97316] border border-[#F97316]/30">TODAY</span>`;
    } else if (diffDays <= 3) {
        return `<span class="text-[#F97316]">${due.toLocaleDateString()}</span>`;
    }
    
    return due.toLocaleDateString();
}

function getStatusBadge(status) {
    const styles = {
        'OPEN': 'border border-white/20 text-slate-400',
        'IN_PROGRESS': 'bg-blue-500/20 text-blue-500 border border-blue-500/30',
        'COMPLETE': 'bg-[#22C55E]/20 text-[#22C55E] border border-[#22C55E]/30',
        'OVERDUE': 'bg-[#EF4444]/20 text-[#EF4444] border border-[#EF4444]/30',
        'CANCELLED': 'border border-white/20 text-slate-400 line-through'
    };
    
    return `<span class="px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider ${styles[status] || styles['OPEN']}">${status.replace('_', ' ')}</span>`;
}

function updateEmptyState() {
    const emptyState = document.getElementById('empty-state');
    const table = document.getElementById('work-orders-table-body');
    
    if (emptyState && table) {
        if (currentWorkOrders.length === 0) {
            emptyState.classList.remove('hidden');
            table.parentElement.classList.add('hidden');
        } else {
            emptyState.classList.add('hidden');
            table.parentElement.classList.remove('hidden');
        }
    }
}

// Filters - multi-select priority pills
function filterWorkOrders(priority) {
    if (priority === 'all') {
        selectedPriorities.clear();
        selectedPriorities.add('all');
    } else {
        selectedPriorities.delete('all');
        if (selectedPriorities.has(priority)) {
            selectedPriorities.delete(priority);
        } else {
            selectedPriorities.add(priority);
        }
        if (selectedPriorities.size === 0) {
            selectedPriorities.add('all');
        }
    }
    
    // Update button styles
    document.querySelectorAll('.wo-filter-btn').forEach(btn => {
        const btnPriority = btn.textContent.toLowerCase();
        if (selectedPriorities.has(btnPriority) || (btnPriority === 'all' && selectedPriorities.has('all'))) {
            btn.classList.remove('bg-white/5', 'border-white/20', 'text-white');
            btn.classList.add('bg-[#F97316]/20', 'border-[#F97316]/50', 'text-[#F97316]');
        } else {
            btn.classList.remove('bg-[#F97316]/20', 'border-[#F97316]/50', 'text-[#F97316]');
            btn.classList.add('bg-white/5', 'border-white/20', 'text-white');
        }
    });
    
    renderWorkOrdersTable();
}

function filterByAsset(assetId) {
    currentAssetFilter = assetId;
    loadWorkOrders();
}

function filterByStatus(status) {
    currentStatusFilter = status;
    renderWorkOrdersTable();
}

function filterBySearch() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        currentSearchFilter = document.getElementById('search-filter').value;
        renderWorkOrdersTable();
    }, 200);
}

// Load assets dropdown
async function loadAssetsDropdown(elementId) {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/assets`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const assets = await response.json();
        const select = document.getElementById(elementId);
        if (select) {
            select.innerHTML = '<option value="">Select Asset</option>' + 
                assets.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
        }
    } catch (err) {
        console.error('Load assets error:', err);
    }
}

// Work order detail drawer
async function openWorkOrderDetail(woId) {
    currentWorkOrderId = woId;
    const drawer = document.getElementById('wo-detail-drawer');
    
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/workorders`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const workOrders = await response.json();
        const workOrder = workOrders.find(wo => wo.id === woId);
        
        if (workOrder) {
            populateDetailDrawer(workOrder);
            drawer.classList.remove('translate-x-full');
        }
    } catch (err) {
        console.error('Load work order detail error:', err);
    }
}

function populateDetailDrawer(wo) {
    const woId = generateWOId(wo.id);
    
    document.getElementById('detail-wo-id').textContent = woId;
    document.getElementById('detail-title').textContent = wo.title;
    document.getElementById('detail-assigned-to').textContent = wo.assigned_to || 'UNASSIGNED';
    document.getElementById('detail-due-date').textContent = wo.due_date ? new Date(wo.due_date).toLocaleDateString() : '--';
    document.getElementById('detail-estimated-hours').textContent = wo.estimated_hours || '--';
    document.getElementById('detail-created').textContent = wo.created_at ? new Date(wo.created_at).toLocaleDateString() : '--';
    document.getElementById('detail-created-from').textContent = wo.created_from || 'MANUAL';
    
    // Priority badge
    const priorityBadge = document.getElementById('detail-priority-badge');
    const priorityColors = {
        'CRITICAL': ['bg-[#EF4444]/20', 'text-[#EF4444]', 'border-[#EF4444]/30'],
        'HIGH': ['bg-[#F97316]/20', 'text-[#F97316]', 'border-[#F97316]/30'],
        'MEDIUM': ['bg-[#FACC15]/20', 'text-[#FACC15]', 'border-[#FACC15]/30'],
        'LOW': ['bg-[#64748B]/20', 'text-[#64748B]', 'border-[#64748B]/30']
    };
    const colors = priorityColors[wo.priority] || priorityColors['MEDIUM'];
    priorityBadge.className = `px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${colors[0]} ${colors[1]} border ${colors[2]}`;
    priorityBadge.textContent = wo.priority;
    
    // Status badge
    const statusBadge = document.getElementById('detail-status-badge');
    statusBadge.outerHTML = getStatusBadge(wo.status).replace('span', 'span id="detail-status-badge"');
    
    // Asset link
    const assetLink = document.getElementById('detail-asset-link');
    assetLink.textContent = wo.asset_name || 'UNLINKED';
    assetLink.href = wo.asset_id ? `#assets?asset=${wo.asset_id}` : '#';
    
    // Procedure steps
    const stepsContainer = document.getElementById('detail-procedure-steps');
    const noSteps = document.getElementById('no-procedure-steps');
    
    if (wo.procedure_steps && wo.procedure_steps.length > 0) {
        stepsContainer.innerHTML = wo.procedure_steps.map((step, i) => `
            <div class="flex gap-3 text-sm">
                <span class="text-[#F97316] font-bold">${i + 1}.</span>
                <span class="text-slate-300">${step}</span>
            </div>
        `).join('');
        stepsContainer.classList.remove('hidden');
        noSteps.classList.add('hidden');
    } else {
        stepsContainer.classList.add('hidden');
        noSteps.classList.remove('hidden');
    }
    
    // AI briefing
    const briefingContainer = document.getElementById('detail-ai-briefing');
    const noBriefing = document.getElementById('no-ai-briefing');
    
    if (wo.ai_briefed && wo.ai_briefing) {
        briefingContainer.innerHTML = wo.ai_briefing.sources.map(source => `
            <div class="p-3 bg-white/5 rounded-lg border border-white/10">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-sm font-semibold text-white">${source.document_name}</span>
                    <span class="px-2 py-0.5 rounded text-[9px] font-bold ${source.confidence === 'HIGH' ? 'bg-[#22C55E]/20 text-[#22C55E]' : 'bg-[#FACC15]/20 text-[#FACC15]'}">${source.confidence}</span>
                </div>
                <div class="text-xs text-slate-400 mb-1">Page ${source.page} · ${source.section}</div>
                <div class="text-sm text-slate-300">${source.summary}</div>
                <a href="#" class="text-[10px] text-[#F97316] hover:underline mt-2 inline-block">VIEW PAGE →</a>
            </div>
        `).join('');
        briefingContainer.classList.remove('hidden');
        noBriefing.classList.add('hidden');
    } else {
        briefingContainer.classList.add('hidden');
        noBriefing.classList.remove('hidden');
    }
    
    // Asset history (placeholder)
    document.getElementById('detail-asset-history').innerHTML = `
        <div class="text-slate-400">Last service: ${wo.asset_name ? 'Not available' : '--'}</div>
        <div class="text-slate-400">Previous work orders: None</div>
    `;
    
    // Notes
    const notesContainer = document.getElementById('detail-notes');
    if (wo.notes && Array.isArray(wo.notes)) {
        notesContainer.innerHTML = wo.notes.map(note => `
            <div class="p-2 bg-white/5 rounded-lg">
                <div class="flex items-center justify-between mb-1">
                    <span class="text-xs font-semibold text-white">${note.author}</span>
                    <span class="text-[10px] text-slate-500">${new Date(note.timestamp).toLocaleString()}</span>
                </div>
                <div class="text-sm text-slate-300">${note.text}</div>
            </div>
        `).join('');
    } else {
        notesContainer.innerHTML = '<div class="text-sm text-slate-400">No notes yet</div>';
    }
    
    // Action buttons based on status
    updateDetailActions(wo);
}

function updateDetailActions(wo) {
    const actionsContainer = document.getElementById('detail-actions');
    
    let buttons = '';
    
    if (wo.status === 'OPEN') {
        buttons = `
            <button onclick="startWorkOrder('${wo.id}')" class="w-full px-4 py-3 bg-[#F97316] text-black font-semibold rounded-lg text-sm hover:bg-[#EA580C] transition-all">
                START WORK ORDER
            </button>
            <button onclick="initiateLOTO('${wo.asset_id}', '${wo.id}')" class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-sm text-white hover:bg-white/20 transition-all">
                INITIATE LOTO →
            </button>
            <button onclick="assignWorkOrder('${wo.id}')" class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-sm text-white hover:bg-white/20 transition-all">
                ASSIGN TECHNICIAN
            </button>
            <button onclick="editWorkOrder('${wo.id}')" class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-sm text-white hover:bg-white/20 transition-all">
                EDIT
            </button>
        `;
    } else if (wo.status === 'IN_PROGRESS') {
        buttons = `
            <button onclick="markWorkOrderComplete('${wo.id}')" class="w-full px-4 py-3 bg-[#22C55E] text-black font-semibold rounded-lg text-sm hover:bg-[#16A34A] transition-all">
                MARK COMPLETE
            </button>
            <button onclick="addNoteToWO('${wo.id}')" class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-sm text-white hover:bg-white/20 transition-all">
                ADD NOTE
            </button>
            <button onclick="escalateWorkOrder('${wo.id}')" class="w-full px-4 py-3 bg-[#EF4444]/10 border border-[#EF4444]/30 rounded-lg text-sm text-[#EF4444] hover:bg-[#EF4444]/20 transition-all">
                ESCALATE TO CRITICAL
            </button>
            <button onclick="initiateLOTO('${wo.asset_id}', '${wo.id}')" class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-sm text-white hover:bg-white/20 transition-all">
                INITIATE LOTO →
            </button>
        `;
    } else if (wo.status === 'COMPLETE') {
        buttons = `
            <button onclick="viewCompletionReport('${wo.id}')" class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-sm text-white hover:bg-white/20 transition-all">
                VIEW COMPLETION REPORT
            </button>
            <button onclick="createFollowUpWO('${wo.id}')" class="w-full px-4 py-3 bg-[#F97316] text-black font-semibold rounded-lg text-sm hover:bg-[#EA580C] transition-all">
                CREATE FOLLOW-UP WO
            </button>
        `;
    }
    
    actionsContainer.innerHTML = buttons;
}

function closeDetailDrawer() {
    const drawer = document.getElementById('wo-detail-drawer');
    drawer.classList.add('translate-x-full');
    currentWorkOrderId = null;
}

// Work order actions
async function startWorkOrder(woId) {
    await updateWorkOrderStatus(woId, 'IN_PROGRESS');
}

async function markWorkOrderComplete(woId) {
    await updateWorkOrderStatus(woId, 'COMPLETE');
}

async function cancelWorkOrder(woId) {
    if (confirm('Are you sure you want to cancel this work order?')) {
        await updateWorkOrderStatus(woId, 'CANCELLED');
    }
}

async function escalateWorkOrder(woId) {
    const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
    await fetch(`${API_URL}/api/workorders/${woId}`, {
        method: 'PATCH',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            priority: 'CRITICAL'
        })
    });
    loadWorkOrders();
    updateKPIFromCurrentData();
    if (currentWorkOrderId) openWorkOrderDetail(currentWorkOrderId);
}

async function updateWorkOrderStatus(woId, status) {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const updateData = { status: status };
        
        if (status === 'COMPLETE') {
            updateData.completed_at = new Date().toISOString();
        }
        
        await fetch(`${API_URL}/api/workorders/${woId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });
        loadWorkOrders();
        updateKPIFromCurrentData();
        if (currentWorkOrderId) openWorkOrderDetail(currentWorkOrderId);
        showToast(`Work order ${status.replace('_', ' ')}`, 'brand');
    } catch (err) {
        console.error('Update work order error:', err);
    }
}

function assignWorkOrder(woId) {
    const name = prompt('Enter technician name:');
    if (name) {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        fetch(`${API_URL}/api/workorders/${woId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                assigned_to: name
            })
        }).then(() => {
            loadWorkOrders();
            if (currentWorkOrderId) openWorkOrderDetail(currentWorkOrderId);
        });
    }
}

function showInlineAssignModal(woId) {
    const dropdown = document.getElementById(`wo-dropdown-${woId}`);
    if (dropdown) dropdown.classList.add('hidden');
    
    const name = prompt('Enter technician name:');
    if (name) {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        fetch(`${API_URL}/api/workorders/${woId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                assigned_to: name
            })
        }).then(() => {
            loadWorkOrders();
            updateKPIFromCurrentData();
        });
    }
}

async function addNote() {
    const input = document.getElementById('new-note-input');
    const note = input.value.trim();
    
    if (!note || !currentWorkOrderId) return;
    
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        await fetch(`${API_URL}/api/workorders/${currentWorkOrderId}/notes`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                note: note
            })
        });
        
        input.value = '';
        openWorkOrderDetail(currentWorkOrderId);
        showToast('Note added', 'brand');
    } catch (err) {
        console.error('Add note error:', err);
    }
}

// AI Briefing
async function generateAIBriefingForWO(woId) {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/workorders/brief`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                work_order_id: woId
            })
        });
        
        const result = await response.json();
        
        if (result.sources) {
            showToast('AI briefing generated', 'brand');
            loadWorkOrders();
            if (currentWorkOrderId === woId) openWorkOrderDetail(woId);
        }
    } catch (err) {
        console.error('Generate AI briefing error:', err);
        if (err.message && err.message.includes('402')) {
            alert('Sandbox limit reached: Maximum 1 AI briefing allowed');
        } else {
            alert('Failed to generate AI briefing');
        }
    }
}

async function generateAIBriefing() {
    if (currentWorkOrderId) {
        await generateAIBriefingForWO(currentWorkOrderId);
    }
}

async function generateProcedureSteps() {
    // Placeholder for procedure step generation
    alert('Procedure step generation will be implemented with RAG integration');
}

// LOTO Integration
function initiateLOTO(assetId, woId) {
    window.location.href = `#loto?asset=${assetId}&wo=${woId}`;
}

// Generate from AI Modal
async function openGenerateAIModal() {
    const modal = document.getElementById('generate-ai-modal');
    if (modal) {
        modal.classList.remove('hidden');
        await runAITerminalAnimation();
    }
}

function closeGenerateAIModal() {
    const modal = document.getElementById('generate-ai-modal');
    if (modal) modal.classList.add('hidden');
    
    // Reset terminal
    document.getElementById('ai-terminal').classList.remove('hidden');
    document.getElementById('ai-suggestions-list').classList.add('hidden');
    document.getElementById('no-manuals-message').classList.add('hidden');
    document.getElementById('create-all-suggestions').classList.add('hidden');
    
    document.querySelectorAll('#ai-terminal .hidden').forEach(el => el.classList.add('hidden'));
}

async function runAITerminalAnimation() {
    const lines = ['terminal-line-1', 'terminal-line-2', 'terminal-line-3', 'terminal-line-4', 'terminal-line-5'];
    
    // Load suggestions first to get count
    const suggestions = await fetchSuggestions();
    
    for (let i = 0; i < lines.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 600));
        const line = document.getElementById(lines[i]);
        if (line) {
            line.classList.remove('hidden');
            line.classList.add('terminal-line');
            // Update last line with count
            if (i === 4) {
                line.textContent = `[✓] SUGGESTIONS READY — ${suggestions.length} FOUND`;
            }
        }
    }
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Display suggestions
    displaySuggestions(suggestions);
}

async function fetchSuggestions() {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/workorders/generate-suggestions`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.status === 402) {
            return [];
        }
        
        return await response.json();
    } catch (err) {
        console.error('Fetch suggestions error:', err);
        return [];
    }
}

function displaySuggestions(suggestions) {
    document.getElementById('ai-terminal').classList.add('hidden');
    
    if (suggestions.length === 0) {
        document.getElementById('no-manuals-message').classList.remove('hidden');
        document.querySelector('#no-manuals-message h4').textContent = 'UPLOAD MANUALS TO GENERATE SUGGESTIONS';
        document.querySelector('#no-manuals-message p').textContent = 'IndexField reads your maintenance manuals and automatically surfaces overdue and upcoming work orders.';
        document.querySelector('#no-manuals-message button').textContent = 'UPLOAD MANUAL →';
        document.querySelector('#no-manuals-message button').onclick = () => window.location.href = '#manuals';
    } else {
        document.getElementById('ai-suggestions-list').classList.remove('hidden');
        document.getElementById('create-all-suggestions').classList.remove('hidden');
        
        document.getElementById('ai-suggestions-list').innerHTML = suggestions.map(s => `
            <div class="p-4 bg-white/5 rounded-xl border border-white/10">
                <div class="flex items-start justify-between mb-3">
                    <div>
                        <h4 class="font-bold text-white">${s.asset_name}</h4>
                        <p class="text-sm text-slate-400">${s.description}</p>
                    </div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${getPriorityClass(s.priority)}">${s.priority}</span>
                </div>
                <div class="text-xs text-slate-500 mb-2">
                    Source: ${s.source} · Interval: ${s.interval} · Last: ${s.last_completed}
                </div>
                <button onclick="createSuggestedWO('${s.asset_id}', '${s.asset_name}', '${s.title}', '${s.description}', '${s.priority}')" class="px-3 py-1.5 bg-[#F97316] text-black font-semibold rounded-lg text-xs hover:bg-[#EA580C] transition-all">
                    CREATE WORK ORDER →
                </button>
            </div>
        `).join('');
    }
}


async function createSuggestedWO(assetId, assetName, title, description, priority) {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/workorders/create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                asset_id: assetId,
                asset_name: assetName,
                title: title,
                description: description,
                priority: priority,
                created_from: 'AI_SUGGESTION'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Work order created from AI suggestion', 'brand');
            loadWorkOrders();
            loadWorkOrderStats();
        }
    } catch (err) {
        console.error('Create suggested WO error:', err);
        alert('Failed to create work order');
    }
}

async function createAllSuggestions() {
    // Get all suggestion cards and create WOs for each
    const buttons = document.querySelectorAll('#ai-suggestions-list button');
    for (const btn of buttons) {
        btn.click();
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    closeGenerateAIModal();
}

function navigateToAssets() {
    window.location.href = '#assets';
}

// Dropdown toggle
function toggleWODropdown(woId) {
    const dropdown = document.getElementById(`wo-dropdown-${woId}`);
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.relative')) {
        document.querySelectorAll('[id^="wo-dropdown-"]').forEach(d => d.classList.add('hidden'));
    }
});

// Placeholder functions
function editWorkOrder(woId) {
    alert('Edit functionality to be implemented');
}

function viewCompletionReport(woId) {
    alert('Completion report to be implemented');
}

function createFollowUpWO(woId) {
    alert('Follow-up WO creation to be implemented');
}

function addNoteToWO(woId) {
    document.getElementById('new-note-input').focus();
}

// ============================================================================
// FEATURE 2: Shift Handover
// ============================================================================

let activeHandoverBrief = null;
let pendingIncomingBrief = null;
let shiftIndicatorInterval = null;

// Hook into showView to trigger page loading
const originalShowView = window.showView;
window.showView = function(view) {
    if (originalShowView) originalShowView(view);
    if (view === 'handover') {
        loadHandoverPageData();
    }
};

function startShiftIndicator() {
    if (shiftIndicatorInterval) clearInterval(shiftIndicatorInterval);
    updateShiftIndicator();
    shiftIndicatorInterval = setInterval(updateShiftIndicator, 10000); // Update every 10s
}

function updateShiftIndicator() {
    const now = new Date();
    const hours = now.getHours();
    let shiftName = '';
    let startHour = 0;
    let startTime = new Date(now);
    
    if (hours >= 6 && hours < 18) {
        shiftName = 'DAY SHIFT';
        startHour = 6;
        startTime.setHours(6, 0, 0, 0);
    } else {
        shiftName = 'NIGHT SHIFT';
        startHour = 18;
        if (hours < 6) {
            startTime.setDate(startTime.getDate() - 1);
        }
        startTime.setHours(18, 0, 0, 0);
    }
    
    const elapsedMs = now - startTime;
    const elapsedHrs = Math.floor(elapsedMs / 3600000);
    const elapsedMins = Math.floor((elapsedMs % 3600000) / 60000);
    
    const startStr = String(startHour).padStart(2, '0') + ':00';
    const elapsedStr = `${elapsedHrs}h ${elapsedMins}m elapsed`;
    
    const text = `${shiftName} · Started ${startStr} · ${elapsedStr}`;
    const indicator = document.getElementById('current-shift-indicator');
    if (indicator) {
        indicator.innerHTML = `<span class="w-2 h-2 rounded-full bg-[#F97316] animate-pulse"></span> ${text}`;
    }
}

async function loadHandoverPageData() {
    startShiftIndicator();
    await loadHandoverHistory();
}

async function loadHandoverHistory() {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/handover/history`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const handovers = await response.json();
        
        // Populate KPIs
        updateHandoverKPIs(handovers);
        
        // Populate previous handovers table
        const tbody = document.getElementById('previous-handovers-tbody');
        const emptyState = document.getElementById('handovers-empty-state');
        const tableContainer = document.getElementById('previous-handovers-container');
        
        if (tbody) {
            if (handovers.length === 0) {
                if (emptyState) emptyState.classList.remove('hidden');
                if (tableContainer) tableContainer.classList.add('hidden');
                tbody.innerHTML = '';
            } else {
                if (emptyState) emptyState.classList.add('hidden');
                if (tableContainer) tableContainer.classList.remove('hidden');
                
                tbody.innerHTML = handovers.map((h, index) => {
                    const statusColors = {
                        'GREEN': 'text-[#22C55E]',
                        'AMBER': 'text-[#FACC15]',
                        'RED': 'text-[#EF4444]'
                    };
                    const statusDot = statusColors[h.overall_status] || 'text-white';
                    
                    const ackText = h.acknowledged_by 
                        ? `✓ ${h.acknowledged_by} · ${new Date(h.acknowledged_at).toLocaleDateString()}` 
                        : `<span class="text-[#F97316] font-bold">PENDING</span>`;
                        
                    const criticalCount = Array.isArray(h.critical_items) ? h.critical_items.length : 0;
                    
                    return `
                        <tr class="hover:bg-white/5 cursor-pointer" onclick="openHandoverHistoryDrawer('${h.id}')">
                            <td class="py-3 font-mono">${new Date(h.created_at).toLocaleDateString()}</td>
                            <td class="py-3 font-bold">${h.shift_type} SHIFT</td>
                            <td class="py-3 font-bold"><span class="${statusDot}">●</span> ${h.overall_status}</td>
                            <td class="py-3 font-mono">${criticalCount} items</td>
                            <td class="py-3">${h.generated_by_name || 'Shift Lead'}</td>
                            <td class="py-3">${ackText}</td>
                            <td class="py-3 text-right" onclick="event.stopPropagation()">
                                <div class="relative inline-block text-left">
                                    <button onclick="toggleBriefDropdown('${h.id}')" class="text-slate-400 hover:text-white p-1">
                                        <i class="fas fa-ellipsis-v"></i>
                                    </button>
                                    <div id="brief-dropdown-${h.id}" class="hidden absolute right-0 mt-2 w-40 bg-[#1F2937] border border-white/10 rounded-lg shadow-xl z-20">
                                        <a href="#" onclick="event.stopPropagation(); openHandoverHistoryDrawer('${h.id}')" class="block px-4 py-2 hover:bg-white/5">View Brief</a>
                                        <a href="#" onclick="event.stopPropagation(); downloadBriefPDFDirectly('${h.id}')" class="block px-4 py-2 hover:bg-white/5">Download PDF</a>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
        
        // Manage unacknowledged incoming banner from previous shift
        // If the latest report is NOT acknowledged and generated by someone else (or even the same user, but we should show it if not acknowledged)
        if (handovers.length > 0) {
            const latest = handovers[0];
            if (!latest.acknowledged_by) {
                pendingIncomingBrief = latest;
                document.getElementById('incoming-handover-banner').classList.remove('hidden');
            } else {
                pendingIncomingBrief = null;
                document.getElementById('incoming-handover-banner').classList.add('hidden');
            }
        }
        
    } catch (err) {
        console.error('Load handover history error:', err);
    }
}

function updateHandoverKPIs(handovers) {
    const briefsWeekEl = document.getElementById('kpi-briefs-week');
    const unackEl = document.getElementById('kpi-unacknowledged');
    const criticalEl = document.getElementById('kpi-critical-flagged');
    const avgHealthEl = document.getElementById('kpi-avg-health');
    
    if (!briefsWeekEl) return;
    
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    // 1. Briefs this week
    const recentHandovers = handovers.filter(h => new Date(h.created_at) >= sevenDaysAgo);
    briefsWeekEl.textContent = recentHandovers.length;
    
    // 2. Unacknowledged count
    const unacknowledgedList = handovers.filter(h => !h.acknowledged_by);
    unackEl.textContent = unacknowledgedList.length;
    if (unacknowledgedList.length > 0) {
        unackEl.className = "text-3xl font-black font-mono text-[#EF4444]";
    } else {
        unackEl.className = "text-3xl font-black font-mono text-slate-400";
    }
    
    // 3. Critical items flagged (last 7 days)
    let criticalCount = 0;
    recentHandovers.forEach(h => {
        if (Array.isArray(h.critical_items)) {
            criticalCount += h.critical_items.length;
        }
    });
    criticalEl.textContent = criticalCount;
    if (criticalCount > 0) {
        criticalEl.className = "text-3xl font-black font-mono text-[#FACC15]";
    } else {
        criticalEl.className = "text-3xl font-black font-mono text-slate-400";
    }
    
    // 4. Avg shift health (rolling 7-shift average)
    const last7 = handovers.slice(0, 7);
    if (last7.length === 0) {
        avgHealthEl.textContent = 'N/A';
        avgHealthEl.className = "inline-block mt-1 px-3 py-1 rounded text-xs font-bold font-mono bg-white/5 border border-white/10 text-white";
    } else {
        const scoreMap = { 'GREEN': 3, 'AMBER': 2, 'RED': 1 };
        let sum = 0;
        last7.forEach(h => {
            sum += scoreMap[h.overall_status] || 2;
        });
        const avg = sum / last7.length;
        let finalStatus = 'AMBER';
        let badgeStyle = 'bg-[#FACC15]/10 text-[#FACC15] border-[#FACC15]/30';
        
        if (avg >= 2.5) {
            finalStatus = 'GREEN';
            badgeStyle = 'bg-[#22C55E]/10 text-[#22C55E] border-[#22C55E]/30';
        } else if (avg < 1.5) {
            finalStatus = 'RED';
            badgeStyle = 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/30';
        }
        
        avgHealthEl.textContent = finalStatus;
        avgHealthEl.className = `inline-block mt-1 px-3 py-1 rounded text-xs font-bold font-mono border ${badgeStyle}`;
    }
}

function toggleBriefDropdown(id) {
    const menu = document.getElementById(`brief-dropdown-${id}`);
    if (menu) {
        const isHidden = menu.classList.contains('hidden');
        document.querySelectorAll('[id^="brief-dropdown-"]').forEach(el => el.classList.add('hidden'));
        if (isHidden) menu.classList.remove('hidden');
    }
}

async function generateHandoverBrief() {
    const terminal = document.getElementById('handover-terminal');
    const btn = document.getElementById('generate-handover-btn');
    
    if (btn) btn.disabled = true;
    if (terminal) {
        terminal.classList.remove('hidden');
        // Hide previous briefs if open to focus on animation
        document.getElementById('handover-brief-container').classList.add('hidden');
    }
    
    // Animate terminal lines
    const lines = ['term-line-1', 'term-line-2', 'term-line-3', 'term-line-4', 'term-line-5', 'term-line-6', 'term-line-7', 'term-line-8'];
    for (let i = 0; i < lines.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 350));
        const line = document.getElementById(lines[i]);
        if (line) line.classList.remove('hidden');
    }
    
    try {
        let token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        
        // Create guest session if no token exists
        if (!token) {
            const guestId = 'guest_' + Math.random().toString(36).substr(2, 9);
            token = 'guest_token_' + guestId;
            sessionStorage.setItem('access_token', token);
            sessionStorage.setItem('guest_session', JSON.stringify({
                id: guestId,
                email: `${guestId}@local.guest`,
                name: 'Guest User',
                is_guest: true
            }));
            console.log('Created guest session for handover generation');
        }
        
        const response = await fetch(`${API_URL}/api/handover/generate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        if (response.status === 402) {
            // Paywall trigger
            showSettings('billing');
            alert('Sandbox limit reached: Maximum 1 shift handover brief allowed.');
            if (btn) btn.disabled = false;
            terminal.classList.add('hidden');
            return;
        }
        
        if (response.status === 401) {
            // Authentication failed
            alert('Authentication required. Please sign in to use this feature.');
            if (btn) btn.disabled = false;
            terminal.classList.add('hidden');
            window.location.href = 'signin.html';
            return;
        }
        
        const brief = await response.json();
        
        if (brief.id) {
            activeHandoverBrief = brief;
            
            // Set flagged count in terminal final line
            const criticalCount = Array.isArray(brief.critical_items) ? brief.critical_items.length : 0;
            document.getElementById('term-critical-count').textContent = criticalCount;
            
            displayHandoverReport(brief);
            loadHandoverHistory();
        } else {
            alert('Failed to generate handover report: ' + (brief.detail || brief.error || 'Unknown error'));
        }
    } catch (err) {
        console.error('Generate handover error:', err);
        alert('Failed to generate handover report: ' + err.message);
    }
    
    if (btn) btn.disabled = false;
}

function displayHandoverReport(brief) {
    const container = document.getElementById('handover-brief-container');
    if (!container) return;
    
    container.classList.remove('hidden');
    
    // Update headers
    document.getElementById('brief-facility').textContent = brief.facility_name;
    document.getElementById('brief-shift-type').textContent = brief.shift_type + ' SHIFT';
    document.getElementById('brief-date').textContent = new Date(brief.shift_start).toLocaleDateString();
    document.getElementById('brief-timestamp').textContent = new Date(brief.generated_at).toLocaleString();
    document.getElementById('brief-creator').textContent = brief.generated_by_name || 'Shift Lead';
    
    // Overall Status
    const statusEl = document.getElementById('brief-overall-status');
    statusEl.textContent = brief.overall_status;
    const statusColors = {
        'GREEN': 'bg-[#22C55E]/10 text-[#22C55E] border-[#22C55E]/30',
        'AMBER': 'bg-[#FACC15]/10 text-[#FACC15] border-[#FACC15]/30',
        'RED': 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/30'
    };
    statusEl.className = `inline-block px-3 py-1.5 rounded text-xs font-bold border ${statusColors[brief.overall_status] || 'bg-white/10'}`;
    
    // AI summary
    document.getElementById('brief-ai-summary').textContent = `"${brief.summary}"`;
    
    // Section 1 - Critical Items
    const criticalList = document.getElementById('sec-critical-list');
    const criticalCountEl = document.getElementById('sec-critical-count');
    const criticalItems = brief.critical_items || [];
    criticalCountEl.textContent = criticalItems.length;
    
    if (criticalItems.length === 0) {
        criticalList.innerHTML = `<div class="text-xs text-[#22C55E] font-bold font-mono">NO CRITICAL ITEMS THIS SHIFT</div>`;
    } else {
        criticalList.innerHTML = criticalItems.map(item => `
            <div class="p-3 bg-red-500/5 border border-red-500/10 rounded-lg flex flex-col gap-1">
                <div class="flex items-center gap-2">
                    <span class="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">● CRITICAL</span>
                    <span class="text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/5 text-slate-300 border border-white/10">${item.type}</span>
                    <span class="text-[9px] text-slate-400 font-mono ml-auto">Asset: ${item.asset}</span>
                </div>
                <p class="text-xs text-white">${item.description}</p>
                <p class="text-[10px] text-slate-400 mt-1"><strong class="text-[#F97316]">Recommended action:</strong> ${item.recommended_action}</p>
            </div>
        `).join('');
    }
    
    // Section 2 - Work Orders
    const wos = brief.work_orders_summary || [];
    document.getElementById('sec-workorders-title').textContent = `WORK ORDERS · ${wos.length} TOTAL`;
    
    const opened = wos.filter(w => w.status === 'OPEN');
    const progress = wos.filter(w => w.status === 'IN_PROGRESS');
    const completed = wos.filter(w => w.status === 'COMPLETE');
    
    const renderWOList = (list) => {
        if (list.length === 0) return `<div class="text-[10px] text-slate-500 italic">None</div>`;
        return list.map(w => {
            const priorityDot = w.priority === 'CRITICAL' ? 'bg-[#EF4444]' : (w.priority === 'HIGH' ? 'bg-[#F97316]' : (w.priority === 'MEDIUM' ? 'bg-[#FACC15]' : 'bg-[#64748B]'));
            const statusBadge = w.status === 'COMPLETE' ? 'bg-[#22C55E]/10 text-[#22C55E]' : (w.status === 'IN_PROGRESS' ? 'bg-blue-500/10 text-blue-400' : 'bg-white/5 text-slate-400');
            return `
                <div class="p-2.5 bg-black/35 hover:bg-black/50 border border-white/5 rounded-lg flex flex-col gap-1 cursor-pointer" onclick="navigateToWorkOrder('${w.id}')">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-1.5">
                            <span class="w-2 h-2 rounded-full ${priorityDot}"></span>
                            <span class="font-mono text-[9px] text-slate-500 hover:underline">${generateWOId(w.id)}</span>
                        </div>
                        <span class="text-[8px] uppercase tracking-wider font-bold px-1 py-0.5 rounded border border-white/5 ${statusBadge}">${w.status}</span>
                    </div>
                    <div class="text-[11px] font-bold text-white truncate">${w.title}</div>
                    <div class="text-[9px] text-slate-400 truncate">Asset: ${w.asset_name} · ${w.assigned_to || 'UNASSIGNED'}</div>
                </div>
            `;
        }).join('');
    };
    
    document.getElementById('wo-opened-list').innerHTML = renderWOList(opened);
    document.getElementById('wo-progress-list').innerHTML = renderWOList(progress);
    document.getElementById('wo-completed-list').innerHTML = renderWOList(completed);
    
    // Section 3 - Assets Accessed
    const accessed = brief.assets_accessed || [];
    document.getElementById('sec-assets-title').textContent = `ASSETS ACCESSED THIS SHIFT · ${accessed.length}`;
    
    const assetsTbody = document.getElementById('sec-assets-table-body');
    if (accessed.length === 0) {
        assetsTbody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-slate-500 italic">No assets accessed this shift.</td></tr>`;
    } else {
        assetsTbody.innerHTML = accessed.map(a => {
            const dot = a.has_open_wo ? `<span class="inline-block w-1.5 h-1.5 rounded-full bg-[#F97316] mr-1.5"></span>` : '';
            return `
                <tr class="hover:bg-white/5">
                    <td class="py-2.5 font-semibold text-white flex items-center">${dot}<a href="#" onclick="navigateToAsset('${a.name}')" class="hover:underline">${a.name}</a></td>
                    <td class="py-2.5 text-center text-slate-300 font-bold">${a.queries_asked}</td>
                    <td class="py-2.5 text-center text-slate-300 font-bold">${a.work_orders}</td>
                    <td class="py-2.5 text-right text-slate-400 font-mono">${new Date(a.last_activity).toLocaleTimeString()}</td>
                </tr>
            `;
        }).join('');
    }
    
    // Section 4 - Maintenance Status
    const maint = brief.maintenance_status || {};
    document.getElementById('maint-overdue-count').textContent = `${maint.overdue_count || 0} Items`;
    document.getElementById('maint-overdue-count').className = `text-xl font-black font-mono mt-1 ${(maint.overdue_count || 0) > 0 ? 'text-[#EF4444]' : 'text-slate-400'}`;
    
    document.getElementById('maint-due-count').textContent = `${maint.due_this_week_count || 0} Items`;
    document.getElementById('maint-due-count').className = `text-xl font-black font-mono mt-1 ${(maint.due_this_week_count || 0) > 0 ? 'text-[#FACC15]' : 'text-slate-400'}`;
    
    document.getElementById('maint-completed-count').textContent = `${maint.completed_count || 0} this shift`;
    
    const overdueListEl = document.getElementById('maint-overdue-list');
    const overdueList = maint.overdue_list || [];
    if (overdueList.length === 0) {
        overdueListEl.innerHTML = '';
    } else {
        overdueListEl.innerHTML = overdueList.map(item => `
            <div class="flex items-center justify-between text-xs p-3 bg-red-500/5 border border-red-500/10 rounded-lg">
                <span class="text-white font-medium">${item.asset_name} · <span class="text-slate-400">${item.task}</span></span>
                <div class="flex items-center gap-3">
                    <span class="text-red-400 font-bold font-mono">${item.days_overdue} days overdue</span>
                    <a href="#" onclick="openWOForOverdue('${item.asset_name}', '${item.task}')" class="text-[#F97316] font-bold hover:underline">CREATE WORK ORDER →</a>
                </div>
            </div>
        `).join('');
    }
    
    // Section 5 - Knowledge Queries
    const queries = brief.queries_summary || [];
    document.getElementById('sec-queries-title').textContent = `KNOWLEDGE QUERIES THIS SHIFT · ${queries.length}`;
    
    const queriesTbody = document.getElementById('sec-queries-table-body');
    let gapCount = 0;
    
    if (queries.length === 0) {
        queriesTbody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-slate-500 italic">No queries logged.</td></tr>`;
        document.getElementById('queries-gap-callout').classList.add('hidden');
    } else {
        queriesTbody.innerHTML = queries.map(q => {
            const isGap = !q.sources || q.sources.length === 0 || (q.answer && q.answer.toLowerCase().includes("does not contain"));
            if (isGap) gapCount++;
            
            const confidence = isGap ? 'LOW' : 'HIGH';
            const bgClass = isGap ? 'bg-yellow-500/5 text-yellow-400/90 border border-yellow-500/20' : '';
            
            const sourceName = q.sources && q.sources.length > 0 ? q.sources[0].manual_name : 'None';
            
            return `
                <tr class="hover:bg-white/5 ${bgClass}">
                    <td class="py-2.5 font-mono text-slate-400">${new Date(q.created_at).toLocaleTimeString()}</td>
                    <td class="py-2.5 font-semibold text-white">${q.query}</td>
                    <td class="py-2.5 text-slate-300">${sourceName}</td>
                    <td class="py-2.5 text-right font-bold font-mono">${confidence}</td>
                </tr>
            `;
        }).join('');
        
        if (gapCount > 0) {
            document.getElementById('queries-gap-callout').classList.remove('hidden');
            document.getElementById('gap-count').textContent = gapCount;
        } else {
            document.getElementById('queries-gap-callout').classList.add('hidden');
        }
    }
    
    // Section 6 - Incidents
    const incidentsList = document.getElementById('sec-incidents-list');
    const incidents = brief.incidents_summary || [];
    
    if (incidents.length === 0) {
        incidentsList.innerHTML = `<div class="text-xs text-[#22C55E] font-bold font-mono">NO INCIDENTS LOGGED</div>`;
    } else {
        incidentsList.innerHTML = incidents.map(inc => `
            <div class="p-3 bg-red-500/5 border border-red-500/20 rounded-lg">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 font-mono">${inc.severity}</span>
                    <span class="text-xs text-white font-bold">${inc.description}</span>
                </div>
                <div class="text-[10px] text-slate-400 font-mono">Asset: ${inc.asset} · Status: ${inc.status} · Logged by: ${inc.logged_by}</div>
                <div class="text-[10px] text-[#F97316] font-bold mt-1 uppercase tracking-wider">REQUIRES INCOMING SHIFT ATTENTION</div>
            </div>
        `).join('');
    }
    
    // Section 7 - Recommendations
    const recsList = document.getElementById('sec-recommendations-list');
    const recs = brief.ai_recommendations || [];
    
    recsList.innerHTML = recs.map(rec => `
        <li class="p-3 bg-[#F97316]/5 border border-[#F97316]/20 rounded-lg"><strong class="text-[#F97316] font-mono block mb-1">PRIORITY</strong> ${rec}</li>
    `).join('');
    
    // Acknowledgment signature area state
    const isAcked = !!brief.acknowledged_by;
    if (isAcked) {
        document.getElementById('signature-input-area').classList.add('hidden');
        document.getElementById('signature-confirmed-area').classList.remove('hidden');
        document.getElementById('ack-signed-name').textContent = brief.acknowledged_by.toUpperCase();
        document.getElementById('ack-signed-time').textContent = new Date(brief.acknowledged_at).toLocaleString();
    } else {
        document.getElementById('signature-input-area').classList.remove('hidden');
        document.getElementById('signature-confirmed-area').classList.add('hidden');
        document.getElementById('incoming-lead-name').value = '';
    }
}

async function submitAcknowledge() {
    if (!activeHandoverBrief) return;
    
    const nameInput = document.getElementById('incoming-lead-name');
    const name = nameInput.value.trim();
    
    if (!name) {
        alert('Please type your name to sign and acknowledge the brief.');
        return;
    }
    
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/handover/${activeHandoverBrief.id}/acknowledge`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: name })
        });
        
        if (response.ok) {
            const updated = await response.json();
            activeHandoverBrief = updated;
            displayHandoverReport(updated);
            loadHandoverHistory();
            showToast('Handover brief signed and acknowledged', 'brand');
        } else {
            alert('Failed to sign and acknowledge handover brief.');
        }
    } catch (err) {
        console.error('Acknowledge handover error:', err);
    }
}

function copyShareBriefLink() {
    if (!activeHandoverBrief) return;
    
    const shareUrl = `${window.location.origin}/handover/${activeHandoverBrief.share_token}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
        showToast('Share link copied to clipboard', 'brand');
    }).catch(err => {
        console.error('Could not copy link:', err);
    });
}

function downloadBriefPDF() {
    if (!activeHandoverBrief) return;
    
    // Copy the print content to the hidden print container
    const briefContent = document.getElementById('handover-brief-container').innerHTML;
    const printContainer = document.getElementById('print-container');
    
    if (printContainer) {
        // Strip out the non-print action buttons/inputs
        printContainer.innerHTML = briefContent;
        // Hide signatures/actions in print view
        const actions = printContainer.querySelector('.flex.flex-wrap.items-center.gap-3');
        if (actions) actions.style.display = 'none';
        const signature = printContainer.querySelector('#signature-input-area');
        if (signature) signature.style.display = 'none';
        
        window.print();
    }
}

function readIncomingHandover() {
    if (pendingIncomingBrief) {
        activeHandoverBrief = pendingIncomingBrief;
        displayHandoverReport(pendingIncomingBrief);
        document.getElementById('handover-brief-container').scrollIntoView({ behavior: 'smooth' });
    }
}

function scrollToAcknowledge() {
    document.getElementById('signature-input-area')?.scrollIntoView({ behavior: 'smooth' });
}

// History drawer controls
async function openHandoverHistoryDrawer(id) {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const historyResponse = await fetch(`${API_URL}/api/handover/history`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const handovers = await historyResponse.json();
        const brief = handovers.find(h => h.id === id);
        
        if (!brief) return;
        
        const drawer = document.getElementById('handover-drawer');
        const backdrop = document.getElementById('drawer-backdrop');
        const content = document.getElementById('drawer-content-area');
        
        if (drawer && backdrop && content) {
            drawer.classList.remove('hidden');
            backdrop.classList.remove('hidden');
            setTimeout(() => drawer.classList.remove('translate-x-full'), 10);
            
            // Build historical report content in drawer
            const statusColors = {
                'GREEN': 'bg-[#22C55E]/10 text-[#22C55E] border-[#22C55E]/30',
                'AMBER': 'bg-[#FACC15]/10 text-[#FACC15] border-[#FACC15]/30',
                'RED': 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/30'
            };
            const criticalItems = brief.critical_items || [];
            const wos = brief.work_orders_summary || [];
            const accessed = brief.assets_accessed || [];
            const maint = brief.maintenance_status || {};
            const queries = brief.queries_summary || [];
            const incidents = brief.incidents_summary || [];
            const recs = brief.ai_recommendations || [];
            
            const opened = wos.filter(w => w.status === 'OPEN');
            const progress = wos.filter(w => w.status === 'IN_PROGRESS');
            const completed = wos.filter(w => w.status === 'COMPLETE');
            
            content.innerHTML = `
                <div class="space-y-6 text-xs text-slate-300">
                    <div class="border-b border-white/10 pb-4">
                        <div class="text-[10px] text-[#F97316] font-mono tracking-widest font-bold">HISTORICAL SHIFT REPORT</div>
                        <h4 class="text-base font-black text-white font-mono mt-1">${brief.facility_name} · ${brief.shift_type} SHIFT</h4>
                        <div class="text-[10px] text-slate-500 font-mono mt-1">
                            Shift: ${new Date(brief.shift_start).toLocaleString()} to ${new Date(brief.shift_end).toLocaleTimeString()}<br>
                            Generated by ${brief.generated_by_name || 'Shift Lead'} at ${new Date(brief.generated_at).toLocaleString()}
                        </div>
                    </div>
                    
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-500 font-mono block mb-1">Overall Status</span>
                        <span class="inline-block px-3 py-1 rounded text-xs font-bold border ${statusColors[brief.overall_status] || 'bg-white/10'}">${brief.overall_status}</span>
                    </div>

                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-500 font-mono block mb-1">Summary</span>
                        <p class="italic text-white">"${brief.summary}"</p>
                    </div>

                    <!-- Critical items -->
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-500 font-mono block mb-2">Critical Items (${criticalItems.length})</span>
                        <div class="space-y-2">
                            ${criticalItems.length === 0 ? '<div class="text-slate-500 font-mono">None</div>' : criticalItems.map(item => `
                                <div class="p-3 bg-red-500/5 border border-red-500/10 rounded-lg">
                                    <div class="flex items-center gap-2 mb-1">
                                        <span class="font-bold text-red-400 font-mono text-[9px] uppercase">● CRITICAL</span>
                                        <span class="font-bold text-slate-300 font-mono text-[9px] uppercase bg-white/5 border border-white/10 px-1 rounded">${item.type}</span>
                                        <span class="text-[9px] text-slate-500 font-mono ml-auto">Asset: ${item.asset}</span>
                                    </div>
                                    <p class="text-white">${item.description}</p>
                                    <p class="text-[10px] text-slate-400 mt-1"><strong class="text-[#F97316]">Action:</strong> ${item.recommended_action}</p>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <!-- Work Orders -->
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-500 font-mono block mb-2">Work Orders (${wos.length})</span>
                        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <div class="space-y-1.5">
                                <div class="text-[9px] font-bold text-slate-500 uppercase">Opened (${opened.length})</div>
                                ${opened.map(w => `<div class="p-2 bg-black/40 border border-white/5 rounded truncate font-mono text-[10px]">${generateWOId(w.id)} · ${w.title}</div>`).join('') || '<div class="text-[9px] text-slate-600">None</div>'}
                            </div>
                            <div class="space-y-1.5">
                                <div class="text-[9px] font-bold text-slate-500 uppercase">In Progress (${progress.length})</div>
                                ${progress.map(w => `<div class="p-2 bg-black/40 border border-white/5 rounded truncate font-mono text-[10px]">${generateWOId(w.id)} · ${w.title}</div>`).join('') || '<div class="text-[9px] text-slate-600">None</div>'}
                            </div>
                            <div class="space-y-1.5">
                                <div class="text-[9px] font-bold text-slate-500 uppercase">Completed (${completed.length})</div>
                                ${completed.map(w => `<div class="p-2 bg-black/40 border border-white/5 rounded truncate font-mono text-[10px] border-l-2 border-l-[#22C55E]">${generateWOId(w.id)} · ${w.title}</div>`).join('') || '<div class="text-[9px] text-slate-600">None</div>'}
                            </div>
                        </div>
                    </div>

                    <!-- Assets Accessed -->
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-500 font-mono block mb-2">Assets Accessed (${accessed.length})</span>
                        <table class="w-full text-left border-collapse text-[10px]">
                            <thead>
                                <tr class="border-b border-white/10 text-slate-500">
                                    <th class="pb-1.5">Asset</th>
                                    <th class="pb-1.5 text-center">Queries</th>
                                    <th class="pb-1.5 text-center">WOs</th>
                                    <th class="pb-1.5 text-right">Last Activity</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${accessed.length === 0 ? '<tr><td colspan="4" class="py-2 text-slate-600 italic">None</td></tr>' : accessed.map(a => `
                                    <tr class="border-b border-white/5">
                                        <td class="py-1.5 text-white font-bold">${a.name}</td>
                                        <td class="py-1.5 text-center">${a.queries_asked}</td>
                                        <td class="py-1.5 text-center">${a.work_orders}</td>
                                        <td class="py-1.5 text-right text-slate-400 font-mono">${new Date(a.last_activity).toLocaleTimeString()}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>

                    <!-- Maintenance status -->
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-500 font-mono block mb-2">Maintenance Status</span>
                        <div class="grid grid-cols-3 gap-3 mb-3 text-center">
                            <div class="p-2 bg-black/40 border border-white/5 rounded">
                                <div class="text-[8px] uppercase text-slate-500 font-bold">Overdue</div>
                                <div class="text-sm font-black font-mono mt-0.5">${maint.overdue_count || 0}</div>
                            </div>
                            <div class="p-2 bg-black/40 border border-white/5 rounded">
                                <div class="text-[8px] uppercase text-slate-500 font-bold">Due Week</div>
                                <div class="text-sm font-black font-mono mt-0.5">${maint.due_this_week_count || 0}</div>
                            </div>
                            <div class="p-2 bg-black/40 border border-white/5 rounded">
                                <div class="text-[8px] uppercase text-slate-500 font-bold">Completed</div>
                                <div class="text-sm font-black font-mono text-[#22C55E] mt-0.5">${maint.completed_count || 0}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Incidents -->
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-500 font-mono block mb-2">Incidents</span>
                        <div class="space-y-1.5">
                            ${incidents.length === 0 ? '<div class="text-slate-500 font-mono">None</div>' : incidents.map(inc => `
                                <div class="p-2 bg-black/40 border border-white/5 rounded text-[10px]">
                                    <span class="font-bold text-red-400 font-mono uppercase bg-red-500/10 px-1 rounded mr-1.5">${inc.severity}</span>
                                    <strong class="text-white">${inc.description}</strong>
                                    <div class="text-slate-500 mt-1 font-mono text-[9px]">Asset: ${inc.asset} · Status: ${inc.status}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <!-- Recommendations -->
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-500 font-mono block mb-2">Recommended Priorities</span>
                        <ol class="space-y-2">
                            ${recs.map(rec => `<li class="p-2.5 bg-[#F97316]/5 border border-[#F97316]/20 rounded-lg">${rec}</li>`).join('')}
                        </ol>
                    </div>

                    <!-- Acknowledged State -->
                    <div class="pt-4 border-t border-white/10">
                        ${brief.acknowledged_by ? `
                            <div class="text-[#22C55E] font-bold font-mono text-center">
                                ✓ ACKNOWLEDGED BY ${brief.acknowledged_by.toUpperCase()} AT ${new Date(brief.acknowledged_at).toLocaleString()}
                            </div>
                        ` : `
                            <div class="text-[#F97316] font-bold font-mono text-center">
                                PENDING ACKNOWLEDGEMENT BY INCOMING LEAD
                            </div>
                        `}
                    </div>
                </div>
            `;
        }
    } catch (err) {
        console.error('Open history drawer error:', err);
    }
}

function closeHandoverDrawer() {
    const drawer = document.getElementById('handover-drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    if (drawer && backdrop) {
        drawer.classList.add('translate-x-full');
        setTimeout(() => {
            drawer.classList.add('hidden');
            backdrop.classList.add('hidden');
        }, 300);
    }
}

function printDrawerBrief() {
    const printContainer = document.getElementById('print-container');
    const content = document.getElementById('drawer-content-area');
    if (printContainer && content) {
        printContainer.innerHTML = content.innerHTML;
        window.print();
    }
}

function downloadBriefPDFDirectly(id) {
    openHandoverHistoryDrawer(id);
    setTimeout(() => {
        printDrawerBrief();
        closeHandoverDrawer();
    }, 500);
}

// Navigation helpers
function navigateToWorkOrder(woId) {
    showView('workorders');
    setTimeout(() => {
        if (typeof openWorkOrderDetail === 'function') {
            openWorkOrderDetail(woId);
        }
    }, 300);
}

function navigateToAsset(assetName) {
    showView('assets');
    // Set asset search filter if applicable
    setTimeout(() => {
        const searchInput = document.getElementById('asset-search-input');
        if (searchInput) {
            searchInput.value = assetName;
            searchInput.dispatchEvent(new Event('input'));
        }
    }, 300);
}

function openWOForOverdue(assetName, task) {
    showView('workorders');
    setTimeout(() => {
        if (typeof openCreateWorkOrderModal === 'function') {
            openCreateWorkOrderModal();
            // Pre-select asset if dropdown loaded
            setTimeout(() => {
                const select = document.getElementById('new-wo-asset');
                if (select) {
                    for (let i = 0; i < select.options.length; i++) {
                        if (select.options[i].text === assetName) {
                            select.selectedIndex = i;
                            break;
                        }
                    }
                }
                const title = document.getElementById('new-wo-title');
                if (title) title.value = `${task} - ${assetName}`;
            }, 300);
        }
    }, 300);
}

// Close dropdowns
document.addEventListener('click', (e) => {
    if (!e.target.closest('.relative')) {
        document.querySelectorAll('[id^="brief-dropdown-"]').forEach(d => d.classList.add('hidden'));
    }
});

// Attach shift handover functions to window
window.generateHandoverBrief = generateHandoverBrief;
window.submitAcknowledge = submitAcknowledge;
window.copyShareBriefLink = copyShareBriefLink;
window.downloadBriefPDF = downloadBriefPDF;
window.readIncomingHandover = readIncomingHandover;
window.scrollToAcknowledge = scrollToAcknowledge;
window.openHandoverHistoryDrawer = openHandoverHistoryDrawer;
window.closeHandoverDrawer = closeHandoverDrawer;
window.printDrawerBrief = printDrawerBrief;
window.toggleBriefDropdown = toggleBriefDropdown;
window.downloadBriefPDFDirectly = downloadBriefPDFDirectly;
window.navigateToWorkOrder = navigateToWorkOrder;
window.navigateToAsset = navigateToAsset;
window.openWOForOverdue = openWOForOverdue;
window.loadHandoverPageData = loadHandoverPageData;

// Initialize on script load
loadHandoverPageData();

// ============================================================================
// FEATURE 6: Facility Health Score
// ============================================================================

async function loadFacilityHealth() {
    try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/api/facility/health`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const health = await response.json();
        
        // Update top nav
        const navValue = document.getElementById('nav-health-value');
        if (navValue) {
            navValue.textContent = health.score;
            navValue.className = `text-sm font-bold ${getHealthColor(health.status)}`;
        }
        
        // Update dashboard widget
        const widgetValue = document.getElementById('health-score-value');
        if (widgetValue) {
            widgetValue.textContent = health.score;
            widgetValue.className = `text-2xl font-bold ${getHealthColor(health.status)}`;
        }
        
        const statusBadge = document.getElementById('health-status-badge');
        if (statusBadge) {
            statusBadge.textContent = health.status;
            statusBadge.className = `text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${getStatusColor(health.status)}`;
        }
        
        // Update breakdown bars
        const breakdown = health.breakdown;
        if (breakdown) {
            updateHealthBar('documents', breakdown.documents);
            updateHealthBar('maintenance', breakdown.maintenance);
            updateHealthBar('workorders', breakdown.work_orders);
        }
    } catch (err) {
        console.error('Load facility health error:', err);
    }
}

function updateHealthBar(type, data) {
    const bar = document.getElementById(`health-${type}-bar`);
    const score = document.getElementById(`health-${type}-score`);
    
    if (bar && score) {
        const percentage = (data.score / data.max) * 100;
        bar.style.width = `${percentage}%`;
        score.textContent = `${data.score}/${data.max}`;
    }
}

function getHealthColor(status) {
    switch (status) {
        case 'GREEN': return 'text-[#22C55E]';
        case 'AMBER': return 'text-[#FACC15]';
        case 'RED': return 'text-[#EF4444]';
        default: return 'text-slate-400';
    }
}

// ============================================================================
// Initialization
// ============================================================================

// Load facility health on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        loadFacilityHealth();
        loadWorkOrders();
    });
} else {
    loadFacilityHealth();
    loadWorkOrders();
}

// Refresh facility health every 5 minutes
setInterval(loadFacilityHealth, 300000);

// Attach work order functions to window for global access
window.openCreateWorkOrderModal = openCreateWorkOrderModal;
window.closeCreateWorkOrderModal = closeCreateWorkOrderModal;
window.setNewWOPriority = setNewWOPriority;
window.addProcedureStep = addProcedureStep;
window.createNewWorkOrder = createNewWorkOrder;
window.createNewWorkOrderWithAI = createNewWorkOrderWithAI;
window.openGenerateAIModal = openGenerateAIModal;
window.closeGenerateAIModal = closeGenerateAIModal;
window.filterWorkOrders = filterWorkOrders;
window.filterByAsset = filterByAsset;
window.filterByStatus = filterByStatus;
window.filterBySearch = filterBySearch;
window.toggleWODropdown = toggleWODropdown;
window.openWorkOrderDetail = openWorkOrderDetail;
window.closeDetailDrawer = closeDetailDrawer;
window.updateWorkOrderStatus = updateWorkOrderStatus;
window.escalateWorkOrder = escalateWorkOrder;
window.assignWorkOrder = assignWorkOrder;
window.showInlineAssignModal = showInlineAssignModal;
window.markWorkOrderComplete = markWorkOrderComplete;
window.cancelWorkOrder = cancelWorkOrder;
window.addNote = addNote;
window.generateAIBriefing = generateAIBriefing;
window.generateProcedureSteps = generateProcedureSteps;
window.generateAIBriefingForWO = generateAIBriefingForWO;
window.linkToLOTO = function() {
    alert('LOTO integration coming soon');
};
window.createSuggestedWO = createSuggestedWO;
window.createAllSuggestions = createAllSuggestions;

// Handle manuals upload
window.handleManualsUpload = async function(input) {
    const files = Array.from(input.files);
    if (files.length === 0) return;

    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('asset_type', 'Industrial Equipment');

    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            alert(`Manual uploaded successfully: ${file.name}\n${result.message}`);
            // Refresh manuals list
            if (window.loadManuals) {
                window.loadManuals();
            }
        } else {
            alert('Upload failed: ' + result.message);
        }
    } catch (error) {
        alert('Upload failed: ' + error.message);
    }

    input.value = '';
};
