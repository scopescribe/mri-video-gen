"""
MRI Video Report Generator - Streamlit Application
Converts PrecisionPlus V3™ MRI reports into patient-friendly video explanations
"""

import os
import shutil
import streamlit as st
import time
import tempfile
import uuid  # <--- Added for unique IDs
from pathlib import Path

# --- Universal FFmpeg Fix ---
def configure_ffmpeg():
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        possible_paths = [
            "/usr/bin/ffmpeg",              # Streamlit Cloud
            "/usr/local/bin/ffmpeg",        # Intel Mac
            "/opt/homebrew/bin/ffmpeg",     # Apple Silicon Mac
        ]
        for path in possible_paths:
            if os.path.exists(path):
                ffmpeg_path = path
                break
    
    if ffmpeg_path:
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path

configure_ffmpeg()
# ---------------------------

from pdf_extractor import PDFExtractor
from api_clients import ElevenLabsClient, HeyGenClient
from video_composer import VideoComposer

# Configuration
try:
    ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
    HEYGEN_API_KEY = st.secrets["HEYGEN_API_KEY"]
    HEYGEN_AVATAR_ID = st.secrets["HEYGEN_AVATAR_ID"]
except:
    ELEVENLABS_API_KEY = "" 
    HEYGEN_API_KEY = ""
    HEYGEN_AVATAR_ID = "Abigail_standing_office_front"

ELEVENLABS_VOICES = {
    "Rachel (American Female)": "21m00Tcm4TlvDq8ikWAM",
    "Nicole (Whisper Female)": "piTKgcLEGmPE4e6mEKli",
    "Charlotte (British Female)": "XB0fDUnXU5powFXDhCwa",
    "Adam (Deep Male)": "pNInz6obpgDQGcFmaJgB",
    "Antoni (American Male)": "ErXwobaYiN019PkySvjV",
}

def main():
    st.set_page_config(page_title="MRI Video Gen", page_icon="🏥", layout="wide")
    st.title("🏥 MRI Video Report Generator")

    # --- UNIQUE SESSION MANAGEMENT ---
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    # Define unique filename for this specific user
    user_avatar_file = f"avatar_{st.session_state.session_id}.mp4"
    # ---------------------------------

    if 'extracted_content' not in st.session_state:
        st.session_state.extracted_content = None
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Audio Source
        audio_source = st.radio("Audio Source", ["HeyGen TTS (Recommended)", "ElevenLabs TTS"])
        
        if audio_source == "ElevenLabs TTS":
            selected_voice = st.selectbox("Select Voice", list(ELEVENLABS_VOICES.keys()))
        else:
            selected_voice = None

        # Check for THIS USER'S saved video
        if os.path.exists(user_avatar_file):
            st.success("💾 Found your cached avatar video!")
            if st.button("🗑️ Generate New (Delete Cache)"):
                os.remove(user_avatar_file)
                st.rerun()
        
        st.markdown("---")
        # Optional: Allow users to input their own keys on the live site
        with st.expander("Own API Keys (Optional)"):
            user_heygen = st.text_input("HeyGen Key", type="password")
            if user_heygen:
                st.session_state['custom_heygen_key'] = user_heygen

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
            text = content.get('patient_explanation', '')
            with st.expander("📝 Cleaned Script", expanded=False):
                st.text_area("Script text", value=text, height=150, label_visibility="collapsed")
            
            with st.expander("🖼️ Extracted Images", expanded=True):
                images = content.get('images', [])
                if images:
                    st.write(f"Found {len(images)} images")
                    cols = st.columns(3)
                    for i, img in enumerate(images):
                        with cols[i % 3]:
                            st.image(img['image'], caption=img.get('description', f"Image {i+1}"), width="stretch")
                else:
                    st.warning("No images found.")

    st.markdown("---")
    st.header("3. Generate Video")
    
    if st.session_state.extracted_content:
        if st.button("🎬 Generate Video"):
            # Pass the unique filename to the generator
            generate_video_pipeline(
                st.session_state.extracted_content, 
                audio_source, 
                selected_voice, 
                user_avatar_file
            )

def generate_video_pipeline(content, audio_source, selected_voice_name, user_avatar_file):
    status = st.empty()
    progress = st.progress(0)
    
    # 1. Check for UNIQUE local file
    if os.path.exists(user_avatar_file):
        status.info("♻️ Using your cached avatar video (Credits Saved!)")
        avatar_video_path = user_avatar_file
        progress.progress(50)
        time.sleep(1)
    else:
        # 2. Generate New
        status.text("Connecting to HeyGen...")
        
        # Use user key if provided, else use secret
        heygen_key = st.session_state.get('custom_heygen_key') or HEYGEN_API_KEY
        if not heygen_key:
            st.error("No API Key found. Please add it in the sidebar or secrets.")
            return

        client = HeyGenClient(heygen_key)
        
        text = content['patient_explanation'][:1800]
        voice_id = None
        
        if audio_source == "ElevenLabs TTS":
            # (ElevenLabs logic remains same...)
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
            
            status.text("Generating Avatar Video (this takes 2-5 mins)...")
            video_path = client.generate_avatar_video(
                text=text,
                avatar_id=HEYGEN_AVATAR_ID,
                audio_url=audio_url,
                width=1280, 
                height=720
            )
            
        else:
            status.text("Selecting HeyGen Female Voice...")
            voices = client.get_voices()
            
            for v in voices:
                if 'English' in v.get('language', '') and v.get('gender') == 'female':
                    voice_id = v.get('voice_id')
                    break
            
            if not voice_id and voices:
                voice_id = voices[0]['voice_id']

            status.text("Generating Avatar Video (this takes 2-5 mins)...")
            video_path = client.generate_avatar_video(
                text=text,
                avatar_id=HEYGEN_AVATAR_ID,
                voice_id=voice_id,
                width=1280,
                height=720
            )
        
        if not video_path:
            st.error("Video generation failed.")
            return

        # Save with UNIQUE filename
        shutil.copy(video_path, user_avatar_file)
        avatar_video_path = user_avatar_file
        progress.progress(50)
    
    # 3. Compose
    status.text("Composing with FFmpeg...")
    composer = VideoComposer()
    images = content.get('images', [])[:3]
    
    final_path = composer.create_pip_video(
        avatar_video_path=avatar_video_path,
        images=images,
        output_path=f"output_{st.session_state.session_id}.mp4", # Unique output too
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