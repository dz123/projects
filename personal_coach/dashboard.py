import sys
import subprocess
import os
import importlib.util

def install_package(package_name):
    print(f"📦 Installing missing package: {package_name}...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])

# def check_dependencies():
#     packages = {
#         'streamlit': 'streamlit',
#         'pandas': 'pandas',
#         'google.genai': 'google-genai', 
#         'garminconnect': 'garminconnect',
#         'dotenv': 'python-dotenv',
#         'tabulate': 'tabulate',
#         'altair': 'altair',
#         'langgraph': 'langgraph',
#         'langchain_google_genai': 'langchain-google-genai',
#         'langchain_core': 'langchain-core',
#         'langgraph.checkpoint.sqlite': 'langgraph-checkpoint-sqlite'
#     }
#     for import_name, pip_name in packages.items():
#         try:
#             if importlib.util.find_spec(import_name) is None:
#                 install_package(pip_name)
#         except ModuleNotFoundError:
#             install_package(pip_name)

# check_dependencies()

if __name__ == "__main__":
    if "streamlit" not in sys.modules:
        cmd = [sys.executable, "-m", "streamlit", "run", __file__]
        subprocess.run(cmd)
        sys.exit()

import streamlit as st
import pandas as pd
import datetime
import json
import altair as alt
from data_processor import DataProcessor
from agentic_coach import AgenticCoach 

st.set_page_config(layout="wide", page_title="Training Block Manager")

# Initialize Processors
processor = DataProcessor()

# Initialize the LangGraph Agent globally
if "agent" not in st.session_state:
    st.session_state.agent = AgenticCoach()
    st.session_state.thread_id = "unified_copilot_thread" 

agent = st.session_state.agent
thread_id = st.session_state.thread_id

st.title("🏃‍♂️ Training & Health Dashboard")

# --- GLOBAL SIDEBAR ACTIONS ---
# --- GLOBAL SIDEBAR ACTIONS ---
st.sidebar.subheader("🔄 Data Management")

if st.sidebar.button("☁️ Download Garmin Data"):
    with st.spinner("Syncing with Garmin Connect... (This may take a minute)"):
        try:
            # Run the sync script and capture the output
            result = subprocess.run([sys.executable, "garmin_sync.py"], capture_output=True, text=True)

            if result.returncode == 0:
                st.sidebar.success("Garmin data downloaded successfully!")
            else:
                combined = result.stdout + result.stderr
                if "[AUTH_REQUIRED]" in combined:
                    st.sidebar.warning("Garmin token expired. Use **Re-authorize Garmin** below to log in first.")
                else:
                    st.sidebar.error("Garmin sync failed.")
                    with st.sidebar.expander("View Error Log"):
                        st.code(combined)
        except Exception as e:
            st.sidebar.error(f"Execution error: {e}")

st.sidebar.divider()
st.sidebar.subheader("🔑 Re-authorize Garmin")
_SSO_URL = (
    "https://sso.garmin.com/mobile/sso/en_US/sign-in"
    "?clientId=GCM_ANDROID_DARK&service=https://mobile.integration.garmin.com/gcm/android"
)
st.sidebar.markdown(
    f"1. [Open Garmin login page]({_SSO_URL})\n"
    "2. Log in, then copy the full redirect URL from the address bar.\n"
    "3. Paste it below and click **Authorize**."
)
_ticket_input = st.sidebar.text_input("Redirect URL or ST-...-sso ticket", key="garmin_ticket")
if st.sidebar.button("Authorize", key="garmin_auth_btn"):
    if not _ticket_input.strip():
        st.sidebar.error("Please paste the redirect URL or ticket first.")
    else:
        with st.spinner("Exchanging token..."):
            _script = os.path.join(os.path.dirname(os.path.abspath("garmin_ticket_login.py")), "garmin_ticket_login.py")
            _res = subprocess.run(
                [sys.executable, _script, "--ticket", _ticket_input.strip(), "--compat"],
                capture_output=True, text=True,
            )
        if _res.returncode == 0:
            st.sidebar.success("Authorization successful! You can now sync Garmin data.")
        else:
            st.sidebar.error("Authorization failed.")
            with st.sidebar.expander("Details"):
                st.code(_res.stderr or _res.stdout)

if st.sidebar.button("📊 Update Health Ledger"):
    with st.spinner("Aggregating daily metrics..."):
        processor.compile_health_ledger()
    st.sidebar.success("Health ledger updated!")

st.sidebar.divider()

st.sidebar.divider()
st.sidebar.subheader("⚙️ AI Telemetry Settings")
downsample_sec = st.sidebar.slider("Sampling Interval (sec)", min_value=5, max_value=60, value=10, step=5, help="Controls how granular the data sent to the AI is. Lower = More detail but more tokens.")

# --- TABS ---
tab_train, tab_health = st.tabs(["🏋️ Training Log", "❤️ Recovery & Health"])

# ==========================================
# TAB 1: CALENDAR TRAINING VIEW
# ==========================================
with tab_train:
    blocks = processor.get_blocks()
    if not blocks: st.stop()
    current_block = blocks[0]

    today = datetime.date.today()
    today_iso = today.isoformat()

    # ---- Month options: April 2026 – November 2026 ----
    _range_start = datetime.date(2026, 4, 1)
    _range_end   = datetime.date(2026, 11, 1)
    month_list = []
    m = _range_start
    while m <= _range_end:
        month_list.append(m)
        m = (m.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    month_opts = {m.strftime("%B %Y"): m for m in month_list}
    default_month = today.strftime("%B %Y") if today.strftime("%B %Y") in month_opts else list(month_opts.keys())[0]

    selected_month_label = st.selectbox("Select Month", list(month_opts.keys()),
                                         index=list(month_opts.keys()).index(default_month))
    sel_month = month_opts[selected_month_label]
    month_start = sel_month
    month_end   = (sel_month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)

    # ---- Fetch all activities for the month ----
    all_month_activities = processor.get_activities_in_range(month_start.isoformat(), month_end.isoformat())

    activity_by_date = {}
    for act in all_month_activities:
        d_key = act['startTimeLocal'][:10]
        activity_by_date.setdefault(d_key, []).append(act)

    runs_all = [a for a in all_month_activities if 'running' in a.get('activityType', {}).get('typeKey', '')]
    total_dist = sum(r.get('distance', 0) for r in runs_all) / 1609.34
    st.info(f"**{selected_month_label}:** {len(runs_all)} Runs | {total_dist:.1f} Miles total")

    # ---- Auxiliary log (sidebar) ----
    with st.sidebar:
        st.divider()
        st.subheader("📓 Auxiliary Log")
        with st.expander("➕ Log Activity"):
            with st.form("aux_form"):
                a_date = st.date_input("Date")
                a_type = st.text_input("Type")
                a_desc = st.text_area("Description")
                if st.form_submit_button("Save"):
                    processor.add_aux_activity(a_date.isoformat(), a_type, a_desc)
                    st.rerun()
        auxs = processor.get_aux_in_range(month_start.isoformat(), month_end.isoformat())
        for a in auxs:
            st.info(f"**{a['date']}** | {a['type']}\n\n{a['desc']}")

    # ---- Build calendar weeks (Mon-Sun rows) ----
    # Find the Monday on or before month_start
    cal_start = month_start - datetime.timedelta(days=month_start.weekday())
    cal_weeks = []
    d = cal_start
    while d <= month_end:
        cal_weeks.append([d + datetime.timedelta(days=i) for i in range(7)])
        d += datetime.timedelta(days=7)

    # ---- CSS ----
    st.markdown("""
    <style>
    .cal-header { font-weight: 700; text-align: center; padding: 4px 2px; border-radius: 5px 5px 0 0; font-size: 0.88em; }
    .cal-header-today  { background: #ff4b4b; color: white; }
    .cal-header-normal { background: #f0f2f6; color: #333; }
    .cal-header-dimmed { background: #fafafa; color: #ccc; }
    .cal-section-label { font-size: 0.68em; font-weight: 700; color: #aaa; text-transform: uppercase;
                         letter-spacing: 0.06em; margin: 4px 0 1px; }
    .cal-plan-text  { font-size: 0.80em; min-height: 44px; color: #333; white-space: pre-wrap; }
    .cal-no-content { font-size: 0.75em; color: #ccc; min-height: 44px; }
    .cal-stat       { font-size: 0.80em; color: #333; line-height: 1.5; }
    .cal-stat-muted { font-size: 0.75em; color: #999; }
    .cal-total      { font-size: 0.85em; color: #333; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

    # ---- Column headers ----
    hdr_cols = st.columns(8)
    for hdr_col, name in zip(hdr_cols, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Week Total"]):
        with hdr_col:
            st.markdown(f"<div style='text-align:center;font-weight:700;font-size:0.85em;color:#666'>{name}</div>",
                        unsafe_allow_html=True)

    # ---- Render each week row ----
    for week_days in cal_weeks:
        row_cols = st.columns(8)

        # Pre-compute weekly totals (only in-month days)
        week_runs = []
        for day in week_days:
            if month_start <= day <= month_end:
                week_runs.extend(
                    a for a in activity_by_date.get(day.isoformat(), [])
                    if 'running' in a.get('activityType', {}).get('typeKey', '')
                )
        week_dist = sum(r.get('distance', 0) for r in week_runs) / 1609.34

        for col, day in zip(row_cols[:7], week_days):
            date_str  = day.isoformat()
            in_month  = month_start <= day <= month_end
            is_today  = date_str == today_iso
            activities = activity_by_date.get(date_str, []) if in_month else []
            runs = [a for a in activities if 'running' in a.get('activityType', {}).get('typeKey', '')]
            plan_text = processor.get_daily_plan(date_str) if in_month else ""

            with col:
                if not in_month:
                    hdr_cls = "cal-header-dimmed"
                elif is_today:
                    hdr_cls = "cal-header-today"
                else:
                    hdr_cls = "cal-header-normal"

                st.markdown(
                    f'<div class="cal-header {hdr_cls}">{day.strftime("%d")}</div>',
                    unsafe_allow_html=True,
                )

                if not in_month:
                    st.markdown("<div style='min-height:120px;border:1px solid #f5f5f5;border-radius:0 0 5px 5px'></div>",
                                unsafe_allow_html=True)
                    continue

                with st.container(border=True):
                    # TOP: Plan
                    st.markdown('<div class="cal-section-label">Plan</div>', unsafe_allow_html=True)
                    if plan_text:
                        st.markdown(f'<div class="cal-plan-text">{plan_text}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="cal-no-content">—</div>', unsafe_allow_html=True)

                    with st.popover("✏️", use_container_width=False):
                        new_plan = st.text_area(
                            f"{day.strftime('%a %b %d')}",
                            value=plan_text or "",
                            key=f"plan_ta_{date_str}",
                            height=80,
                        )
                        if st.button("Save", key=f"save_plan_{date_str}"):
                            processor.save_daily_plan(date_str, new_plan)
                            st.rerun()

                    st.markdown("<hr style='margin:5px 0;border-color:#eee'>", unsafe_allow_html=True)

                    # BOTTOM: Actual
                    st.markdown('<div class="cal-section-label">Actual</div>', unsafe_allow_html=True)
                    if runs:
                        for run in runs:
                            meta      = run.get('manual_meta', {})
                            dist_mi   = run.get('distance', 0) / 1609.34
                            avg_hr    = run.get('averageHR')
                            avg_speed = run.get('averageSpeed')
                            name      = meta.get('name', run.get('activityName', 'Run'))
                            pace_str  = ""
                            if avg_speed and avg_speed > 0:
                                p = (1 / avg_speed) * (1609.34 / 60)
                                pace_str = f"{int(p)}:{int((p % 1)*60):02d}/mi"

                            lines = [f"<b>{name}</b>", f"📏 {dist_mi:.1f} mi"]
                            if pace_str: lines.append(f"⏱ {pace_str}")
                            if avg_hr:   lines.append(f"❤️ {int(avg_hr)} bpm")
                            st.markdown(
                                '<div class="cal-stat">' + "<br/>".join(lines) + "</div>",
                                unsafe_allow_html=True,
                            )
                            is_selected = st.session_state.get('selected_run_id') == run['activityId']
                            btn_label = "▲ Hide" if is_selected else "▼ Details"
                            if st.button(btn_label, key=f"view_{run['activityId']}"):
                                st.session_state['selected_run_id'] = None if is_selected else run['activityId']
                                st.session_state['selected_run_data'] = None if is_selected else run
                                st.session_state['editing_run_id'] = None
                                st.session_state['selected_week_start'] = None
                                st.session_state['selected_week_runs'] = None
                                st.rerun()
                    elif activities:
                        act_type = activities[0].get('activityType', {}).get('typeKey', 'activity').replace('_', ' ').title()
                        st.markdown(f'<div class="cal-stat-muted">{act_type}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="cal-no-content">Rest</div>', unsafe_allow_html=True)

        # Weekly total column
        week_key = week_days[0].isoformat()
        is_week_selected = st.session_state.get('selected_week_start') == week_key
        with row_cols[7]:
            with st.container(border=True):
                if week_dist > 0:
                    n = len(week_runs)
                    st.markdown(
                        f'<div class="cal-total"><b>{week_dist:.1f}</b> mi<br/>'
                        f'<span style="font-size:0.8em;color:#888">{n} run{"s" if n != 1 else ""}</span></div>',
                        unsafe_allow_html=True,
                    )
                    wk_btn = "▲ Hide" if is_week_selected else "▼ Details"
                    if st.button(wk_btn, key=f"week_{week_key}"):
                        st.session_state['selected_week_start'] = None if is_week_selected else week_key
                        st.session_state['selected_week_runs'] = None if is_week_selected else week_runs
                        st.session_state['selected_run_id'] = None
                        st.session_state['selected_run_data'] = None
                        st.rerun()
                else:
                    st.markdown('<div class="cal-total" style="color:#ccc">0 mi</div>', unsafe_allow_html=True)

    # ---- Weekly overlay panel ----
    selected_week_start = st.session_state.get('selected_week_start')
    if selected_week_start:
        week_runs_data = st.session_state.get('selected_week_runs') or []
        runs_with_telemetry = [
            r for r in week_runs_data
            if os.path.exists(os.path.join("data", "get_activity_details", f"{r['activityId']}.json"))
        ]
        if runs_with_telemetry:
            st.divider()
            st.subheader(f"Week of {selected_week_start} — Overlaid Runs")

            # Build combined DataFrames
            frames_hr, frames_pace, frames_elev = [], [], []
            for run in runs_with_telemetry:
                run_id  = run['activityId']
                meta    = run.get('manual_meta', {})
                label   = meta.get('name', run.get('activityName', str(run_id)))
                date_lbl = run.get('startTimeLocal', '')[:10]
                run_label = f"{date_lbl} · {label}"
                laps = processor.get_run_laps(run_id)
                df_raw, _ = processor.get_activity_telemetry(run_id, laps=laps, downsample_sec=downsample_sec)
                if df_raw is None or df_raw.empty:
                    continue
                df_raw = df_raw.copy()
                df_raw['Run'] = run_label
                hr_df = df_raw[['Second', 'HeartRate', 'Run']].dropna(subset=['HeartRate'])
                if not hr_df.empty:
                    frames_hr.append(hr_df)
                pace_df = df_raw[['Second', 'Pace', 'Run']].dropna(subset=['Pace'])
                pace_df = pace_df[pace_df['Pace'].between(4, 15)]
                if not pace_df.empty:
                    frames_pace.append(pace_df)
                if df_raw['Elevation'].notna().any():
                    elev_df = df_raw[['Second', 'Elevation', 'Run']].dropna(subset=['Elevation'])
                    frames_elev.append(elev_df)

            tab_hr, tab_pace, tab_elev = st.tabs(["❤️ Heart Rate", "👟 Pace", "⛰️ Elevation"])

            color_scale = alt.Color('Run:N', legend=alt.Legend(title='Run', orient='bottom'))

            with tab_hr:
                if frames_hr:
                    df_all = pd.concat(frames_hr, ignore_index=True)
                    chart = alt.Chart(df_all).mark_line(opacity=0.8, strokeWidth=1.5).encode(
                        x=alt.X('Second:Q', title='Time (seconds)'),
                        y=alt.Y('HeartRate:Q', scale=alt.Scale(zero=False), title='Heart Rate (bpm)'),
                        color=color_scale,
                        tooltip=['Run', 'Second', 'HeartRate'],
                    ).interactive()
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("No heart rate data for this week.")

            with tab_pace:
                if frames_pace:
                    df_all = pd.concat(frames_pace, ignore_index=True)
                    chart = alt.Chart(df_all).mark_line(opacity=0.8, strokeWidth=1.5).encode(
                        x=alt.X('Second:Q', title='Time (seconds)'),
                        y=alt.Y('Pace:Q', scale=alt.Scale(zero=False, reverse=True), title='Pace (min/mi)'),
                        color=color_scale,
                        tooltip=['Run', 'Second', 'Pace'],
                    ).interactive()
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("No pace data for this week.")

            with tab_elev:
                if frames_elev:
                    df_all = pd.concat(frames_elev, ignore_index=True)
                    chart = alt.Chart(df_all).mark_line(opacity=0.8, strokeWidth=1.5).encode(
                        x=alt.X('Second:Q', title='Time (seconds)'),
                        y=alt.Y('Elevation:Q', scale=alt.Scale(zero=False), title='Elevation (m)'),
                        color=color_scale,
                        tooltip=['Run', 'Second', 'Elevation'],
                    ).interactive()
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("No elevation data for runs this week (treadmill or no GPS).")
        else:
            st.info("No telemetry data available for runs this week.")

    # ---- Detail panel ----
    selected_run_id = st.session_state.get('selected_run_id')
    if selected_run_id:
        selected_run = st.session_state.get('selected_run_data') or \
                       next((a for a in all_month_activities if a['activityId'] == selected_run_id), None)
        if selected_run:
            run_id = selected_run_id
            run    = selected_run
            meta   = run.get('manual_meta', {})
            has_stats     = 'category_stats' in meta
            splits_path   = os.path.join("data", "get_activity_splits", f"{run_id}.json")
            has_splits    = os.path.exists(splits_path)
            telemetry_path = os.path.join("data", "get_activity_details", f"{run_id}.json")
            has_telemetry = os.path.exists(telemetry_path)
            laps = processor.get_run_laps(run_id)

            st.divider()
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    display_name = meta.get('name', run.get('activityName', 'Run'))
                    st.subheader(display_name)
                    dist_mi = run.get('distance', 0) / 1609.34
                    st.caption(f"{run.get('startTimeLocal', '')[:10]} | {dist_mi:.2f} mi")

                    if has_stats:
                        df_stats = pd.DataFrame(meta['category_stats'])
                        st.dataframe(df_stats, hide_index=True)
                    elif not has_splits:
                        st.warning("⚠️ Splits not synced.")
                    else:
                        st.info("ℹ️ Uncategorized. Click Edit.")

                with c2:
                    if has_splits:
                        if st.button("Edit", key=f"ed_{run_id}"):
                            st.session_state['editing_run_id'] = run_id
                            st.rerun()

                    if has_stats:
                        if st.button("Analyze", key=f"ai_{run_id}"):
                            with st.spinner("Coach is thinking..."):
                                ctx = processor.build_agent_working_memory(run_id, current_block['id'])
                                if "error" not in ctx:
                                    ctx['workout_summary']['name'] = meta.get('name', run.get('activityName', 'Unnamed Workout'))
                                    ctx['workout_summary']['notes'] = meta.get('notes', '')
                                    df_ai = None
                                    if has_telemetry and hasattr(processor, 'get_activity_telemetry'):
                                        _, df_ai = processor.get_activity_telemetry(run_id, laps=laps, downsample_sec=downsample_sec)
                                    history = processor.search_episodic_memories(limit=3)
                                    report = agent.analyze_run(
                                        working_memory_dict=ctx,
                                        thread_id=f"run_analysis_{run_id}",
                                        telemetry_df=df_ai,
                                        historical_memories=history,
                                    )
                                    st.session_state[f"report_{run_id}"] = report
                                    try:
                                        memory_payload = agent.generate_episodic_summary(ctx, telemetry_df=df_ai)
                                        processor.save_episodic_memory(
                                            activity_id=run_id,
                                            date=ctx['date'],
                                            summary_text=memory_payload.get('summary_text', 'Run completed.'),
                                            tags=memory_payload.get('tags', []),
                                        )
                                    except Exception as e:
                                        st.sidebar.warning(f"Failed to generate episodic memory for {run_id}: {e}")
                                    st.rerun()
                                else:
                                    st.error("Could not build agent context.")

                if has_telemetry and hasattr(processor, 'get_activity_telemetry'):
                    with st.expander("📈 Telemetry Curves", expanded=True):
                        df_raw, df_ai = processor.get_activity_telemetry(run_id, laps=laps, downsample_sec=downsample_sec)
                        if df_raw is not None and not df_raw.empty:
                            has_elev = df_raw['Elevation'].notna().any()
                            elev_tab_label = "⛰️ Elevation" if has_elev else "⛰️ Elevation (n/a)"
                            tab_hr, tab_pace, tab_elev, tab_ai_view = st.tabs(["❤️ Heart Rate", "👟 Pace", elev_tab_label, "🤖 AI Data View"])
                            with tab_hr:
                                hr_chart = alt.Chart(df_raw.dropna(subset=['HeartRate'])).mark_line(color='#ff4b4b').encode(
                                    x=alt.X('Second:Q', title='Time (seconds)'),
                                    y=alt.Y('HeartRate:Q', scale=alt.Scale(zero=False), title='Heart Rate (bpm)'),
                                    tooltip=['Second', 'HeartRate'],
                                ).interactive()
                                st.altair_chart(hr_chart, use_container_width=True)
                            with tab_pace:
                                pace_df = df_raw.dropna(subset=['Pace']).copy()
                                pace_df['Pace'] = pace_df['Pace'].clip(lower=4, upper=15)
                                pace_chart = alt.Chart(pace_df).mark_line(color='#4b4bff').encode(
                                    x=alt.X('Second:Q', title='Time (seconds)'),
                                    y=alt.Y('Pace:Q', scale=alt.Scale(reverse=True), title='Pace (min/mi)'),
                                    tooltip=['Second', 'Pace'],
                                ).interactive()
                                st.altair_chart(pace_chart, use_container_width=True)
                            with tab_elev:
                                if not has_elev:
                                    st.info("No elevation data for this activity (treadmill or GPS not recorded).")
                                else:
                                    elev_df = df_raw.dropna(subset=['Elevation']).copy()
                                    elev_area = alt.Chart(elev_df).mark_area(opacity=0.3, color='#2ca02c').encode(
                                        x=alt.X('Second:Q', title='Time (seconds)'),
                                        y=alt.Y('Elevation:Q', scale=alt.Scale(zero=False), title='Elevation (m)'),
                                    )
                                    elev_line = alt.Chart(elev_df).mark_line(color='#2ca02c', size=2).encode(
                                        x=alt.X('Second:Q', title='Time (seconds)'),
                                        y=alt.Y('Elevation:Q', scale=alt.Scale(zero=False), title='Elevation (m)'),
                                        tooltip=['Second', 'Elevation'],
                                    )
                                    st.altair_chart((elev_area + elev_line).interactive(), use_container_width=True)
                            with tab_ai_view:
                                st.caption(f"Downsampled CSV ({downsample_sec}s intervals) sent to the AI Coach.")
                                st.dataframe(df_ai, hide_index=True)

                if f"report_{run_id}" in st.session_state:
                    st.markdown("---")
                    st.markdown("### 📋 Coach's Review")
                    st.markdown(st.session_state[f"report_{run_id}"])
                    st.markdown("#### 💬 Discuss this Run")
                    chat_history = processor.get_run_chat_history(run_id)
                    for msg in chat_history:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])
                    if run_prompt := st.chat_input("Ask a follow-up about this run...", key=f"chat_input_{run_id}"):
                        processor.save_run_chat_message(run_id, "user", run_prompt)
                        with st.chat_message("user"):
                            st.markdown(run_prompt)
                        with st.chat_message("assistant"):
                            with st.spinner("Coach is reviewing the telemetry..."):
                                response = agent.follow_up_chat(user_input=run_prompt, thread_id=f"run_analysis_{run_id}")
                                st.markdown(response)
                                processor.save_run_chat_message(run_id, "assistant", response)
                        st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Close Report", key=f"close_{run_id}"):
                        with st.spinner("Consolidating memory records..."):
                            chat_summary = agent.summarize_thread(f"run_analysis_{run_id}")
                            if chat_summary:
                                processor.append_chat_to_episodic_memory(run_id, chat_summary)
                        del st.session_state[f"report_{run_id}"]
                        st.rerun()

                if st.session_state.get('editing_run_id') == run_id:
                    st.divider()
                    st.markdown("#### ✏️ Categorize Laps")
                    state_key = f"lap_cats_{run_id}"
                    laps = processor.get_run_laps(run_id)
                    if laps:
                        if state_key not in st.session_state:
                            saved_cats = meta.get('lap_categories', [])
                            if saved_cats and len(saved_cats) == len(laps):
                                st.session_state[state_key] = saved_cats.copy()
                            else:
                                st.session_state[state_key] = ["Hold Back Easy"] * len(laps)
                        new_name = st.text_input("Run Name", value=meta.get('name', run.get('activityName', '')))
                        notes = st.text_area("Subjective Notes (Optional)", value=meta.get('notes', ''), help="How did the run feel? Any aches, fatigue, or pacing thoughts?")
                        w_num = st.number_input("Week #", value=meta.get('week_num', 0))
                        lap_rows = []
                        for i, lap in enumerate(laps):
                            d_mi = lap.get('distance', 0) / 1609.34
                            t_sec = lap.get('duration', 0)
                            pace = "N/A"
                            if t_sec > 0 and d_mi > 0:
                                p_min = (t_sec / 60) / d_mi
                                pace = f"{int(p_min)}:{int((p_min % 1) * 60):02d}"
                            cat = st.session_state[state_key][i] if i < len(st.session_state[state_key]) else "Hold Back Easy"
                            lap_rows.append({"Lap": i + 1, "Dist (mi)": round(d_mi, 2), "Pace": pace, "Avg HR": lap.get('averageHR', 0), "category": cat})
                        cat_options = ["Hold Back Easy", "Steady Effort", "Increasing Effort", "Marathon", "LT Effort", "VO2Max", "Sprint", "Rest"]
                        st.markdown("##### ⚡️ Batch Edit Laps")
                        col_batch1, col_batch2, col_batch3 = st.columns([2, 2, 1])
                        with col_batch1:
                            batch_laps = st.multiselect("Select Laps to update:", options=[r["Lap"] for r in lap_rows], key=f"bl_{run_id}")
                        with col_batch2:
                            batch_cat = st.selectbox("Assign Category:", options=cat_options, key=f"bc_{run_id}")
                        with col_batch3:
                            st.write("")
                            st.write("")
                            if st.button("Apply to Selected", key=f"apply_{run_id}"):
                                for lap_num in batch_laps:
                                    st.session_state[state_key][lap_num - 1] = batch_cat
                                st.rerun()
                        st.markdown("##### 📝 Individual Laps")
                        edited_laps = st.data_editor(
                            lap_rows,
                            column_config={"category": st.column_config.SelectboxColumn("Category", options=cat_options, required=True)},
                            hide_index=True,
                            key=f"editor_{run_id}",
                        )
                        for i, row in enumerate(edited_laps):
                            if i < len(st.session_state[state_key]):
                                st.session_state[state_key][i] = row['category']
                        st.markdown("<br>", unsafe_allow_html=True)
                        c1, c2, _ = st.columns([1, 1, 4])
                        with c1:
                            if st.button("Save & Calculate", type="primary", key=f"save_{run_id}"):
                                lap_cats_to_save = []
                                for i, cat in enumerate(st.session_state[state_key]):
                                    laps[i]['category'] = cat
                                    lap_cats_to_save.append(cat)
                                cat_stats = processor.calculate_category_stats(laps)
                                processor.save_run_metadata(run_id, w_num, new_name, cat_stats, notes=notes, lap_categories=lap_cats_to_save)
                                del st.session_state[state_key]
                                st.session_state['editing_run_id'] = None
                                st.rerun()
                        with c2:
                            if st.button("Cancel", key=f"cancel_{run_id}"):
                                if state_key in st.session_state:
                                    del st.session_state[state_key]
                                st.session_state['editing_run_id'] = None
                                st.rerun()
                    else:
                        st.error("No valid laps found.")
                        if st.button("Cancel", key=f"cancel_err_{run_id}"):
                            st.session_state['editing_run_id'] = None
                            st.rerun()

# ==========================================
# TAB 2: RECOVERY & HEALTH
# ==========================================
with tab_health:
    st.header("Holistic Health View")
    
    stats = processor.get_health_stats()
    if not stats:
        st.warning("No health data found. Please run sync.")
    else:
        df = pd.DataFrame(stats)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        col1, col2, col3, col4 = st.columns(4)
        last_day = df.iloc[-1]
        
        def safe_metric(label, key, avg_key=None, inverse=False):
            val = last_day.get(key)
            if pd.isna(val): return st.metric(label, "N/A")
            
            val = float(val)
            delta = None
            if avg_key and not pd.isna(df[avg_key].mean()):
                diff = val - df[avg_key].mean()
                delta = f"{diff:.1f}"
                
            color = "inverse" if inverse else "normal"
            st.metric(label, f"{int(val)}", delta=delta, delta_color=color)

        with col1: safe_metric("Sleep Score", "sleep_score", "sleep_score")
        with col2: safe_metric("RHR", "rhr", "rhr", inverse=True)
        with col3: safe_metric("HRV (ms)", "hrv", "hrv")
        with col4: safe_metric("Stress", "stress", "stress", inverse=True)

        st.divider()

        st.subheader("HRV Status (7-Day Average vs Baseline)")
        df['hrv_7d'] = df['hrv'].rolling(window=7, min_periods=1).mean()
        df['baseline_mean'] = df['hrv'].rolling(window=21, min_periods=1).mean()
        df['baseline_std'] = df['hrv'].rolling(window=21, min_periods=1).std().clip(lower=3.5)
        df['baseline_high'] = df['baseline_mean'] + df['baseline_std']
        df['baseline_low'] = df['baseline_mean'] - df['baseline_std']

        def determine_hrv_status(row):
            if pd.isna(row['hrv_7d']) or pd.isna(row['baseline_low']): 
                return "Unknown"
            if row['hrv_7d'] < row['baseline_low'] or row['hrv_7d'] > row['baseline_high']:
                return "Unbalanced"
            return "Balanced"

        df['hrv_status'] = df.apply(determine_hrv_status, axis=1)

        chart_df = df.reset_index().dropna(subset=['hrv_7d'])

        baseline_band = alt.Chart(chart_df).mark_area(opacity=0.15, color='#888888').encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('baseline_low:Q', title='HRV (ms)', scale=alt.Scale(zero=False)),
            y2='baseline_high:Q'
        )

        hrv_line = alt.Chart(chart_df).mark_line(color='#A0A0A0', size=1.5).encode(
            x='date:T',
            y='hrv_7d:Q'
        )

        hrv_points = alt.Chart(chart_df).mark_circle(size=80).encode(
            x='date:T',
            y='hrv_7d:Q',
            color=alt.Color('hrv_status:N', 
                            scale=alt.Scale(domain=['Balanced', 'Unbalanced', 'Unknown'], 
                                            range=['#2ca02c', '#d62728', '#7f7f7f']),
                            legend=alt.Legend(title="Status")),
            tooltip=[
                alt.Tooltip('date:T', title='Date'),
                alt.Tooltip('hrv_7d:Q', title='7-Day Avg HRV', format='.1f'),
                alt.Tooltip('hrv:Q', title='Last Night HRV', format='.1f'),
                alt.Tooltip('baseline_low:Q', title='Baseline Low', format='.1f'),
                alt.Tooltip('baseline_high:Q', title='Baseline High', format='.1f'),
                alt.Tooltip('hrv_status:N', title='Status')
            ]
        )

        final_hrv_chart = alt.layer(baseline_band, hrv_line, hrv_points).properties(height=300).interactive()
        st.altair_chart(final_hrv_chart, use_container_width=True)

        col_charts_1, col_charts_2 = st.columns(2)
        with col_charts_1:
            st.subheader("Sleep Quality vs. Volume")
            st.line_chart(df[['sleep_score', 'run_miles']])
        with col_charts_2:
            st.subheader("RHR vs. Stress")
            st.line_chart(df[['rhr', 'stress']])

        # ==========================================
        # 4. LANGGRAPH AGENT CHATBOX
        # ==========================================
        st.divider()
        st.subheader("🤖 Unified AI Co-Pilot")
        st.caption("Ask questions about your pacing, HRV, sleep, or training blocks. The Supervisor will route it to the right expert.")

        if st.button("🩺 Analyze Today's Health"):
            with st.spinner("Doctor is reviewing your charts..."):
                yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
                raw_sleep = processor.load_json_safe(processor.paths['sleep'], f"{yesterday_str}.json")
                
                # 1. Generate report (LangGraph auto-saves the full conversation to data/chat_memory.db)
                report = agent.analyze_health(
                    history_df=df.tail(14), 
                    yesterday_raw=raw_sleep, 
                    thread_id=thread_id
                )
                
                # 2. Extract the doctor's core verdict and write it to permanent episodic memory
                try:
                    import datetime
                    today_str = datetime.date.today().isoformat()
                    processor.save_episodic_memory(
                        activity_id=f"health_check_{today_str}",
                        date=today_str,
                        summary_text=f"Daily Health Check: {report}",  # Store doctor's analysis as permanent record
                        tags=["Daily Health", "Doctor Analysis", "Recovery"]
                    )
                except Exception as e:
                    st.sidebar.warning(f"Failed to save health memory: {e}")

                st.rerun()

        if prompt := st.chat_input("Ask your agents a question...", key="global_chat_input"):
            with st.spinner("Supervisor is routing your request..."):
                import datetime
                today_str = datetime.date.today().isoformat()
                
                if not df.empty:
                    latest_health_dict = df.iloc[-1].dropna().to_dict()
                    if 'date' not in latest_health_dict:
                        latest_health_dict['date'] = df.index[-1].isoformat()[:10]
                else:
                    latest_health_dict = {}
                
                recent_miles = df.tail(7)['run_miles'].sum() if not df.empty else 0
                
                # Fetch the 5 most recent permanent memories (including chat advice)
                recent_memories = processor.search_episodic_memories(limit=5)
                memory_log = ""
                for m in recent_memories:
                    memory_log += f"- {m['date']}: {m['summary']}\n"
                    if 'coach_advice' in m:
                        memory_log += f"  > Past coaching advice: {m['coach_advice']}\n"
                
                # Build a high-density global context JSON
                global_context = {
                    "current_date": today_str,
                    "athlete_status_today": latest_health_dict,
                    "recent_training_load": {
                        "last_7_days_miles": round(recent_miles, 1)
                    },
                    "episodic_memories": memory_log,  # Inject permanent memories
                    "instruction": "You are the global coach/doctor. Use the real-time snapshot and EPISODIC MEMORIES to answer."
                }
                
                context_str = f"=== REAL-TIME SNAPSHOT & MEMORIES ===\n{json.dumps(global_context, indent=2, ensure_ascii=False)}"
                
                agent.chat(
                    user_input=prompt, 
                    thread_id=thread_id,
                    system_context=context_str
                )
            st.rerun()

        history = agent.get_history(thread_id)
        chat_msgs = [msg for msg in history if msg.type != "system"]

        interactions = []
        current_interaction = []
        
        for msg in chat_msgs:
            if msg.type == "human":
                if current_interaction:
                    interactions.append(current_interaction)
                current_interaction = [msg]
            else:
                current_interaction.append(msg)
                
        if current_interaction:
            interactions.append(current_interaction)

        recent_interactions = interactions[-10:][::-1]

        for interaction in recent_interactions:
            for msg in interaction:
                content = msg.content
                if isinstance(content, list):
                    content = "".join([block.get("text", "") for block in content if isinstance(block, dict) and "text" in block])
                    
                role = "user" if msg.type == "human" else "assistant"
                with st.chat_message(role):
                    st.markdown(content)