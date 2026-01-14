"""
MRI Video Report Generator - Streamlit Application
Converts PrecisionPlus V3™ MRI reports into patient-friendly video explanations
"""

import os
import shutil
import streamlit as st
import time
import tempfile
from pathlib import Path

# --- FFmpeg Fix for Mac (Hardcoded) ---
import os
# PASTE YOUR PATH HERE (From your previous step)
FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg" 

if os.path.exists(FFMPEG_PATH):
    # print(f"✅ Forced ffmpeg path: {FFMPEG_PATH}")
    os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH
else:
    # Fallback search if hardcoded path fails
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
# ---------------------------

from pdf_extractor import PDFExtractor
from api_clients import ElevenLabsClient, HeyGenClient
from video_composer import VideoComposer

# Configuration - UPDATED FOR CLOUD
# Try to get keys from Streamlit Secrets (Cloud), otherwise use empty string
try:
    ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
    HEYGEN_API_KEY = st.secrets["HEYGEN_API_KEY"]
    HEYGEN_AVATAR_ID = st.secrets["HEYGEN_AVATAR_ID"]
except:
    # Fallback for local testing if secrets.toml isn't set up
    ELEVENLABS_API_KEY = "" 
    HEYGEN_API_KEY = ""
    HEYGEN_AVATAR_ID = "Abigail_standing_office_front"

# Voices Configuration (Added Female Voices)
ELEVENLABS_VOICES = {
    "Rachel (American Female)": "21m00Tcm4TlvDq8ikWAM",
    "Nicole (Whisper Female)": "piTKgcLEGmPE4e6mEKli",
    "Charlotte (British Female)": "XB0fDUnXU5powFXDhCwa",
    "Adam (Deep Male)": "pNInz6obpgDQGcFmaJgB",
    "Antoni (American Male)": "ErXwobaYiN019PkySvjV",
}

def main():
    st.set_page_config(page_title="MRI Video Gen", page_icon="🏥", layout="wide")
    st.title("Expert Radiology Video Report Generator")

    if 'extracted_content' not in st.session_state:
        st.session_state.extracted_content = None
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        audio_source = st.radio("Audio Source", ["HeyGen TTS (Recommended)", "ElevenLabs TTS"])
        
        if audio_source == "ElevenLabs TTS":
            selected_voice = st.selectbox("Select Voice", list(ELEVENLABS_VOICES.keys()))
        else:
            selected_voice = None # HeyGen will auto-select female

        # Check for locally saved avatar video
        if os.path.exists("saved_avatar.mp4"):
            st.success("💾 Found 'saved_avatar.mp4'!")
            if st.button("🗑️ Delete Saved Video"):
                os.remove("saved_avatar.mp4")
                st.rerun()
        
        st.markdown("---")
        st.caption("API Keys")
        new_heygen_key = st.text_input("HeyGen Key", value=st.session_state.get('custom_heygen_key', ''), type="password")
        if st.button("Save Keys"):
            st.session_state['custom_heygen_key'] = new_heygen_key

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("1. Upload PDF")
        uploaded_file = st.file_uploader("Upload PrecisionPlus V3™ PDF", type=['pdf'])
        
        if uploaded_file and st.button("🔍 Extract Content"):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(uploaded_file.read())
                extractor = PDFExtractor(tmp.name)
                st.session_state.extracted_content = extractor.extract_all()
                st.success("Extracted!")

    with col2:
        st.header("2. Preview")
        if st.session_state.extracted_content:
            content = st.session_state.extracted_content
            
            # Script Preview
            text = content.get('patient_explanation', '')
            with st.expander("📝 Cleaned Script", expanded=False):
                st.text_area("Script text", value=text, height=150, label_visibility="collapsed")
            
            # --- RESTORED IMAGE GRID ---
            with st.expander("🖼️ Extracted Images", expanded=True):
                images = content.get('images', [])
                if images:
                    st.write(f"Found {len(images)} images")
                    # Create columns for the grid
                    cols = st.columns(3)
                    for i, img in enumerate(images):
                        with cols[i % 3]:
                            st.image(
                                img['image'],
                                caption=img.get('description', f"Image {i+1}"),
                                width="stretch" # Fills the column width
                            )
                else:
                    st.warning("No images found.")

    st.markdown("---")
    st.header("3. Generate Video")
    
    if st.session_state.extracted_content:
        if st.button("🎬 Generate Video"):
            generate_video_pipeline(st.session_state.extracted_content, audio_source, selected_voice)

