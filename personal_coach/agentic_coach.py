import os
import sqlite3
import json
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

class AgenticCoach:
    # --- STEP 1: Inject Semantic Memory ---
    def __init__(self, db_path="data/chat_memory.db", user_profile: dict = None):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Accept global profile; default to empty if none provided
        self.user_profile = user_profile or {}
        
        self.api_key = self._find_api_key()
        if not self.api_key:
            print("[WARNING] Agentic Coach: No API Key found.")
        else:
            os.environ["OPENAI_API_KEY"] = self.api_key

        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4, api_key=self.api_key)
        self.router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=self.api_key)
        
        graph_builder = StateGraph(State)
        graph_builder.add_node("coach", self._coach_node)
        graph_builder.add_node("doctor", self._doctor_node)
        
        graph_builder.add_conditional_edges(
            START, 
            self._route_message, 
            {"coach": "coach", "doctor": "doctor"}
        )
        
        graph_builder.add_edge("coach", END)
        graph_builder.add_edge("doctor", END)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.memory = SqliteSaver(self.conn)
        self.graph = graph_builder.compile(checkpointer=self.memory)

    def _find_api_key(self):
        key = os.getenv("OPENAI_KEY")
        if key: return key
        current_dir = Path(__file__).resolve().parent
        env_path = current_dir / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            key = os.getenv("OPENAI_KEY")
            if key: return key
        try: return st.secrets["OPENAI_KEY"]
        except: return None

    def _route_message(self, state: State) -> str:
        last_msg = state["messages"][-1].content
        if isinstance(last_msg, list):
            last_msg = "".join([block.get("text", "") for block in last_msg if isinstance(block, dict) and "text" in block])
            
        if "bearing in mind my workouts" in last_msg.lower():
            return "coach"

        prompt = f"""
        You are a routing supervisor. Decide if the following message should be handled by the 'coach' or 'doctor'.
        - COACH: Running, pace, splits, workouts, run analysis, training blocks.
        - DOCTOR: Health, HRV, sleep, stress, resting heart rate, recovery.
        If it's a general greeting or ambiguous, pick 'coach'.
        Output ONLY the exact word 'coach' or 'doctor'.
        
        User message: {last_msg}
        """
        response = self.router_llm.invoke([HumanMessage(content=prompt)])
        
        content = response.content
        if isinstance(content, list):
            content = "".join([block.get("text", "") for block in content if isinstance(block, dict) and "text" in block])
            
        decision = content.strip().lower()
        if "doctor" in decision:
            return "doctor"
        return "coach"

    # --- STEP 1 continued: Wire global memory into System Prompt ---
    def _coach_node(self, state: State):
        profile_str = json.dumps(self.user_profile, indent=2)
        sys_msg = SystemMessage(content=f"""
        You are an elite Running Coach and Sports Physiologist. 
        Focus on biomechanics, pace, splits, and training, but ALWAYS connect them to the athlete's overall health context.
        
        === USER BASELINE PROFILE (SEMANTIC MEMORY) ===
        {profile_str}
        ===============================================
        Use this baseline to evaluate all incoming data.
        """)
        messages = [sys_msg] + state["messages"]
        response = self.llm.invoke(messages)
        return {"messages": [response]}

    def _doctor_node(self, state: State):
        profile_str = json.dumps(self.user_profile, indent=2)
        sys_msg = SystemMessage(content=f"""
        You are an elite physiological Health Doctor. 
        Focus on HRV, Sleep Scores, and nervous system recovery. 
        
        === USER BASELINE PROFILE (SEMANTIC MEMORY) ===
        {profile_str}
        ===============================================
        Acknowledge running data if it explains fatigue, but stick to your domain.
        """)
        messages = [sys_msg] + state["messages"]
        response = self.llm.invoke(messages)
        return {"messages": [response]}

    def chat(self, user_input: str, thread_id: str, system_context: str = None):
        config = {"configurable": {"thread_id": thread_id}}
        messages_to_send = []
        
        if system_context:
            messages_to_send.append(SystemMessage(content=system_context))
            
        messages_to_send.append(HumanMessage(content=user_input))
        
        events = self.graph.stream(
            {"messages": messages_to_send}, 
            config, 
            stream_mode="values"
        )
        
        for event in events:
            final_message = event["messages"][-1]
            
        content = final_message.content
        if isinstance(content, list):
            return "".join([block.get("text", "") for block in content if isinstance(block, dict) and "text" in block])
        return str(content)
        
    def get_history(self, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = self.graph.get_state(config)
            return state.values.get("messages", [])
        except:
            return []

    def follow_up_chat(self, user_input: str, thread_id: str):
        return self.chat(user_input=user_input, thread_id=thread_id, system_context=None)

    def summarize_thread(self, thread_id: str):
        """
        Read a thread's chat history and distill the core advice, ready for permanent memory.
        """
        history = self.get_history(thread_id)
        # If only a system prompt and one user message, not enough depth — skip
        if len(history) <= 3:
            return None

        chat_text = "\n".join([f"{msg.type}: {msg.content}" for msg in history if msg.type in ['human', 'ai']])

        prompt = f"""
        Compress the following coach-athlete conversation into 1-2 sentences of core conclusions or advice.
        Focus on: the athlete's pain points/feelings and the coach's specific recommendations. Use third-person statements.

        Conversation:
        {chat_text}
        """
        # Use router_llm (Temperature=0) for objective, precise summaries
        response = self.router_llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()

    # --- STEP 2: Working Memory fusion analysis ---
    def analyze_run(self, working_memory_dict: dict, thread_id: str, telemetry_df=None, historical_memories: list = None):
        """
        Takes the dense JSON from dp.build_agent_working_memory() and historical records to perform a deep analysis.
        """
        run_name = working_memory_dict.get('workout_summary', {}).get('name', 'Unnamed Workout')

        # Extract similar historical records (if available)
        history_section = ""
        if historical_memories:
            history_section = "\n\n**Historical Context (similar past workouts):**\n"
            for mem in historical_memories:
                history_section += f"- {mem['date']}: {mem['summary']}\n"

        telemetry_section = ""
        if telemetry_df is not None and not telemetry_df.empty:
            csv_data = telemetry_df.to_csv(index=False)
            telemetry_section = f"\n\n**Raw Telemetry Data (per-lap):**\n```csv\n{csv_data}\n```"

        working_memory_str = json.dumps(working_memory_dict, indent=2)

        system_instructions = f"""
        Act as an elite sports data scientist and physiologist.

        **Data Inputs:**
        - **Today's Working Memory (health + training context):**
        ```json
        {working_memory_str}
        ```
        {history_section}
        {telemetry_section}

        **Analysis Instructions:**
        1. **Intent vs. Execution:** Use the working memory JSON data as your analysis framework. Directly connect the `daily_readiness` metrics (sleep/HRV/etc.) to the actual running performance.
        2. **Historical Comparison:** If "Historical Context" is provided, explicitly compare today's run data against past performance to highlight progress or recurring issues.
        3. **Telemetry Analysis (critical):**
           - Evaluate the curve shapes of labeled laps (pace, cadence, elevation).
           - Identify cardiac lag during speed/interval work. Compare actual/peak HR against the expected zones from the Baseline Profile.

        **Output Format (Markdown):**
        ### Run Analysis: {run_name}
        *(Detailed observation report: connect the day's physiological readiness to actual telemetry execution. Compare with historical records if applicable.)*

        ### HR Zone Mapping (Today's Actual)
        | Effort Category | Baseline Zone | **Actual Mapping (Actual/Peak HR)** | Drift |
        | :--- | :--- | :--- | :--- |
        | [e.g. Marathon Pace] | [e.g. 145-160] | **[Fill in actual or peak HR]** | [e.g. +7 bpm] |

        ### Recommendations
        *(Provide actionable physiological or training advice for next steps.)*
        """

        run_date = working_memory_dict.get('date', 'today')
        user_message = f"Please analyze the workout named '{run_name}' that I did on {run_date}."

        return self.chat(
            user_input=user_message, 
            thread_id=thread_id, 
            system_context=system_instructions
        )

    # --- STEP 3: Episodic Memory (generate short summaries for future RAG retrieval) ---
    def generate_episodic_summary(self, working_memory_dict: dict, telemetry_df=None):
        """
        Calls the LLM purely to generate a dense, factual summary and tags to be saved 
        into the episodic vector/JSON database.
        """
        run_name = working_memory_dict.get('workout_summary', {}).get('name', 'Unnamed Workout')
        working_memory_str = json.dumps(working_memory_dict, indent=2)
        
        prompt = f"""
        You are an AI Memory Summarizer. Look at this run and compress the core physiological takeaways into a dense 50-75 word summary. 
        Focus on facts: Distance, Pace, HR Drift, and how Daily Readiness (like sleep) affected it. 
        Also, assign 2-4 broad categorization tags (e.g., "Long Run", "Fatigue", "VO2Max", "Hot Weather").

        Context:
        ```json
        {working_memory_str}
        ```

        Output EXACTLY in this JSON format, nothing else:
        {{
            "tags": ["Tag1", "Tag2"],
            "summary_text": "Your dense summary here."
        }}
        """
        # Create a temporary stateless LLM call for formatting
        formatting_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=self.api_key)
        response = formatting_llm.invoke([SystemMessage(content="You return strictly JSON."), HumanMessage(content=prompt)])
        
        try:
            # Clean up potential markdown formatting from the response
            content = response.content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except Exception as e:
            print(f"Error generating episodic memory: {e}")
            return {"tags": ["Analysis"], "summary_text": f"Completed {run_name}."}

    def analyze_health(self, history_df, yesterday_raw, thread_id: str):
        import datetime
        today_str = datetime.date.today().isoformat()
        yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        
        trends = history_df.to_markdown()

        sleep_dto = yesterday_raw.get('dailySleepDTO', {})
        sleep_details = {
            "deep_sleep_min": sleep_dto.get('deepSleepSeconds', 0) / 60,
            "rem_sleep_min": sleep_dto.get('remSleepSeconds', 0) / 60,
            "awake_min": sleep_dto.get('awakeSleepSeconds', 0) / 60,
            "feedback": sleep_dto.get('sleepScoreFeedback'),
            "stress_during_sleep": yesterday_raw.get('avgSleepStress')
        }

        system_instructions = f"""
        Act as a Holistic Health & Performance Doctor.

        **Core Objective:** Based on long-term data trends and last night's sleep quality ({yesterday_str}), provide a deep analysis of the athlete's recovery status for today ({today_str}).

        **Data Source 1: 14-Day Historical Trends (CSV format)**
        {trends}
        *(Columns: sleep_score, rhr=resting heart rate, hrv=heart rate variability, run_miles, stress=all-day stress level)*

        **Data Source 2: Last Night's Sleep Deep Dive (JSON extract)**
        - Deep Sleep: {sleep_details['deep_sleep_min']:.0f} minutes
        - REM Sleep: {sleep_details['rem_sleep_min']:.0f} minutes
        - Awake/Restless: {sleep_details['awake_min']:.0f} minutes
        - Garmin Feedback: "{sleep_details['feedback']}"
        - Overnight Stress: {sleep_details['stress_during_sleep']} (lower is better)

        **Analysis Required (use Markdown):**

        ### Trend Diagnosis
        *Review the 14-day history. Is RHR trending up? Is HRV declining? How does Sleep Score correlate with recent running mileage?*
        *Provide very specific medical/physiological observations.*

        ### Last Night's Sleep Quality
        *Don't just read the total score. Compare Deep Sleep (physical repair) vs. REM Sleep (neural/mental repair) ratios. Was the athlete truly rested, or in a state of "body recovered but mind still fatigued"? Factor in overnight stress.*

        ### Today's Readiness Verdict
        *Synthesize all objective data and provide a clear training recommendation for today ({today_str}).*
        *Choose one of the following as the baseline and justify:*
        * [GREEN LIGHT: Excellent condition, cleared for high-intensity training]
        * [YELLOW LIGHT: Recovering, recommend easy aerobic or cross-training only]
        * [RED LIGHT: Severe fatigue or illness risk, recommend complete rest]
        """

        # Route to the Doctor agent for health analysis
        user_message = f"Based on my recent physiological metrics, please provide a deep analysis of my health, recovery status, and sleep quality for today ({today_str})."

        return self.chat(
            user_input=user_message, 
            thread_id=thread_id, 
            system_context=system_instructions
        )