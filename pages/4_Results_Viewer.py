# pages/4_Results_Viewer.py
import streamlit as st
import json
from datetime import datetime

st.set_page_config(
    page_title="AI CONTENT STUDIO - Results Viewer",
    page_icon=":card_file_box:",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.header(body=":card_file_box: AI CONTENT STUDIO - Results Viewer ⚡", divider="orange")

# Check if we have the required session state variables
if ("final_outline" not in st.session_state or 
    "completed_slides" not in st.session_state or 
    len(st.session_state.completed_slides) != len(st.session_state.final_outline.slide_outlines)):
    st.error("Please complete the content generation first")
    st.stop()

# Display presentation overview
st.subheader("📊 Presentation Overview")
overview_container = st.container(border=True)
with overview_container:
    st.write(f"**Title:** {st.session_state.final_outline.presentation_title}")
    st.write(f"**Total Slides:** {len(st.session_state.final_outline.slide_outlines)}")
    st.write(f"**Generation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.write(f"**Token Usage:** {st.session_state.input_tokens} input tokens, {st.session_state.output_tokens} output tokens")

# Create tabs for different view modes
tab_slides, tab_export, tab_logs = st.tabs(["🎯 Slide View", "📑 Export View", "📋 Process Logs"])

with tab_slides:
    # Initialize the current slide index if not exists
    if "view_slide_idx" not in st.session_state:
        st.session_state.view_slide_idx = 0

    # Navigation
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.session_state.view_slide_idx > 0:
            if st.button("⬅️ Previous"):
                st.session_state.view_slide_idx -= 1
                st.rerun()

    with col2:
        # Slide selector
        selected_slide = st.select_slider(
            "Select Slide",
            options=range(len(st.session_state.final_outline.slide_outlines)),
            value=st.session_state.view_slide_idx,
            format_func=lambda x: f"Slide {x + 1}"
        )
        if selected_slide != st.session_state.view_slide_idx:
            st.session_state.view_slide_idx = selected_slide
            st.rerun()

    with col3:
        if st.session_state.view_slide_idx < len(st.session_state.final_outline.slide_outlines) - 1:
            if st.button("Next ➡️"):
                st.session_state.view_slide_idx += 1
                st.rerun()

    # Display current slide content
    current_slide = st.session_state.final_outline.slide_outlines[st.session_state.view_slide_idx]
    
    # Find the corresponding content in the results
    slide_content = None
    slide_image = None
    for step in st.session_state.results["process_steps"]:
        if step["step"] == f"initial_content_slide_{st.session_state.view_slide_idx + 1}":
            slide_content = step["data"]
        elif step["step"].startswith(f"image_generation_slide_{st.session_state.view_slide_idx + 1}_attempt_"):
            # Get the last image generation attempt
            slide_image = step["data"]["image_url"]

    if slide_content and slide_image:
        # Display slide content
        slide_container = st.container(border=True)
        with slide_container:
            st.subheader(f"🎯 Slide {st.session_state.view_slide_idx + 1}: {current_slide.slide_title}")
            
            # Create two columns for content and image
            col_content, col_image = st.columns([1, 1])
            
            with col_content:
                st.markdown("### On-screen Text")
                st.markdown(slide_content["slide_onscreen_text"])
                
                st.markdown("### Voiceover Text")
                st.markdown(slide_content["slide_voiceover_text"])
                
                with st.expander("Show Image Prompt"):
                    st.markdown(slide_content["slide_image_prompt"])
            
            with col_image:
                st.image(slide_image, use_container_width=True)

with tab_export:
    st.subheader("📑 Export Options")
    
    # Create export data structure
    export_data = {
        "presentation_title": st.session_state.final_outline.presentation_title,
        "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "slides": []
    }
    
    for idx, slide_outline in enumerate(st.session_state.final_outline.slide_outlines):
        slide_data = {
            "slide_number": idx + 1,
            "slide_title": slide_outline.slide_title,
            "slide_focus": slide_outline.slide_focus,
            "content": None,
            "image_url": None
        }
        
        # Find content and image in results
        for step in st.session_state.results["process_steps"]:
            if step["step"] == f"initial_content_slide_{idx + 1}":
                slide_data["content"] = step["data"]
            elif step["step"].startswith(f"image_generation_slide_{idx + 1}_attempt_"):
                slide_data["image_url"] = step["data"]["image_url"]
        
        export_data["slides"].append(slide_data)
    
    # Export options
    export_format = st.radio(
        "Choose Export Format",
        ["JSON", "Markdown", "HTML"],
        horizontal=True
    )
    
    if export_format == "JSON":
        st.download_button(
            label="Download JSON",
            data=json.dumps(export_data, indent=2),
            file_name=f"presentation_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    elif export_format == "Markdown":
        markdown_content = f"# {export_data['presentation_title']}\n\n"
        markdown_content += f"Generated on: {export_data['generation_date']}\n\n"
        
        for slide in export_data["slides"]:
            markdown_content += f"## Slide {slide['slide_number']}: {slide['slide_title']}\n\n"
            markdown_content += f"**Focus:** {slide['slide_focus']}\n\n"
            markdown_content += "### On-screen Text\n\n"
            markdown_content += f"{slide['content']['slide_onscreen_text']}\n\n"
            markdown_content += "### Voiceover Text\n\n"
            markdown_content += f"{slide['content']['slide_voiceover_text']}\n\n"
            markdown_content += "### Image Prompt\n\n"
            markdown_content += f"{slide['content']['slide_image_prompt']}\n\n"
            markdown_content += f"![Slide {slide['slide_number']} Image]({slide['image_url']})\n\n"
            markdown_content += "---\n\n"
        
        st.download_button(
            label="Download Markdown",
            data=markdown_content,
            file_name=f"presentation_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
    else:  # HTML
        html_content = f"""
        <html>
        <head>
            <title>{export_data['presentation_title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .slide {{ margin-bottom: 40px; padding: 20px; border: 1px solid #ccc; }}
                .slide-title {{ color: #2c3e50; }}
                .slide-focus {{ color: #7f8c8d; font-style: italic; }}
                .content-section {{ margin: 20px 0; }}
                img {{ max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <h1>{export_data['presentation_title']}</h1>
            <p>Generated on: {export_data['generation_date']}</p>
        """
        
        for slide in export_data["slides"]:
            html_content += f"""
            <div class="slide">
                <h2 class="slide-title">Slide {slide['slide_number']}: {slide['slide_title']}</h2>
                <p class="slide-focus"><strong>Focus:</strong> {slide['slide_focus']}</p>
                
                <div class="content-section">
                    <h3>On-screen Text</h3>
                    {slide['content']['slide_onscreen_text']}
                </div>
                
                <div class="content-section">
                    <h3>Voiceover Text</h3>
                    <p>{slide['content']['slide_voiceover_text']}</p>
                </div>
                
                <div class="content-section">
                    <h3>Image</h3>
                    <img src="{slide['image_url']}" alt="Slide {slide['slide_number']} Image">
                </div>
                
                <div class="content-section">
                    <h3>Image Prompt</h3>
                    <p>{slide['content']['slide_image_prompt']}</p>
                </div>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        st.download_button(
            label="Download HTML",
            data=html_content,
            file_name=f"presentation_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html"
        )

with tab_logs:
    st.subheader("📋 Process Logs")
    
    # Display process metadata
    st.markdown("### Process Overview")
    metadata = st.session_state.results["metadata"]
    st.json({
        "Start Time": metadata["start_time"],
        "Completion Time": metadata.get("completion_time", "Not completed"),
        "Status": metadata["completion_status"]
    })
    
    # Create a filterable view of the logs
    st.markdown("### Detailed Logs")
    
    # Create log filters
    log_types = set(step["step"].split("_")[0] for step in st.session_state.results["process_steps"])
    selected_types = st.multiselect(
        "Filter by Process Type",
        options=sorted(log_types),
        default=list(log_types)
    )
    
    # Display filtered logs
    for step in st.session_state.results["process_steps"]:
        if step["step"].split("_")[0] in selected_types:
            with st.expander(f"🔍 {step['step']} ({step.get('timestamp', 'N/A')})"):
                st.json(step["data"])
    
    # Add download button for complete logs
    st.download_button(
        label="Download Complete Logs",
        data=json.dumps(st.session_state.results, indent=2),
        file_name=f"complete_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )