# MRI Video Report Generator

Transform PrecisionPlus V3™ MRI reports into patient-friendly video explanations with an AI avatar.

![Demo](https://via.placeholder.com/800x400?text=MRI+Video+Report+Generator)

## 🎯 Features

- **PDF Upload**: Accept PrecisionPlus V3™ MRI report PDFs
- **Content Extraction**: Automatically extract patient explanation text and key images
- **AI Voice**: Generate natural narration using ElevenLabs text-to-speech
- **Avatar Video**: Create talking avatar video using HeyGen
- **Picture-in-Picture**: Compose final video with MRI images and avatar overlay
- **Image Transitions**: Smooth transitions between images at logical points

## 📋 Requirements

### System Requirements
- Python 3.9 or higher
- poppler-utils (for PDF image extraction)
- ffmpeg (for video processing)

### Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils ffmpeg
```

**macOS:**
```bash
brew install poppler ffmpeg
```

**Windows:**
- Download poppler from: https://github.com/oschwartz10612/poppler-windows/releases
- Download ffmpeg from: https://ffmpeg.org/download.html
- Add both to your PATH

### Install Python Dependencies
```bash
pip install -r requirements.txt
```

## 🚀 Quick Start

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

4. **Open in browser:**
   Navigate to `http://localhost:8501`

5. **Upload your MRI PDF and generate video!**

## 📁 Project Structure

```
mri_video_app/
├── app.py              # Main Streamlit application
├── pdf_extractor.py    # PDF content extraction module
├── api_clients.py      # ElevenLabs & HeyGen API clients
├── video_composer.py   # Video composition module
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🔧 Configuration

### API Keys
The application uses the following API keys (pre-configured in `app.py`):

- **ElevenLabs**: `sk_3b5043d68a91d1d461cc97cb01a28f644b7e0db2cc7c52d6`
- **HeyGen**: `sk_V2_hgu_ktnQdm1avGm_ezvg7zsGoEVlGKbKrmJs6iaJCfDmNFw0`
- **HeyGen Avatar ID**: `Armando_Sweater_Front2_public`

To use your own API keys, update the constants in `app.py`:
```python
ELEVENLABS_API_KEY = "your_elevenlabs_key"
HEYGEN_API_KEY = "your_heygen_key"
HEYGEN_AVATAR_ID = "your_avatar_id"
```

### Available Voices
The app includes several pre-configured ElevenLabs voices:
- Adam (Deep Male)
- Antoni (American Male)
- Arnold (American Male)
- Josh (Deep American)
- Sam (American Male)

## 📖 Usage Guide

### Step 1: Upload PDF
- Click "Upload PrecisionPlus V3™ PDF"
- Select your MRI report PDF file
- The app supports PrecisionPlus V3™ format reports

### Step 2: Extract Content
- Click "🔍 Extract Content"
- The app will extract:
  - Simplified Patient Explanation text (pages 12-13)
  - Key images (MRI scans and illustrations from pages 4-7, 10-11)

### Step 3: Preview & Select
- Review the extracted text in the preview area
- Select 2-3 images to include in the video

### Step 4: Generate Video
- Configure voice and video settings in the sidebar
- Click "🎬 Generate Video"
- Wait for processing (typically 2-5 minutes)

### Step 5: Download
- Preview the generated video
- Click "📥 Download Video" to save

## 🎬 Video Composition

The final video features:
- **Main Content**: Selected MRI images displayed prominently
- **Avatar Overlay**: Talking avatar in the bottom-right corner
- **Smooth Transitions**: Images transition at logical points in the narration
- **Professional Audio**: Natural-sounding AI narration

## 🔌 API Integration

### ElevenLabs Text-to-Speech
- Endpoint: `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
- Model: `eleven_multilingual_v2`
- Output: MP3 audio file

### HeyGen Avatar Video
- Endpoint: `POST https://api.heygen.com/v2/video/generate`
- Status check: `GET https://api.heygen.com/v1/video_status.get`
- Avatar: Armando_Sweater_Front2_public

## 🐛 Troubleshooting

### Common Issues

**"Failed to extract text from PDF"**
- Ensure the PDF is a valid PrecisionPlus V3™ report
- Check that pdfplumber is installed correctly

**"API connection failed"**
- Verify your API keys are correct
- Check your internet connection
- Ensure you have available credits on both APIs

**"Video generation timeout"**
- HeyGen video generation can take 2-10 minutes
- Check your HeyGen account for any quota limits

**"No images extracted"**
- Install PyMuPDF: `pip install PyMuPDF`
- Or install pdf2image: `pip install pdf2image`
- Ensure poppler-utils is installed

### Debug Mode
To see detailed logs, run:
```bash
streamlit run app.py --logger.level=debug
```

## 📝 PDF Structure Reference

PrecisionPlus V3™ reports follow this structure:
- **Pages 1-3**: Technical radiologist report
- **Pages 4-7**: Key MRI images with annotations (Figures 1-4)
- **Page 8**: Colorized comparison images
- **Page 9**: Radiologist credentials and photo
- **Pages 10-11**: Customized Spine Illustrations
- **Pages 12-13**: Simplified Patient Explanation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is for demonstration purposes. Please ensure you have appropriate licenses for:
- ElevenLabs API usage
- HeyGen API usage
- Any medical content handling

## 🔗 Resources

- [ElevenLabs API Documentation](https://elevenlabs.io/docs/api-reference/text-to-speech)
- [HeyGen API Documentation](https://docs.heygen.com/reference/create-an-avatar-video-v2)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [MoviePy Documentation](https://zulko.github.io/moviepy/)

## ⚠️ Disclaimer

This application is designed for educational and demonstration purposes. The generated videos should not be used as a substitute for professional medical advice. Always consult with qualified healthcare providers for medical decisions.
