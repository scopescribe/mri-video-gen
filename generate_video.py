#!/usr/bin/env python3
"""
MRI Video Report Generator - Standalone Test Script
This script demonstrates the complete workflow without the Streamlit UI.
Useful for testing and debugging the core functionality.
"""

import os
import sys
import argparse
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_extractor import PDFExtractor
from api_clients import ElevenLabsClient, HeyGenClient
from video_composer import VideoComposer


# Configuration
ELEVENLABS_API_KEY = "sk_3b5043d68a91d1d461cc97cb01a28f644b7e0db2cc7c52d6"
HEYGEN_API_KEY = "sk_V2_hgu_ktnQdm1avGm_ezvg7zsGoEVlGKbKrmJs6iaJCfDmNFw0"
HEYGEN_AVATAR_ID = "Armando_Sweater_Front2_public"

# Default ElevenLabs voice (Adam - Deep Male)
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"


def extract_pdf_content(pdf_path: str, verbose: bool = True):
    """Extract content from MRI report PDF"""
    print("\n" + "="*60)
    print("STEP 1: Extracting PDF Content")
    print("="*60)
    
    extractor = PDFExtractor(pdf_path)
    content = extractor.extract_all()
    
    if verbose:
        print(f"\n✅ Extracted {len(content.get('patient_explanation', ''))} characters of text")
        print(f"✅ Found {len(content.get('images', []))} images")
        
        if content.get('metadata'):
            print(f"✅ Metadata: {content['metadata']}")
    
    return content


def generate_audio(text: str, voice_id: str = DEFAULT_VOICE_ID, verbose: bool = True):
    """Generate audio narration using ElevenLabs"""
    print("\n" + "="*60)
    print("STEP 2: Generating Audio Narration")
    print("="*60)
    
    client = ElevenLabsClient(ELEVENLABS_API_KEY)
    
    # Test connection
    if verbose:
        print("Testing ElevenLabs connection...")
    
    if not client.test_connection():
        print("❌ ElevenLabs API connection failed!")
        return None
    
    if verbose:
        print("✅ ElevenLabs connected")
        print(f"Generating speech for {len(text)} characters...")
    
    audio_path = client.generate_speech(
        text=text,
        voice_id=voice_id,
        speed=1.0
    )
    
    if audio_path:
        print(f"✅ Audio saved to: {audio_path}")
        
        # Get duration
        duration = client.get_audio_duration(audio_path)
        print(f"✅ Audio duration: {duration:.1f} seconds")
    else:
        print("❌ Audio generation failed!")
    
    return audio_path


def generate_avatar_video(
    text: str,
    avatar_id: str = HEYGEN_AVATAR_ID,
    width: int = 1280,
    height: int = 720,
    verbose: bool = True
):
    """Generate avatar video using HeyGen"""
    print("\n" + "="*60)
    print("STEP 3: Generating Avatar Video")
    print("="*60)
    
    client = HeyGenClient(HEYGEN_API_KEY)
    
    # Test connection
    if verbose:
        print("Testing HeyGen connection...")
    
    if not client.test_connection():
        print("❌ HeyGen API connection failed!")
        return None
    
    if verbose:
        print("✅ HeyGen connected")
        print(f"Avatar: {avatar_id}")
        print(f"Resolution: {width}x{height}")
        print("Generating video (this may take several minutes)...")
    
    # Get a HeyGen voice
    voices = client.get_voices()
    heygen_voice_id = None
    
    # Find an English male voice
    for voice in voices:
        if voice.get('language') == 'English' and voice.get('gender') == 'male':
            heygen_voice_id = voice.get('voice_id')
            if verbose:
                print(f"Using HeyGen voice: {voice.get('name')} ({heygen_voice_id})")
            break
    
    if not heygen_voice_id and voices:
        heygen_voice_id = voices[0].get('voice_id')
        if verbose:
            print(f"Using first available voice: {heygen_voice_id}")
    
    video_path = client.generate_avatar_video(
        text=text,
        avatar_id=avatar_id,
        voice_id=heygen_voice_id,
        width=width,
        height=height
    )
    
    if video_path:
        print(f"✅ Video saved to: {video_path}")
    else:
        print("❌ Video generation failed!")
    
    return video_path


