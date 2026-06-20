from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from typing import Optional
from supabase import create_client
from ..config import settings
import os

router = APIRouter()
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Return guest user when no valid credentials are provided."""
    from jose import jwt, JWTError
    import uuid

    if not credentials:
        guest_id = f"guest_{uuid.uuid4().hex[:8]}"
        return {"user_id": guest_id, "token": f"guest_token_{guest_id}", "is_guest": True}

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return {"user_id": user_id, "token": token}
    except JWTError:
        guest_id = f"guest_{uuid.uuid4().hex[:8]}"
        return {"user_id": guest_id, "token": f"guest_token_{guest_id}", "is_guest": True}

@router.get("/handover", response_class=HTMLResponse)
async def serve_handover_view(current_user: dict = Depends(get_current_user)):
    """Serve the shift handover dashboard view."""
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(PROJECT_ROOT, "dashboard-pages", "handover-view.html"))

@router.get("/handover/{share_token}", response_class=HTMLResponse)
async def serve_handover_share(share_token: str):
    """Serve the public read-only shift handover brief."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        # Support looking up by both share_token or primary ID
        response = supabase.table('shift_handovers').select('*').eq('share_token', share_token).execute()
        if not response.data:
            response = supabase.table('shift_handovers').select('*').eq('id', share_token).execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail="Handover report not found")
        
        brief = response.data[0]

        
        # Format dates
        generated_at = brief.get("generated_at", "")
        if generated_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                generated_at = dt.strftime("%b %d, %Y at %H:%M:%S")
            except:
                pass
                
        shift_start = brief.get("shift_start", "")
        if shift_start:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(shift_start.replace('Z', '+00:00'))
                shift_start = dt.strftime("%b %d, %Y %H:%M")
            except:
                pass
                
        shift_end = brief.get("shift_end", "")
        if shift_end:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(shift_end.replace('Z', '+00:00'))
                shift_end = dt.strftime("%H:%M")
            except:
                pass
                
        # Status Badge Styles
        status_colors = {
            "GREEN": "bg-[#22C55E]/10 text-[#22C55E] border-[#22C55E]/30",
            "AMBER": "bg-[#FACC15]/10 text-[#FACC15] border-[#FACC15]/30",
            "RED": "bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/30"
        }
        status_color = status_colors.get(brief.get("overall_status", "AMBER"), "bg-white/10 text-white")
        
        # Build HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>IndexField | Shift Handover Brief</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                body {{
                    background-color: #111827;
                    color: #F8FAFC;
                    font-family: 'Inter', sans-serif;
                }}
                @media print {{
                    body {{
                        background-color: #ffffff !important;
                        color: #000000 !important;
                    }}
                    .no-print {{
                        display: none !important;
                    }}
                    .print-card {{
                        background: #ffffff !important;
                        border: 1px solid #000000 !important;
                        color: #000000 !important;
                    }}
                }}
            </style>
        </head>
        <body class="p-6 max-w-4xl mx-auto">
            <div class="flex items-center justify-between border-b border-white/10 pb-6 mb-6 no-print">
                <div class="flex items-center gap-3">
                    <span class="font-bold tracking-widest text-sm text-[#F97316]">INDEX FIELD</span>
                    <span class="text-xs text-slate-400">|</span>
                    <span class="text-xs text-slate-400 font-mono">OPERATIONAL INTELLIGENCE BRIEF</span>
                </div>
                <button onclick="window.print()" class="px-4 py-2 bg-[#F97316] text-black font-bold rounded hover:bg-[#EA580C] transition text-sm">
                    <i class="fas fa-print mr-2"></i>PRINT / SAVE PDF
                </button>
            </div>
            
            <div class="print-card bg-[#1F2937]/90 border border-white/5 rounded-xl p-8 shadow-2xl">
                <!-- Brief Header -->
                <div class="border-b border-white/10 pb-6 mb-6">
                    <h1 class="text-2xl font-black tracking-wider text-white mb-2">SHIFT HANDOVER BRIEF</h1>
                    <div class="grid grid-cols-2 gap-4 text-sm text-slate-400">
                        <div>
                            <p>Facility: <strong class="text-white">{brief.get("facility_name")}</strong></p>
                            <p>Shift: <strong class="text-white">{brief.get("shift_type")} SHIFT ({shift_start} to {shift_end})</strong></p>
                        </div>
                        <div class="text-right">
                            <p>Generated: <strong class="text-white">{generated_at}</strong></p>
                            <p>Lead: <strong class="text-white">{brief.get("generated_by_name", "Shift Lead")}</strong></p>
                        </div>
                    </div>
                </div>
                
                <!-- Status & Summary -->
                <div class="mb-8 p-4 bg-black/40 border border-white/5 rounded-lg flex items-start gap-4">
                    <div class="flex flex-col items-center">
                        <span class="text-[9px] uppercase tracking-widest text-slate-500 font-mono font-bold mb-1">Status</span>
                        <span class="px-3 py-1.5 rounded text-xs font-bold border {status_color}">{brief.get("overall_status")}</span>
                    </div>
                    <div class="flex-1">
                        <span class="text-[9px] uppercase tracking-widest text-slate-500 font-mono font-bold block mb-1">AI Summary</span>
                        <p class="text-sm italic text-slate-300">"{brief.get("summary")}"</p>
                    </div>
                </div>
                
                <!-- Section 1: Critical Items -->
                <div class="mb-8">
                    <h2 class="text-xs font-bold uppercase tracking-wider text-[#EF4444] mb-3 flex items-center gap-2">
                        <span class="w-1.5 h-1.5 rounded-full bg-[#EF4444]"></span> Critical Items Requiring Attention
                    </h2>
                    <div class="space-y-3">
                        """
        
        critical_items = brief.get("critical_items", [])
        if not critical_items:
            html_content += f"""
            <div class="text-sm text-[#22C55E] font-bold font-mono">NO CRITICAL ITEMS THIS SHIFT</div>
            """
        else:
            for item in critical_items:
                html_content += f"""
                <div class="p-3 bg-red-500/5 border border-red-500/20 rounded-lg">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">● CRITICAL</span>
                        <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-white/5 text-slate-300 border border-white/10">{item.get('type')}</span>
                        <span class="text-[10px] text-slate-400 font-mono ml-auto">Asset: {item.get('asset')}</span>
                    </div>
                    <p class="text-xs text-white font-medium">{item.get('description')}</p>
                    <p class="text-[11px] text-slate-300 mt-1 font-mono"><strong class="text-[#F97316]">Action:</strong> {item.get('recommended_action')}</p>
                </div>
                """
                
        # Section 2: Work Orders
        html_content += f"""
                </div>
                
                <!-- Section 2: Work Orders -->
                <div class="mb-8">
                    <h2 class="text-xs font-bold uppercase tracking-wider text-white mb-3">Work Orders This Shift</h2>
        """
        
        wos = brief.get("work_orders_summary", [])
        if not wos:
            html_content += f"""
            <div class="text-xs text-slate-500 font-mono">NO WORK ORDERS THIS SHIFT</div>
            """
        else:
            opened = [w for w in wos if w.get('status') == 'OPEN']
            in_progress = [w for w in wos if w.get('status') == 'IN_PROGRESS']
            completed = [w for w in wos if w.get('status') == 'COMPLETE']
            
            html_content += f"""
            <div class="grid grid-cols-3 gap-4">
                <div>
                    <div class="text-[10px] uppercase font-bold text-slate-500 mb-2">Opened ({len(opened)})</div>
                    <div class="space-y-2">
            """
            for w in opened:
                html_content += f"""
                <div class="p-2 bg-black/20 border border-white/5 rounded text-xs">
                    <div class="font-mono text-[10px] text-slate-500">{w.get('id')}</div>
                    <div class="font-semibold text-white truncate">{w.get('title')}</div>
                    <div class="text-[9px] text-slate-400">{w.get('asset_name')}</div>
                </div>
                """
            html_content += f"""
                    </div>
                </div>
                <div>
                    <div class="text-[10px] uppercase font-bold text-slate-500 mb-2">In Progress ({len(in_progress)})</div>
                    <div class="space-y-2">
            """
            for w in in_progress:
                html_content += f"""
                <div class="p-2 bg-black/20 border border-white/5 rounded text-xs">
                    <div class="font-mono text-[10px] text-slate-500">{w.get('id')}</div>
                    <div class="font-semibold text-white truncate">{w.get('title')}</div>
                    <div class="text-[9px] text-slate-400">{w.get('asset_name')}</div>
                </div>
                """
            html_content += f"""
                    </div>
                </div>
                <div>
                    <div class="text-[10px] uppercase font-bold text-slate-500 mb-2">Completed ({len(completed)})</div>
                    <div class="space-y-2">
            """
            for w in completed:
                html_content += f"""
                <div class="p-2 bg-black/20 border border-white/5 rounded text-xs border-l-2 border-l-[#22C55E]">
                    <div class="font-mono text-[10px] text-slate-500">{w.get('id')}</div>
                    <div class="font-semibold text-white truncate">{w.get('title')}</div>
                    <div class="text-[9px] text-slate-400">{w.get('asset_name')}</div>
                </div>
                """
            html_content += f"""
                    </div>
                </div>
            </div>
            """
            
        # Section 3: Assets Accessed
        html_content += f"""
                </div>
                
                <!-- Section 3: Assets Accessed -->
                <div class="mb-8">
                    <h2 class="text-xs font-bold uppercase tracking-wider text-white mb-3">Assets Accessed This Shift</h2>
                    <table class="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr class="border-b border-white/10 text-slate-400">
                                <th class="pb-2">Asset Name</th>
                                <th class="pb-2 text-center">Queries Asked</th>
                                <th class="pb-2 text-center">Work Orders</th>
                                <th class="pb-2 text-right">Last Activity</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        assets_acc = brief.get("assets_accessed", [])
        if not assets_acc:
            html_content += f"""
            <tr><td colspan="4" class="py-4 text-slate-500 font-mono text-center">NO ASSETS ACCESSED THIS SHIFT</td></tr>
            """
        else:
            for ass in assets_acc:
                dot = '<span class="inline-block w-1.5 h-1.5 rounded-full bg-[#F97316] mr-1.5"></span>' if ass.get('has_open_wo') else ''
                # format last activity date
                act_str = ass.get('last_activity', '')
                if act_str:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(act_str.replace('Z', '+00:00'))
                        act_str = dt.strftime("%b %d, %H:%M")
                    except:
                        pass
                html_content += f"""
                <tr class="border-b border-white/5 hover:bg-white/5">
                    <td class="py-2.5 font-medium flex items-center">{dot}{ass.get('name')}</td>
                    <td class="py-2.5 text-center">{ass.get('queries_asked')}</td>
                    <td class="py-2.5 text-center">{ass.get('work_orders')}</td>
                    <td class="py-2.5 text-right text-slate-400 font-mono">{act_str}</td>
                </tr>
                """
                
        # Section 4: Maintenance Status
        maint = brief.get("maintenance_status", {})
        overdue_list = maint.get("overdue_list", [])
        html_content += f"""
                        </tbody>
                    </table>
                </div>
                
                <!-- Section 4: Maintenance Status -->
                <div class="mb-8">
                    <h2 class="text-xs font-bold uppercase tracking-wider text-white mb-3">Maintenance Status</h2>
                    <div class="grid grid-cols-3 gap-4 mb-4 text-center">
                        <div class="p-3 bg-black/20 border border-white/5 rounded">
                            <div class="text-[9px] uppercase text-slate-500 font-bold">Overdue Now</div>
                            <div class="text-lg font-black font-mono mt-1 {'text-[#EF4444]' if maint.get('overdue_count', 0) > 0 else 'text-slate-400'}">{maint.get('overdue_count', 0)} Items</div>
                        </div>
                        <div class="p-3 bg-black/20 border border-white/5 rounded">
                            <div class="text-[9px] uppercase text-slate-500 font-bold">Due This Week</div>
                            <div class="text-lg font-black font-mono mt-1 {'text-[#FACC15]' if maint.get('due_this_week_count', 0) > 0 else 'text-slate-400'}">{maint.get('due_this_week_count', 0)} Items</div>
                        </div>
                        <div class="p-3 bg-black/20 border border-white/5 rounded">
                            <div class="text-[9px] uppercase text-slate-500 font-bold">Completed</div>
                            <div class="text-lg font-black font-mono mt-1 text-[#22C55E]">{maint.get('completed_count', 0)} this shift</div>
                        </div>
                    </div>
        """
        if overdue_list:
            html_content += f"""
            <div class="space-y-1">
            """
            for it in overdue_list:
                html_content += f"""
                <div class="flex items-center justify-between text-xs p-2 bg-red-500/5 border border-red-500/10 rounded">
                    <span>{it.get('asset_name')} · {it.get('task')}</span>
                    <span class="text-red-400 font-bold">{it.get('days_overdue')} days overdue</span>
                </div>
                """
            html_content += f"""
            </div>
            """
            
        # Section 5: Queries Asked
        html_content += f"""
                </div>
                
                <!-- Section 5: Queries Asked -->
                <div class="mb-8">
                    <h2 class="text-xs font-bold uppercase tracking-wider text-white mb-3">Knowledge Queries Asked This Shift</h2>
                    <table class="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr class="border-b border-white/10 text-slate-400">
                                <th class="pb-2">Time</th>
                                <th class="pb-2">Question Asked</th>
                                <th class="pb-2">Source Found</th>
                                <th class="pb-2 text-right">Confidence</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        queries = brief.get("queries_summary", [])
        gap_count = 0
        if not queries:
            html_content += f"""
            <tr><td colspan="4" class="py-4 text-slate-500 font-mono text-center">NO KNOWLEDGE QUERIES LOGGED</td></tr>
            """
        else:
            for q in queries:
                q_time_str = q.get('created_at', '')
                if q_time_str:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(q_time_str.replace('Z', '+00:00'))
                        q_time_str = dt.strftime("%H:%M")
                    except:
                        pass
                
                # Check confidence/documentation gap
                sources = q.get('sources', [])
                source_found = sources[0].get('manual_name', 'OEM Manual') if sources else ''
                
                is_gap = not source_found or "does not contain" in q.get('answer', '').lower()
                confidence = "LOW" if is_gap else "HIGH"
                bg_style = 'bg-yellow-500/5 text-yellow-400/90 border border-yellow-500/20' if is_gap else ''
                
                if is_gap:
                    gap_count += 1
                
                html_content += f"""
                <tr class="border-b border-white/5 hover:bg-white/5 {bg_style}">
                    <td class="py-2.5 font-mono text-slate-400">{q_time_str}</td>
                    <td class="py-2.5 font-medium">{q.get('query')}</td>
                    <td class="py-2.5 text-slate-300">{source_found or 'None'}</td>
                    <td class="py-2.5 text-right font-bold font-mono">{confidence}</td>
                </tr>
                """
        html_content += f"""
                        </tbody>
                    </table>
        """
        if gap_count > 0:
            html_content += f"""
            <div class="mt-3 p-3 bg-yellow-500/5 border border-yellow-500/20 rounded-lg flex items-center gap-3">
                <i class="fas fa-exclamation-triangle text-[#FACC15]"></i>
                <div class="text-xs">
                    <p class="font-bold text-[#FACC15]">{gap_count} QUERIES HAD NO GOOD ANSWER</p>
                    <p class="text-slate-400">These topics have no uploaded documentation.</p>
                </div>
            </div>
            """
            
        # Section 6: Incidents
        html_content += f"""
                </div>
                
                <!-- Section 6: Incidents -->
                <div class="mb-8">
                    <h2 class="text-xs font-bold uppercase tracking-wider text-white mb-3">Incidents This Shift</h2>
        """
        
        incidents = brief.get("incidents_summary", [])
        if not incidents:
            html_content += f"""
            <div class="text-sm text-[#22C55E] font-bold font-mono">NO INCIDENTS LOGGED</div>
            """
        else:
            for inc in incidents:
                html_content += f"""
                <div class="p-3 bg-red-500/5 border border-red-500/20 rounded-lg mb-2">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 font-mono">{inc.get('severity')}</span>
                        <span class="text-xs text-white font-bold">{inc.get('description')}</span>
                    </div>
                    <div class="text-[10px] text-slate-400 font-mono">Asset: {inc.get('asset')} · Status: {inc.get('status')} · Logged by: {inc.get('logged_by')}</div>
                    <div class="text-[10px] text-[#F97316] font-bold mt-1 uppercase tracking-wider">REQUIRES INCOMING SHIFT ATTENTION</div>
                </div>
                """
                
        # Section 7: Recommendations
        html_content += f"""
                </div>
                
                <!-- Section 7: AI Recommendations -->
                <div class="mb-8">
                    <h2 class="text-xs font-bold uppercase tracking-wider text-white mb-3">Recommended Priorities for Incoming Shift</h2>
                    <ol class="space-y-3 text-xs leading-relaxed text-slate-300">
        """
        
        recs = brief.get("ai_recommendations", [])
        for rec in recs:
            html_content += f"""
            <li class="p-3 bg-[#F97316]/5 border border-[#F97316]/20 rounded-lg"><strong class="text-[#F97316] block mb-1 font-mono">PRIORITY</strong> {rec}</li>
            """
            
        # Footer
        ack_by = brief.get("acknowledged_by")
        ack_at = brief.get("acknowledged_at")
        ack_html = ""
        if ack_by and ack_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ack_at.replace('Z', '+00:00'))
                ack_at_str = dt.strftime("%b %d, %Y %H:%M")
            except:
                ack_at_str = ack_at
            ack_html = f"""
            <div class="text-[#22C55E] font-bold text-sm text-center py-2 font-mono">
                ✓ ACKNOWLEDGED BY {ack_by.upper()} AT {ack_at_str}
            </div>
            """
        else:
            ack_html = """
            <div class="text-slate-500 font-mono text-center text-xs">
                HANDOVER PENDING ACKNOWLEDGEMENT BY INCOMING LEAD
            </div>
            """
            
        html_content += f"""
                    </ol>
                </div>
                
                <!-- Brief Footer -->
                <div class="border-t border-white/10 pt-6 mt-6 flex flex-col items-center gap-4">
                    {ack_html}
                    <div class="text-[10px] text-slate-500 font-mono text-center">
                        Generated by IndexField · {generated_at}<br>
                        {brief.get("facility_name")} · Confidential
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve shared brief page: {str(e)}")
