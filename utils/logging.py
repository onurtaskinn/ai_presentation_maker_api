import streamlit as st
from datetime import datetime
import json
import os

def initialize_logging():
    time = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"presentation_{time}.json"
    return {
        "timestamp": time,
        "process_steps": [],
        "metadata": {
            "start_time": time,
            "completion_status": {
                "topic_selection": False,
                "outline_generation": False,
                "content_generation": False
            }
        }
    }, filename

def save_logs():
    """Save the current logs to file"""
    if "results" in st.session_state and "filename" in st.session_state:
        try:
            os.makedirs("./_outputs", exist_ok=True)
            with open(f"./_outputs/{st.session_state.filename}", "w") as f:
                json.dump(st.session_state.results, f, indent=3)
            return True
        except Exception as e:
            st.error(f"Error saving logs: {str(e)}")
            return False
    return False

def log_step(step_name: str, data: dict):
    """Add a step to the logs"""
    if "results" in st.session_state:
        st.session_state.results["process_steps"].append({
            "step": step_name,
            "data": data,
            "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")
        })
        save_logs()  # Save after each step