def compose_final_video(
    avatar_video_path: str,
    images: list,
    audio_path: str = None,
    output_path: str = "output_video.mp4",
    width: int = 1280,
    height: int = 720,
    verbose: bool = True
):
    """Compose final video with picture-in-picture"""
    print("\n" + "="*60)
    print("STEP 4: Composing Final Video")
    print("="*60)
    
    composer = VideoComposer()
    
    if verbose:
        print(f"Avatar video: {avatar_video_path}")
        print(f"Images: {len(images)}")
        print(f"Output: {output_path}")
    
    final_path = composer.create_pip_video(
        avatar_video_path=avatar_video_path,
        images=images,
        audio_path=audio_path,
        output_path=output_path,
        width=width,
        height=height,
        avatar_size=(320, 240),
        avatar_position="bottom_right",
        transition_type="crossfade",
        transition_duration=0.5
    )
    
    if final_path:
        print(f"✅ Final video saved to: {final_path}")
    else:
        print("❌ Video composition failed!")
    
    return final_path


def run_full_pipeline(
    pdf_path: str,
    output_path: str = "mri_explanation_video.mp4",
    skip_apis: bool = False,
    verbose: bool = True
):
    """Run the complete video generation pipeline"""
    print("\n" + "="*60)
    print("MRI VIDEO REPORT GENERATOR")
    print("="*60)
    print(f"Input PDF: {pdf_path}")
    print(f"Output: {output_path}")
    
    # Step 1: Extract PDF content
    content = extract_pdf_content(pdf_path, verbose)
    
    if not content.get('patient_explanation'):
        print("❌ No patient explanation text found in PDF!")
        return None
    
    text = content['patient_explanation']
    images = content.get('images', [])[:3]  # Use first 3 images
    
    if skip_apis:
        print("\n⚠️ Skipping API calls (--skip-apis flag set)")
        print("Extracted content preview:")
        print("-" * 40)
        print(text[:500] + "...")
        print("-" * 40)
        print(f"Images available: {len(images)}")
        for img in images:
            print(f"  - {img.get('description', 'No description')}")
        return None
    
    # Step 2: Generate audio
    audio_path = generate_audio(text, verbose=verbose)
    
    # Step 3: Generate avatar video
    avatar_video_path = generate_avatar_video(text, verbose=verbose)
    
    if not avatar_video_path:
        print("❌ Cannot proceed without avatar video!")
        return None
    
    # Step 4: Compose final video
    final_path = compose_final_video(
        avatar_video_path=avatar_video_path,
        images=images,
        audio_path=audio_path,
        output_path=output_path,
        verbose=verbose
    )
    
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    
    if final_path:
        print(f"✅ Video successfully created: {final_path}")
        file_size = os.path.getsize(final_path) / (1024 * 1024)
        print(f"   File size: {file_size:.1f} MB")
    else:
        print("❌ Video generation failed!")
    
    return final_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate patient-friendly MRI explanation videos"
    )
    parser.add_argument(
        "pdf_path",
        help="Path to the PrecisionPlus V3™ MRI report PDF"
    )
    parser.add_argument(
        "-o", "--output",
        default="mri_explanation_video.mp4",
        help="Output video file path"
    )
    parser.add_argument(
        "--skip-apis",
        action="store_true",
        help="Skip API calls (for testing PDF extraction only)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    parser.add_argument(
        "--test-elevenlabs",
        action="store_true",
        help="Test ElevenLabs API connection only"
    )
    parser.add_argument(
        "--test-heygen",
        action="store_true",
        help="Test HeyGen API connection only"
    )
    
    args = parser.parse_args()
    
    # API tests
    if args.test_elevenlabs:
        print("Testing ElevenLabs API...")
        client = ElevenLabsClient(ELEVENLABS_API_KEY)
        if client.test_connection():
            print("✅ ElevenLabs API connected!")
            voices = client.get_voices()
            print(f"\nAvailable voices: {len(voices)}")
            for v in voices[:5]:
                print(f"  - {v.get('name')}: {v.get('voice_id')}")
        else:
            print("❌ ElevenLabs API failed!")
        return
    
    if args.test_heygen:
        print("Testing HeyGen API...")
        client = HeyGenClient(HEYGEN_API_KEY)
        if client.test_connection():
            print("✅ HeyGen API connected!")
            avatars = client.get_avatars()
            print(f"\nAvailable avatars: {len(avatars)}")
            for a in avatars[:5]:
                print(f"  - {a.get('avatar_name')}: {a.get('avatar_id')}")
        else:
            print("❌ HeyGen API failed!")
        return
    
    # Validate input
    if not os.path.exists(args.pdf_path):
        print(f"❌ PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Run pipeline
    result = run_full_pipeline(
        pdf_path=args.pdf_path,
        output_path=args.output,
        skip_apis=args.skip_apis,
        verbose=not args.quiet
    )
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
