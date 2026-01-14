"""
API Clients Module
Handles communication with ElevenLabs and HeyGen APIs
"""

import os
import time
import tempfile
import requests
from typing import Optional, Dict, Any
from pathlib import Path


class ElevenLabsClient:
    """Client for ElevenLabs Text-to-Speech API"""
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    # Default model - multilingual v2 for high quality
    DEFAULT_MODEL = "eleven_multilingual_v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        self.temp_dir = tempfile.mkdtemp()
    
    def test_connection(self) -> bool:
        """Test API connection by fetching voices"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/voices",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"ElevenLabs connection test failed: {e}")
            return False
    
    def get_voices(self) -> list:
        """Get list of available voices"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/voices",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('voices', [])
            else:
                print(f"Failed to get voices: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting voices: {e}")
            return []
    
    def generate_speech(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        output_format: str = "mp3_44100_128"
    ) -> Optional[str]:
        """
        Generate speech from text
        
        Args:
            text: The text to convert to speech
            voice_id: ElevenLabs voice ID
            speed: Speech speed multiplier (0.5 - 2.0)
            output_format: Audio output format
        
        Returns:
            Path to the generated audio file, or None if failed
        """
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
        
        # Voice settings for natural speech
        voice_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        payload = {
            "text": text,
            "model_id": self.DEFAULT_MODEL,
            "voice_settings": voice_settings
        }
        
        # Add output format if specified
        params = {"output_format": output_format}
        
        try:
            print(f"Generating speech for {len(text)} characters...")
            
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                params=params,
                timeout=120  # Longer timeout for long text
            )
            
            if response.status_code == 200:
                # Save audio to file
                audio_path = os.path.join(self.temp_dir, "narration.mp3")
                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"Audio saved to: {audio_path}")
                return audio_path
            else:
                print(f"Speech generation failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error generating speech: {e}")
            return None
    
    def get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds"""
        try:
            from mutagen.mp3 import MP3
            audio = MP3(audio_path)
            return audio.info.length
        except ImportError:
            # Fallback: estimate from file size
            # MP3 at 128kbps ≈ 16KB per second
            file_size = os.path.getsize(audio_path)
            return file_size / 16000
        except Exception as e:
            print(f"Error getting audio duration: {e}")
            return 60.0  # Default fallback


class HeyGenClient:
    """Client for HeyGen Avatar Video API"""
    
    BASE_URL = "https://api.heygen.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        self.temp_dir = tempfile.mkdtemp()
    
    def test_connection(self) -> bool:
        """Test API connection by checking quota"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/v2/user/remaining_quota",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"HeyGen connection test failed: {e}")
            return False
    
    def get_avatars(self) -> list:
        """Get list of available avatars"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/v2/avatars",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('avatars', [])
            else:
                print(f"Failed to get avatars: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting avatars: {e}")
            return []
    
    def get_voices(self) -> list:
        """Get list of available HeyGen voices"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/v2/voices",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('voices', [])
            else:
                print(f"Failed to get voices: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting voices: {e}")
            return []
    
    def upload_audio(self, audio_path: str) -> Optional[str]:
        """
        Upload audio file to HeyGen and get asset URL
        
        Returns:
            Asset URL for use in video generation
        """
        upload_url = f"{self.BASE_URL}/v1/asset"
        
        try:
            with open(audio_path, 'rb') as f:
                files = {'file': ('narration.mp3', f, 'audio/mpeg')}
                headers = {"X-Api-Key": self.api_key}
                
                response = requests.post(
                    upload_url,
                    files=files,
                    headers=headers,
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('data', {}).get('url')
                else:
                    print(f"Upload failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error uploading audio: {e}")
            return None
    
    def generate_avatar_video(
        self,
        text: str,
        avatar_id: str,
        voice_id: Optional[str] = None,
        audio_url: Optional[str] = None,
        width: int = 1280,
        height: int = 720,
        background_color: str = "#ffffff"
    ) -> Optional[str]:
        """
        Generate avatar video using HeyGen API v2
        
        Args:
            text: Script for the avatar to speak
            avatar_id: HeyGen avatar ID
            voice_id: Voice ID (optional if using audio_url)
            audio_url: Pre-uploaded audio URL (optional)
            width: Video width
            height: Video height
            background_color: Background color hex code
        
        Returns:
            Path to downloaded video file, or None if failed
        """
        url = f"{self.BASE_URL}/v2/video/generate"
        
        # Build video input
        video_input = {
            "character": {
                "type": "avatar",
                "avatar_id": avatar_id,
                "avatar_style": "normal"
            },
            "background": {
                "type": "color",
                "value": background_color
            }
        }
        
        # Voice configuration
        if audio_url:
            # Use uploaded audio
            video_input["voice"] = {
                "type": "audio",
                "audio_url": audio_url
            }
        elif voice_id:
            # Use text-to-speech with voice ID
            video_input["voice"] = {
                "type": "text",
                "input_text": text,
                "voice_id": voice_id,
                "speed": 1.0
            }
        else:
            print("Error: Either voice_id or audio_url must be provided")
            return None
        
        payload = {
            "video_inputs": [video_input],
            "dimension": {
                "width": width,
                "height": height
            },
            "test": False  # Set to True for testing without consuming credits
        }
        
        try:
            print(f"Initiating video generation...")
            print(f"Avatar: {avatar_id}, Resolution: {width}x{height}")
            
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                video_id = data.get('data', {}).get('video_id')
                
                if video_id:
                    print(f"Video ID: {video_id}")
                    return self._wait_for_video(video_id)
                else:
                    print(f"No video_id in response: {data}")
                    return None
            else:
                print(f"Video generation failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error generating video: {e}")
            return None
    
    def _wait_for_video(
        self,
        video_id: str,
        max_wait: int = 600,
        poll_interval: int = 10
    ) -> Optional[str]:
        """
        Poll for video completion and download when ready
        
        Args:
            video_id: HeyGen video ID
            max_wait: Maximum wait time in seconds
            poll_interval: Time between status checks
        
        Returns:
            Path to downloaded video, or None if failed/timeout
        """
        url = f"{self.BASE_URL}/v1/video_status.get"
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    url,
                    params={"video_id": video_id},
                    headers=self.headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('data', {}).get('status')
                    
                    print(f"Video status: {status}")
                    
                    if status == 'completed':
                        video_url = data.get('data', {}).get('video_url')
                        if video_url:
                            return self._download_video(video_url)
                        else:
                            print("Video completed but no URL provided")
                            return None
                    
                    elif status == 'failed':
                        error = data.get('data', {}).get('error', 'Unknown error')
                        print(f"Video generation failed: {error}")
                        return None
                    
                    elif status in ['pending', 'processing']:
                        print(f"Video {status}, waiting...")
                        time.sleep(poll_interval)
                    
                    else:
                        print(f"Unknown status: {status}")
                        time.sleep(poll_interval)
                else:
                    print(f"Status check failed: {response.status_code}")
                    time.sleep(poll_interval)
                    
            except Exception as e:
                print(f"Error checking status: {e}")
                time.sleep(poll_interval)
        
        print(f"Timeout waiting for video after {max_wait} seconds")
        return None
    
    def _download_video(self, video_url: str) -> Optional[str]:
        """Download video from URL"""
        try:
            print(f"Downloading video...")
            
            response = requests.get(video_url, timeout=120, stream=True)
            
            if response.status_code == 200:
                video_path = os.path.join(self.temp_dir, "avatar_video.mp4")
                
                with open(video_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"Video downloaded to: {video_path}")
                return video_path
            else:
                print(f"Download failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error downloading video: {e}")
            return None
    
    def generate_webm_video(
        self,
        text: str,
        avatar_id: str,
        voice_id: str,
        width: int = 512,
        height: int = 512
    ) -> Optional[str]:
        """
        Generate WebM video with transparent background
        Useful for picture-in-picture composition
        """
        url = f"{self.BASE_URL}/v2/video/generate/webm"
        
        payload = {
            "avatar_id": avatar_id,
            "input_text": text,
            "voice_id": voice_id,
            "dimension": {
                "width": width,
                "height": height
            }
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                video_id = data.get('data', {}).get('video_id')
                
                if video_id:
                    return self._wait_for_video(video_id)
                    
            print(f"WebM generation failed: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"Error generating WebM: {e}")
            return None


# Test functions
def test_elevenlabs(api_key: str):
    """Test ElevenLabs connection and voice listing"""
    client = ElevenLabsClient(api_key)
    
    print("Testing ElevenLabs API...")
    
    if client.test_connection():
        print("✅ Connection successful!")
        
        voices = client.get_voices()
        print(f"\nAvailable voices ({len(voices)}):")
        for voice in voices[:10]:  # Show first 10
            print(f"  - {voice.get('name')}: {voice.get('voice_id')}")
    else:
        print("❌ Connection failed")


def test_heygen(api_key: str):
    """Test HeyGen connection and avatar listing"""
    client = HeyGenClient(api_key)
    
    print("Testing HeyGen API...")
    
    if client.test_connection():
        print("✅ Connection successful!")
        
        avatars = client.get_avatars()
        print(f"\nAvailable avatars ({len(avatars)}):")
        for avatar in avatars[:10]:  # Show first 10
            print(f"  - {avatar.get('avatar_name')}: {avatar.get('avatar_id')}")
    else:
        print("❌ Connection failed")


if __name__ == "__main__":
    import sys
    
    # Test with provided API keys
    ELEVENLABS_KEY = "sk_3b5043d68a91d1d461cc97cb01a28f644b7e0db2cc7c52d6"
    HEYGEN_KEY = "sk_V2_hgu_ktnQdm1avGm_ezvg7zsGoEVlGKbKrmJs6iaJCfDmNFw0"
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "elevenlabs":
            test_elevenlabs(ELEVENLABS_KEY)
        elif sys.argv[1] == "heygen":
            test_heygen(HEYGEN_KEY)
        else:
            print("Usage: python api_clients.py [elevenlabs|heygen]")
    else:
        test_elevenlabs(ELEVENLABS_KEY)
        print("\n" + "="*50 + "\n")
        test_heygen(HEYGEN_KEY)
