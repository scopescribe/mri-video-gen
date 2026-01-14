"""
Video Composer Module
Creates picture-in-picture video with avatar and MRI images
Compatible with MoviePy 2.x
"""

import os
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# MoviePy 2.x imports
MOVIEPY_AVAILABLE = False
MOVIEPY_VERSION = 0

try:
    # MoviePy 2.x - use simple import
    from moviepy import *
    MOVIEPY_AVAILABLE = True
    MOVIEPY_VERSION = 2
    print(f"MoviePy 2.x loaded successfully")
except ImportError as e:
    print(f"MoviePy 2.x import failed: {e}")
    try:
        # Fallback to MoviePy 1.x
        from moviepy.editor import (
            VideoFileClip, ImageClip, AudioFileClip,
            CompositeVideoClip, concatenate_videoclips,
            ColorClip, TextClip
        )
        from moviepy.video.fx.all import resize, fadein, fadeout
        MOVIEPY_AVAILABLE = True
        MOVIEPY_VERSION = 1
        print(f"MoviePy 1.x loaded successfully")
    except ImportError as e2:
        print(f"Warning: moviepy not available. Video composition will be limited. Error: {e2}")

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


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
        """
        Create picture-in-picture video
        """
        if MOVIEPY_AVAILABLE:
            return self._create_with_moviepy(
                avatar_video_path, images, audio_path, output_path,
                width, height, avatar_size, avatar_position,
                transition_type, transition_duration
            )
        elif CV2_AVAILABLE:
            return self._create_with_opencv(
                avatar_video_path, images, audio_path, output_path,
                width, height, avatar_size, avatar_position
            )
        else:
            print("Error: Neither moviepy nor opencv available for video composition")
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
            
            print(f"Avatar video duration: {total_duration:.1f}s")
            
            # Resize avatar for picture-in-picture
            avatar_w, avatar_h = avatar_size
            
            if MOVIEPY_VERSION == 2:
                avatar_clip = avatar_clip.resized((avatar_w, avatar_h))
            else:
                avatar_clip = avatar_clip.resize((avatar_w, avatar_h))
            
            # Calculate avatar position
            pos_x, pos_y = self._get_position(
                avatar_position, width, height, avatar_w, avatar_h
            )
            
            if MOVIEPY_VERSION == 2:
                avatar_clip = avatar_clip.with_position((pos_x, pos_y))
            else:
                avatar_clip = avatar_clip.set_position((pos_x, pos_y))
            
            # Process images
            if images:
                image_clips = self._create_image_clips(
                    images, total_duration, width, height, transition_duration
                )
            else:
                # Create a simple background if no images
                bg_clip = ColorClip(size=(width, height), color=(240, 240, 245))
                if MOVIEPY_VERSION == 2:
                    bg_clip = bg_clip.with_duration(total_duration)
                else:
                    bg_clip = bg_clip.set_duration(total_duration)
                image_clips = [bg_clip]
            
            # Composite all layers
            background = self._compose_images_with_transitions(
                image_clips, total_duration, transition_type, transition_duration
            )
            
            # Combine background and avatar
            final_clip = CompositeVideoClip(
                [background, avatar_clip],
                size=(width, height)
            )
            
            # Add audio if provided separately
            if audio_path and os.path.exists(audio_path):
                audio_clip = AudioFileClip(audio_path)
                if MOVIEPY_VERSION == 2:
                    final_clip = final_clip.with_audio(audio_clip)
                else:
                    final_clip = final_clip.set_audio(audio_clip)
            
            # Write output
            print(f"Writing video to {output_path}...")
            
            # --- UPDATED: Removed verbose=False which caused the error ---
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=30,
                preset='medium',
                threads=4,
                logger=None  # Keep logger=None to suppress progress bars if needed
            )
            
            # Clean up
            avatar_clip.close()
            final_clip.close()
            
            print(f"✅ Video created: {output_path}")
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
        height: int,
        transition_duration: float
    ) -> List[Any]:
        """Create image clips from image data"""
        clips = []
        
        # Calculate duration per image
        num_images = len(images)
        duration_per_image = total_duration / num_images
        
        for idx, img_data in enumerate(images):
            try:
                # Get image (either PIL Image or path)
                if 'path' in img_data and os.path.exists(img_data['path']):
                    img_path = img_data['path']
                elif 'image' in img_data:
                    # Save PIL image to temp file
                    img_path = os.path.join(self.temp_dir, f"image_{idx}.png")
                    img_data['image'].save(img_path)
                else:
                    continue
                
                # Create image clip
                clip = ImageClip(img_path)
                
                # Resize to fit while maintaining aspect ratio
                clip = self._resize_to_fit(clip, width, height)
                
                # Set duration and start time (MoviePy 2.x uses with_* methods)
                if MOVIEPY_VERSION == 2:
                    clip = clip.with_duration(duration_per_image)
                    clip = clip.with_start(idx * duration_per_image)
                else:
                    clip = clip.set_duration(duration_per_image)
                    clip = clip.set_start(idx * duration_per_image)
                
                clips.append(clip)
                
            except Exception as e:
                print(f"Error processing image {idx}: {e}")
        
        return clips
    
    def _resize_to_fit(self, clip, target_width: int, target_height: int):
        """Resize clip to fit within target dimensions while maintaining aspect ratio"""
        original_w, original_h = clip.size
        
        # Calculate scaling factor
        scale_w = target_width / original_w
        scale_h = target_height / original_h
        scale = min(scale_w, scale_h)
        
        new_w = int(original_w * scale)
        new_h = int(original_h * scale)
        
        # Resize based on version
        if MOVIEPY_VERSION == 2:
            resized = clip.resized((new_w, new_h))
        else:
            resized = clip.resize((new_w, new_h))
        
        # Center on canvas
        x_offset = (target_width - new_w) // 2
        y_offset = (target_height - new_h) // 2
        
        # Create background and composite
        background = ColorClip(
            size=(target_width, target_height),
            color=(240, 240, 245)
        )
        
        if MOVIEPY_VERSION == 2:
            background = background.with_duration(clip.duration if clip.duration else 1)
            resized = resized.with_position((x_offset, y_offset))
        else:
            background = background.set_duration(clip.duration if clip.duration else 1)
            resized = resized.set_position((x_offset, y_offset))
        
        return CompositeVideoClip([background, resized], size=(target_width, target_height))
    
    def _compose_images_with_transitions(
        self,
        clips: List[Any],
        total_duration: float,
        transition_type: str,
        transition_duration: float
    ) -> Any:
        """Compose image clips with transitions"""
        if not clips:
            bg = ColorClip(size=(1280, 720), color=(240, 240, 245))
            if MOVIEPY_VERSION == 2:
                return bg.with_duration(total_duration)
            else:
                return bg.set_duration(total_duration)
        
        if len(clips) == 1:
            if MOVIEPY_VERSION == 2:
                return clips[0].with_duration(total_duration)
            else:
                return clips[0].set_duration(total_duration)
        
        return CompositeVideoClip(clips, size=clips[0].size)
    
    def _get_position(
        self,
        position: str,
        canvas_width: int,
        canvas_height: int,
        element_width: int,
        element_height: int,
        margin: int = 20
    ) -> Tuple[int, int]:
        """Calculate position coordinates for element placement"""
        positions = {
            "bottom_right": (
                canvas_width - element_width - margin,
                canvas_height - element_height - margin
            ),
            "bottom_left": (
                margin,
                canvas_height - element_height - margin
            ),
            "top_right": (
                canvas_width - element_width - margin,
                margin
            ),
            "top_left": (
                margin,
                margin
            ),
            "center": (
                (canvas_width - element_width) // 2,
                (canvas_height - element_height) // 2
            ),
            "bottom_center": (
                (canvas_width - element_width) // 2,
                canvas_height - element_height - margin
            )
        }
        
        return positions.get(position, positions["bottom_right"])
    
    def _create_with_opencv(
        self,
        avatar_video_path: str,
        images: List[Dict[str, Any]],
        audio_path: Optional[str],
        output_path: str,
        width: int,
        height: int,
        avatar_size: Tuple[int, int],
        avatar_position: str
    ) -> Optional[str]:
        """Create video using OpenCV (fallback method)"""
        try:
            print("Creating video with OpenCV...")
            
            # Open avatar video
            avatar_cap = cv2.VideoCapture(avatar_video_path)
            fps = avatar_cap.get(cv2.CAP_PROP_FPS) or 30
            total_frames = int(avatar_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Prepare output
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # Prepare images
            prepared_images = self._prepare_images_opencv(images, width, height)
            
            # Calculate frame ranges for each image
            frames_per_image = total_frames // max(len(prepared_images), 1)
            
            avatar_w, avatar_h = avatar_size
            pos_x, pos_y = self._get_position(
                avatar_position, width, height, avatar_w, avatar_h
            )
            
            frame_idx = 0
            while True:
                ret, avatar_frame = avatar_cap.read()
                if not ret:
                    break
                
                # Determine which background image to use
                if prepared_images:
                    img_idx = min(frame_idx // frames_per_image, len(prepared_images) - 1)
                    background = prepared_images[img_idx].copy()
                else:
                    background = np.full((height, width, 3), 240, dtype=np.uint8)
                
                # Resize avatar frame
                avatar_resized = cv2.resize(avatar_frame, (avatar_w, avatar_h))
                
                # Overlay avatar on background
                background[pos_y:pos_y+avatar_h, pos_x:pos_x+avatar_w] = avatar_resized
                
                out.write(background)
                frame_idx += 1
            
            avatar_cap.release()
            out.release()
            
            # Add audio if available
            if audio_path:
                self._add_audio_opencv(output_path, audio_path)
            
            print(f"✅ Video created: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error creating video with OpenCV: {e}")
            return None
    
    def _prepare_images_opencv(
        self,
        images: List[Dict[str, Any]],
        width: int,
        height: int
    ) -> List[Any]:
        """Prepare images for OpenCV composition"""
        import numpy as np
        
        prepared = []
        
        for img_data in images:
            try:
                if 'path' in img_data and os.path.exists(img_data['path']):
                    img = cv2.imread(img_data['path'])
                elif 'image' in img_data:
                    # Convert PIL to OpenCV
                    pil_img = img_data['image']
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                else:
                    continue
                
                # Resize to fit
                h, w = img.shape[:2]
                scale = min(width / w, height / h)
                new_w, new_h = int(w * scale), int(h * scale)
                
                resized = cv2.resize(img, (new_w, new_h))
                
                # Center on canvas
                canvas = np.full((height, width, 3), 240, dtype=np.uint8)
                x_offset = (width - new_w) // 2
                y_offset = (height - new_h) // 2
                canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
                
                prepared.append(canvas)
                
            except Exception as e:
                print(f"Error preparing image: {e}")
        
        return prepared