"""
PDF Extractor Module
Extracts text and images from PrecisionPlus V3™ MRI reports
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from io import BytesIO

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class PDFExtractor:
    """
    Extracts content from PrecisionPlus V3™ MRI report PDFs
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.temp_dir = tempfile.mkdtemp()
        
    def extract_all(self) -> Dict[str, Any]:
        """Extract all content from the PDF"""
        result = {
            'patient_explanation': self._extract_patient_explanation(),
            'images': self._extract_images(),
            'metadata': self._extract_metadata()
        }
        return result
    
    def _extract_patient_explanation(self) -> str:
        """Extract the Simplified Patient Explanation text from pages 12-13"""
        text = ""
        
        if pdfplumber:
            try:
                with pdfplumber.open(self.pdf_path) as pdf:
                    # Pages are 0-indexed, so pages 12-13 are indices 11-12
                    for page_num in range(11, min(13, len(pdf.pages))):
                        page = pdf.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                print(f"pdfplumber extraction failed: {e}")
        
        # Clean up the extracted text
        text = self._clean_patient_explanation(text)
        return text
    
    def _clean_patient_explanation(self, text: str) -> str:
        """Clean and format the extracted patient explanation text"""
        if not text:
            return ""
        
        # 1. Remove specific phrases/sections
        remove_phrases = [
            "Not a substitute for the Expert Radiology radiologist's report",
            "MRI of the Lumbar Spine",
            "Technique: MRI images were taken without using contrast dye.",
            "Comparison: No previous MRI scans are available for comparison.",
            "Findings:",
            "Simplified Patient Explanation",
            "of Radiologist's Report*"
        ]
        
        for phrase in remove_phrases:
            text = text.replace(phrase, "")
            
        # 2. Remove "Reason for MRI" lines (using regex since dates change)
        text = re.sub(r"Reason for MRI:.*?(?=\n)", "", text, flags=re.IGNORECASE)
        
        # 3. General formatting cleanup
        lines = text.split('\n')
        cleaned_lines = []
        
        skip_patterns = [
            r'^Patient ID:',
            r'^Patient Name:',
            r'^Date:',
            r'^Page \d+ of \d+',
            r'^_+$',
            r'^\s*$',
        ]
        
        for line in lines:
            should_skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line.strip()):
                    should_skip = True
                    break
            
            if not should_skip:
                cleaned_lines.append(line)
        
        # Join and clean up whitespace
        text = '\n'.join(cleaned_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\[\d+\]', '', text)
        
        return text.strip()
    
    def _extract_images(self) -> List[Dict[str, Any]]:
        """Extract key images from the PDF"""
        images = []
        target_pages = [3, 4, 5, 6, 9, 10]
        
        if fitz:
            images = self._extract_images_fitz(target_pages)
        
        if not images and convert_from_path:
            images = self._extract_images_pdf2image(target_pages)
        
        for img in images:
            img['description'] = self._get_image_description(img.get('page', 0))
        
        return images
    
    def _extract_images_fitz(self, target_pages: List[int]) -> List[Dict[str, Any]]:
        """Extract images using PyMuPDF (fitz)"""
        images = []
        try:
            doc = fitz.open(self.pdf_path)
            
            for page_num in target_pages:
                if page_num >= len(doc): continue
                page = doc[page_num]
                
                # --- REVERTED LOGIC: Priority 1 is extracting embedded images ---
                image_list = page.get_images()
                found_embedded = False
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Filter out tiny icons/logos (often < 5KB)
                        if len(image_bytes) < 5000:
                            continue

                        pil_image = Image.open(BytesIO(image_bytes))
                        
                        # Save to temp file
                        img_path = os.path.join(
                            self.temp_dir, 
                            f"page_{page_num+1}_img_{img_index}.png"
                        )
                        pil_image.save(img_path)
                        
                        images.append({
                            'page': page_num + 1,
                            'image': pil_image,
                            'path': img_path,
                            'type': 'embedded'
                        })
                        found_embedded = True
                    except Exception as e:
                        print(f"Failed to extract image {img_index} from page {page_num}: {e}")
                
                # --- Priority 2: Fallback to full page render ONLY if no images found ---
                if not found_embedded:
                    try:
                        mat = fitz.Matrix(2, 2)
                        pix = page.get_pixmap(matrix=mat)
                        img_path = os.path.join(self.temp_dir, f"page_{page_num+1}_full.png")
                        pix.save(img_path)
                        pil_image = Image.open(img_path)
                        
                        images.append({
                            'page': page_num + 1,
                            'image': pil_image,
                            'path': img_path,
                            'type': 'rendered'
                        })
                    except Exception as e:
                        print(f"Failed to render page {page_num}: {e}")
            doc.close()
            
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
        
        return images
    
    def _extract_images_pdf2image(self, target_pages: List[int]) -> List[Dict[str, Any]]:
        """Extract images using pdf2image (renders pages)"""
        images = []
        try:
            for page_num in target_pages:
                try:
                    page_images = convert_from_path(
                        self.pdf_path,
                        first_page=page_num + 1,
                        last_page=page_num + 1,
                        dpi=150
                    )
                    for img in page_images:
                        img_path = os.path.join(self.temp_dir, f"page_{page_num+1}.png")
                        img.save(img_path)
                        images.append({
                            'page': page_num + 1,
                            'image': img,
                            'path': img_path,
                            'type': 'rendered'
                        })
                except Exception as e:
                    print(f"Failed to convert page {page_num}: {e}")
        except Exception as e:
            print(f"pdf2image extraction failed: {e}")
        return images
    
    def _get_image_description(self, page_num: int) -> str:
        """Get description based on page number"""
        descriptions = {
            4: "Figure 1: Sagittal T2 MRI",
            5: "Figure 2: Sagittal T2 MRI Findings",
            6: "Figure 3: Sagittal T2 MRI Foraminal",
            7: "Figure 4: Axial T2 MRI",
            10: "Spine Illustration - Sagittal",
            11: "Spine Illustration - Axial"
        }
        return descriptions.get(page_num, f"MRI Image - Page {page_num}")
    
    def _extract_metadata(self) -> Dict[str, str]:
        return {}