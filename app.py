import streamlit as st

st.set_page_config(page_title="AI CONTENT STUDIO", page_icon=":card_file_box:", layout="wide")
st.header(body=":card_file_box: AI CONTENT STUDIO ⚡⚡⚡", divider="orange")

st.write("""
# Welcome to AI Content Studio

This application helps you create professional presentations with AI assistance. The process is divided into three main steps:

1. **Topic Selection**: Choose your presentation topic and specify the number of slides
2. **Outline Generation**: AI generates and refines a structured outline for your presentation
3. **Content Generation**: Create detailed content and images for each slide

Click the button below to begin your presentation creation journey.
""")
st.session_state.input_tokens = 0
st.session_state.output_tokens = 0

if st.button("Start Creating"):
    st.switch_page("pages/1_Topic_Selection.py")