def generate_video_pipeline(content, audio_source, selected_voice_name):
    status = st.empty()
    progress = st.progress(0)
    
    # 1. Check for existing local file to SAVE CREDITS
    if os.path.exists("saved_avatar.mp4"):
        status.info("♻️ Using existing 'saved_avatar.mp4' from disk (Credits Saved!)")
        avatar_video_path = "saved_avatar.mp4"
        progress.progress(50)
        time.sleep(1)
    else:
        # 2. Generate New
        status.text("Connecting to HeyGen...")
        heygen_key = st.session_state.get('custom_heygen_key') or HEYGEN_API_KEY
        client = HeyGenClient(heygen_key)
        
        text = content['patient_explanation'][:1800] # Safe limit
        
        voice_id = None
        
        # --- PATH A: ElevenLabs Audio ---
        if audio_source == "ElevenLabs TTS":
            eleven_key = ELEVENLABS_API_KEY
            el_client = ElevenLabsClient(eleven_key)
            el_voice_id = ELEVENLABS_VOICES[selected_voice_name]
            
            status.text(f"Generating audio with {selected_voice_name}...")
            audio_path = el_client.generate_speech(text, el_voice_id)
            
            if not audio_path:
                st.error("ElevenLabs audio generation failed.")
                return

            status.text("Uploading audio to HeyGen...")
            audio_url = client.upload_audio(audio_path)
            
            status.text("Generating Avatar Video (this takes 2-5 mins)...") # <--- STATUS UPDATE
            video_path = client.generate_avatar_video(
                text=text,
                avatar_id=HEYGEN_AVATAR_ID,
                audio_url=audio_url,
                width=1280, 
                height=720
            )
            
        # --- PATH B: HeyGen Internal Audio ---
        else:
            status.text("Selecting HeyGen Female Voice...")
            voices = client.get_voices()
            
            # Logic: Find English + Female voice
            for v in voices:
                if 'English' in v.get('language', '') and v.get('gender') == 'female':
                    voice_id = v.get('voice_id')
                    break
            
            # Fallback if logic fails
            if not voice_id and voices:
                voice_id = voices[0]['voice_id']

            # --- VITAL FIX: Update status so you know it's working ---
            status.text("Generating Avatar Video (this takes 2-5 mins)...") 
            
            video_path = client.generate_avatar_video(
                text=text,
                avatar_id=HEYGEN_AVATAR_ID,
                voice_id=voice_id,
                width=1280,
                height=720
            )
        
        if not video_path:
            st.error("Video generation failed. Please check the terminal for error details.")
            return

        shutil.copy(video_path, "saved_avatar.mp4")
        avatar_video_path = "saved_avatar.mp4"
        progress.progress(50)
    
    # 3. Compose
    status.text("Composing with FFmpeg...")
    composer = VideoComposer()
    images = content.get('images', [])[:3]
    
    final_path = composer.create_pip_video(
        avatar_video_path=avatar_video_path,
        images=images,
        output_path="final_output.mp4",
        width=1280,
        height=720
    )
    
    if final_path:
        progress.progress(100)
        status.success("Done!")
        st.video(final_path)
        with open(final_path, 'rb') as f:
            st.download_button("Download Video", f, "mri_video.mp4")
    else:
        st.error("Composition failed. Ensure ffmpeg is installed.")

if __name__ == "__main__":
    main()