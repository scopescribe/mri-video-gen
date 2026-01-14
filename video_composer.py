"""
Video Composer Module
Creates picture-in-picture video with avatar and MRI images
Compatible with MoviePy 1.x and 2.x
"""

import os
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# --- ROBUST IMPORT SECTION ---
MOVIEPY_AVAILABLE = False
MOVIEPY_VERSION = 0

try:
    # Attempt 1: MoviePy 2.x specific import
    from moviepy import VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip, ColorClip, TextClip
    MOVIEPY_AVAILABLE = True
    MOVIEPY_VERSION = 2
    print("✅ MoviePy 2.x loaded")
except ImportError:
    try:
        # Attempt 2: MoviePy 1.x (legacy) import
        from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip, ColorClip, TextClip
        MOVIEPY_AVAILABLE = True
        MOVIEPY_VERSION = 1
        print("✅ MoviePy 1.x loaded")
    except ImportError as e:
        print(f"❌ MoviePy import failed: {e}")

# OpenCV fallback imports
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class VideoComposer:
    """
    Composes final video with picture-in-picture layout
    """
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def create_pip_video(
        self,
        avatar_video_path: str,
        images: List[Dict[str, Any]],
        audio_path: Optional[str] = None,
        output_path: str = "output.mp4",
        width: int = 1280,
        height: int = 720,
        avatar_size: Tuple[int, int] = (320, 240),
        avatar_position: str = "bottom_right",
        transition_type: str = "crossfade",
        transition_duration: float = 0.5
    ) -> Optional[str]:
        
        if MOVIEPY_AVAILABLE:
            return self._create_with_moviepy(
                avatar_video_path, images, audio_path, output_path,
                width, height, avatar_size, avatar_position,
                transition_type, transition_duration
            )
        elif CV2_AVAILABLE:
            print("⚠️ MoviePy failed, falling back to OpenCV")
            return self._create_with_opencv(
                avatar_video_path, images, audio_path, output_path,
                width, height, avatar_size, avatar_position
            )
        else:
            print("❌ Error: Neither moviepy nor opencv available")
            return None
    
    def _create_with_moviepy(
        self,
        avatar_video_path: str,
        images: List[Dict[str, Any]],
        audio_path: Optional[str],
        output_path: str,
        width: int,
        height: int,
        avatar_size: Tuple[int, int],
        avatar_position: str,
        transition_type: str,
        transition_duration: float
    ) -> Optional[str]:
        """Create video using moviepy"""
        try:
            print(f"Creating video with moviepy (version {MOVIEPY_VERSION})...")
            
            # Load avatar video
            avatar_clip = VideoFileClip(avatar_video_path)
            total_duration = avatar_clip.duration
            
            # Resize avatar
            avatar_w, avatar_h = avatar_size
            if MOVIEPY_VERSION == 2:
                avatar_clip = avatar_clip.resized((avatar_w, avatar_h))
            else:
                avatar_clip = avatar_clip.resize((avatar_w, avatar_h))
            
            # Position avatar
            pos_x, pos_y = self._get_position(avatar_position, width, height, avatar_w, avatar_h)
            
            if MOVIEPY_VERSION == 2:
                avatar_clip = avatar_clip.with_position((pos_x, pos_y))
            else:
                avatar_clip = avatar_clip.set_position((pos_x, pos_y))
            
            # Process images
            if images:
                image_clips = self._create_image_clips(images, total_duration, width, height)
            else:
                # Background fallback
                bg_clip = ColorClip(size=(width, height), color=(240, 240, 245))
                if MOVIEPY_VERSION == 2:
                    bg_clip = bg_clip.with_duration(total_duration)
                else:
                    bg_clip = bg_clip.set_duration(total_duration)
                image_clips = [bg_clip]
            
            # Composite
            background = CompositeVideoClip(image_clips, size=(width, height))
            final_clip = CompositeVideoClip([background, avatar_clip], size=(width, height))
            
            # Add separate audio if provided
            if audio_path and os.path.exists(audio_path):
                audio_clip = AudioFileClip(audio_path)
                if MOVIEPY_VERSION == 2:
                    final_clip = final_clip.with_audio(audio_clip)
                else:
                    final_clip = final_clip.set_audio(audio_clip)
            
            # Write output
            print(f"Writing video to {output_path}...")
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=30,
                preset='medium',
                threads=4,
                logger=None 
            )
            
            avatar_clip.close()
            final_clip.close()
            return output_path
            
        except Exception as e:
            print(f"Error creating video with moviepy: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_image_clips(
        self,
        images: List[Dict[str, Any]],
        total_duration: float,
        width: int,
        height: int
    ) -> List[Any]:
        """Create image clips"""
        clips = []
        num_images = len(images)
        duration_per_image = total_duration / num_images
        
        for idx, img_data in enumerate(images):
            try:
                if 'path' in img_data and os.path.exists(img_data['path']):
                    img_path = img_data['path']
                elif 'image' in img_data:
                    img_path = os.path.join(self.temp_dir, f"image_{idx}.png")
                    img_data['image'].save(img_path)
                else:
                    continue
                
                clip = ImageClip(img_path)
                clip = self._resize_to_fit(clip, width, height)
                
                start_time = idx * duration_per_image
                
                if MOVIEPY_VERSION == 2:
                    clip = clip.with_duration(duration_per_image).with_start(start_time)
                else:
                    clip = clip.set_duration(duration_per_image).set_start(start_time)
                
                clips.append(clip)
            except Exception as e:
                print(f"Error processing image {idx}: {e}")
        
        return clips
    
    def _resize_to_fit(self, clip, target_width: int, target_height: int):
        original_w, original_h = clip.size
        scale = min(target_width / original_w, target_height / original_h)
        new_w, new_h = int(original_w * scale), int(original_h * scale)
        
        if MOVIEPY_VERSION == 2:
            resized = clip.resized((new_w, new_h))
        else:
            resized = clip.resize((new_w, new_h))
        
        x_off = (target_width - new_w) // 2
        y_off = (target_height - new_h) // 2
        
        bg = ColorClip(size=(target_width, target_height), color=(240, 240, 245))
        
        if MOVIEPY_VERSION == 2:
            bg = bg.with_duration(clip.duration if clip.duration else 1)
            resized = resized.with_position((x_off, y_off))
        else:
            bg = bg.set_duration(clip.duration if clip.duration else 1)
            resized = resized.set_position((x_off, y_off))
            
        return CompositeVideoClip([bg, resized], size=(target_width, target_height))

    def _get_position(self, position, cw, ch, ew, eh, margin=20):
        pos = {
            "bottom_right": (cw - ew - margin, ch - eh - margin),
            "bottom_left": (margin, ch - eh - margin),
            "top_right": (cw - ew - margin, margin),
            "top_left": (margin, margin)
        }
        return pos.get(position, pos["bottom_right"])

    # ... (Keep existing OpenCV methods if you want, but MoviePy usually works with above fix)
    def _create_with_opencv(self, *args, **kwargs):
        # Placeholder to prevent crash if moviepy fails completely
        return None