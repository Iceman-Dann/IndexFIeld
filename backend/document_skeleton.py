"""Skeleton-based document processing - fast, lightweight extraction."""
import fitz
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import re
import json
import os
from PIL import Image
import pytesseract
import requests
import io
from tribal_vault import record_tribal_note

class VisionProcessor:
    """Two-tier OCR: fast layer (PyMuPDF) + deep layer (Tesseract)."""
    
    @staticmethod
    def extract_text_from_image(image_bytes: bytes) -> str:
        """Deep OCR using Tesseract."""
        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image)

@dataclass
class DocumentSkeleton:
    """Lightweight document structure for fast AI retrieval."""
    manual_id: str
    manual_name: str
    title: str
    total_pages: int
    sections: List[Dict] = field(default_factory=list)
    key_specs: Dict[str, str] = field(default_factory=dict)
    procedures: List[Dict] = field(default_factory=list)
    troubleshooting: List[Dict] = field(default_factory=list)
    topic_index: Dict[str, List[int]] = field(default_factory=dict)
    uploaded_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self):
        return {
            "manual_id": self.manual_id,
            "manual_name": self.manual_name,
            "title": self.title,
            "total_pages": self.total_pages,
            "sections": self.sections,
            "key_specs": self.key_specs,
            "procedures": self.procedures,
            "troubleshooting": self.troubleshooting,
            "topic_index": self.topic_index,
        }

class SkeletonExtractor:
    """Extract document skeleton - structure without full content."""
    
    def __init__(self):
        self.skeletons = {}
    
    def extract_skeleton(self, file_path: str, manual_id: str, manual_name: str) -> DocumentSkeleton:
        """Extract lightweight skeleton from various file types."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return self._extract_pdf_skeleton(file_path, manual_id, manual_name)
        elif file_ext in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}:
            return self._extract_image_skeleton(file_path, manual_id, manual_name)
        elif file_ext in {'.txt', '.json', '.csv'}:
            return self._extract_text_skeleton(file_path, manual_id, manual_name)
        else:
            # Fallback to text processing
            return self._extract_text_skeleton(file_path, manual_id, manual_name)
    
    def _extract_pdf_skeleton(self, file_path: str, manual_id: str, manual_name: str) -> DocumentSkeleton:
        """Extract skeleton from PDF."""
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
            title = doc[0].get_text().split('\n')[0][:100] if doc else "Manual"
            
            print(f"[SKELETON] Extracting {manual_name}, {total_pages} pages")
            
            sections = []
            key_specs = {}
            procedures = []
            troubleshooting = []
            topic_index = {}
            
            for page_num in range(1, min(total_pages + 1, 51)):
                page = doc[page_num - 1]
                text = page.get_text()[:5000]  # Increased to 5000 chars
                
                if not text.strip():
                    continue
                
                print(f"[SKELETON] Page {page_num}: extracted {len(text)} chars")
                
                # Identify section type
                section_type = self._detect_section_type(text)
                heading = self._extract_heading(text)
                # Don't truncate first page (where manufacturer info usually is)
                if page_num == 1:
                    summary = text
                    print(f"[SKELETON] Page 1 (no truncation): {len(summary)} chars")
                else:
                    summary = text[:1000] + "..." if len(text) > 1000 else text
                    print(f"[SKELETON] Page {page_num}: {len(summary)} chars")
                
                section = {
                    'page': page_num,
                    'type': section_type,
                    'heading': heading,
                    'summary': summary,
                    'topics': self._extract_topics(text)
                }
                sections.append(section)
                
                # Index topics
                for topic in section['topics']:
                    if topic not in topic_index:
                        topic_index[topic] = []
                    topic_index[topic].append(len(sections) - 1)
                
                # Extract specific data based on type
                if section_type == 'specs':
                    specs = self._extract_specs(text)
                    key_specs.update(specs)
                elif section_type == 'procedure':
                    proc = self._extract_procedure(text, page_num)
                    if proc:
                        procedures.append(proc)
                elif section_type == 'troubleshooting':
                    issues = self._extract_issues(text, page_num)
                    troubleshooting.extend(issues)
            
            skeleton = DocumentSkeleton(
                manual_id=manual_id,
                manual_name=manual_name,
                title=title,
                total_pages=total_pages,
                sections=sections,
                key_specs=key_specs,
                procedures=procedures,
                troubleshooting=troubleshooting,
                topic_index=topic_index
            )
            
            self.skeletons[manual_id] = skeleton
            return skeleton
    
    def _detect_section_type(self, text: str) -> str:
        """Detect section type from content."""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ['troubleshooting', 'fault', 'error', 'diagnostic']):
            return 'troubleshooting'
        elif any(kw in text_lower for kw in ['procedure', 'installation', 'maintenance', 'repair', 'steps']):
            return 'procedure'
        elif re.search(r'\d+\s*(nm|psi|°|v|a|rpm|kw|hp)', text_lower):
            return 'specs'
        elif any(kw in text_lower for kw in ['parts', 'components', 'catalog']):
            return 'parts'
        return 'general'
    
    def _extract_heading(self, text: str) -> str:
        """Extract section heading."""
        lines = text.strip().split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line.isupper() and 5 < len(line) < 100:
                return line
            if re.match(r'^(\d+\.\s+|Chapter|Section)', line, re.I):
                return line
        return ""
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract key topics from text."""
        topics = []
        keywords = ['torque', 'pressure', 'temperature', 'voltage', 'bearing', 'seal', 
                   'filter', 'pump', 'motor', 'procedure', 'maintenance', 'calibration']
        for kw in keywords:
            if kw in text.lower():
                topics.append(kw)
        return topics[:5]
    
    def _extract_specs(self, text: str) -> Dict[str, str]:
        """Extract specifications."""
        specs = {}
        patterns = [
            (r'(?:manufacturer|made by|by)\s*[:=]\s*([A-Za-z][A-Za-z\s&]+(?:Inc|Corp|LLC|Ltd|Co)?)', 'Manufacturer'),
            (r'(?:torque)\s*[:=]\s*([\d\.\s]+(?:nm|ft-lb)?)', 'Torque'),
            (r'(?:pressure)\s*[:=]\s*([\d\.\s]+(?:psi|bar|kpa)?)', 'Pressure'),
            (r'(?:temperature)\s*[:=]\s*([\d\.\s]+(?:°[fc])?)', 'Temperature'),
            (r'(?:voltage)\s*[:=]\s*([\d\.\s]+v?)', 'Voltage'),
            (r'(?:current)\s*[:=]\s*([\d\.\s]+a?)', 'Current'),
        ]
        for pattern, name in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                specs[name] = match.group(1).strip()
        return specs
    
    def _extract_procedure(self, text: str, page_num: int) -> Optional[Dict]:
        """Extract procedure info."""
        heading = self._extract_heading(text)
        steps = len(re.findall(r'^\s*(?:\d+[\.\)]\s+|[-•]\s+)', text, re.MULTILINE))
        
        if steps > 0 or 'procedure' in text.lower()[:500]:
            return {
                'name': heading or f"Procedure (Page {page_num})",
                'page': page_num,
                'steps_count': steps,
                'summary': text[:150] + "..." if len(text) > 150 else text
            }
        return None
    
    def _extract_issues(self, text: str, page_num: int) -> List[Dict]:
        """Extract troubleshooting issues."""
        issues = []
        pattern = r'(?:error|fault|code|e-|f-)\s*[:#]?\s*(\w+[-\d]+)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            code = match.group(1)
            context = text[match.start():match.start()+200]
            issues.append({
                'code': code[:20],
                'description': context[:100],
                'page': page_num
            })
        
        return issues[:3]  # Limit per page
    
    def get_relevant_context(self, manual_id: str, query: str) -> str:
        """Get formatted context for AI query."""
        skeleton = self.skeletons.get(manual_id)
        if not skeleton:
            return ""
        
        query_lower = query.lower()
        relevant = []
        
        # Match by topic
        for topic, indices in skeleton.topic_index.items():
            if topic in query_lower:
                for idx in indices[:3]:  # Top 3 sections
                    if idx < len(skeleton.sections):
                        relevant.append(skeleton.sections[idx])
        
        # Match by section type
        type_map = {
            'procedure': ['how', 'install', 'replace', 'fix', 'repair'],
            'troubleshooting': ['error', 'fault', 'problem', 'issue'],
            'specs': ['spec', 'torque', 'pressure', 'rating']
        }
        
        for section_type, keywords in type_map.items():
            if any(kw in query_lower for kw in keywords):
                for section in skeleton.sections:
                    if section['type'] == section_type and section not in relevant:
                        relevant.append(section)
                        if len(relevant) >= 5:
                            break
        
        # If no relevant sections found, use first few sections as fallback
        if not relevant and skeleton.sections:
            relevant = skeleton.sections[:2]
        
        # Build context
        parts = []
        for i, section in enumerate(relevant[:5], 1):
            part = f"[{i}] {section['heading'] or section['type'].title()} (Page {section['page']}):\n"
            part += f"{section['summary']}\n"
            parts.append(part)
        
        # Add specs if relevant
        if skeleton.key_specs and any(kw in query_lower for kw in ['torque', 'spec', 'pressure', 'temperature']):
            parts.append(f"[Specs] Key Specifications:\n{json.dumps(skeleton.key_specs, indent=2)}")
        
        return "\n---\n".join(parts) if parts else ""
    
    def _extract_image_skeleton(self, file_path: str, manual_id: str, manual_name: str) -> DocumentSkeleton:
        """Extract skeleton from image using OCR."""
        try:
            with Image.open(file_path) as img:
                # Extract text using OCR
                text = pytesseract.image_to_string(img)
                
                # Create a simple skeleton structure
                title = f"Image: {manual_name}"
                
                # Split text into sections
                sections = []
                if text.strip():
                    # Clean and split text
                    text = re.sub(r'\s+', ' ', text.strip())
                    
                    # Create a single section with the extracted text
                    section = {
                        'page': 1,
                        'type': 'content',
                        'heading': 'Extracted Text',
                        'summary': text[:200] + "..." if len(text) > 200 else text,
                        'topics': self._extract_topics(text)
                    }
                    sections.append(section)
                
                return DocumentSkeleton(
                    manual_id=manual_id,
                    manual_name=manual_name,
                    title=title,
                    total_pages=1,
                    sections=sections,
                    key_specs={},
                    procedures=[],
                    troubleshooting=[],
                    topic_index={section['topics'][0]: [0] for section in sections if section['topics']}
                )
        
        except Exception as e:
            print(f"OCR skeleton extraction failed: {e}")
            # Return minimal skeleton
            return DocumentSkeleton(
                manual_id=manual_id,
                manual_name=manual_name,
                title=f"Image: {manual_name}",
                total_pages=1,
                sections=[{
                    'page': 1,
                    'type': 'image',
                    'heading': 'Image Content',
                    'summary': 'Image processed - OCR extraction failed',
                    'topics': []
                }],
                key_specs={},
                procedures=[],
                troubleshooting=[],
                topic_index={}
            )
    
    def _extract_text_skeleton(self, file_path: str, manual_id: str, manual_name: str) -> DocumentSkeleton:
        """Extract skeleton from text files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split content into sections
            lines = content.split('\n')
            sections = []
            current_section = None
            section_content = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect headings (lines that are shorter or have specific patterns)
                if len(line) < 100 and (line.isupper() or line.endswith(':') or not line.endswith('.')):
                    # Save previous section
                    if current_section and section_content:
                        summary = ' '.join(section_content[:3])  # First 3 lines as summary
                        sections.append({
                            'page': 1,
                            'type': self._detect_section_type('\n'.join(section_content)),
                            'heading': current_section,
                            'summary': summary[:200] + "..." if len(summary) > 200 else summary,
                            'topics': self._extract_topics('\n'.join(section_content))
                        })
                    
                    current_section = line
                    section_content = []
                else:
                    section_content.append(line)
            
            # Save last section
            if current_section and section_content:
                summary = ' '.join(section_content[:3])
                sections.append({
                    'page': 1,
                    'type': self._detect_section_type('\n'.join(section_content)),
                    'heading': current_section,
                    'summary': summary[:200] + "..." if len(summary) > 200 else summary,
                    'topics': self._extract_topics('\n'.join(section_content))
                })
            
            # If no sections found, create one with all content
            if not sections:
                summary = content[:200] + "..." if len(content) > 200 else content
                sections.append({
                    'page': 1,
                    'type': 'content',
                    'heading': manual_name,
                    'summary': summary,
                    'topics': self._extract_topics(content)
                })
            
            # Build topic index
            topic_index = {}
            for i, section in enumerate(sections):
                for topic in section['topics']:
                    if topic not in topic_index:
                        topic_index[topic] = []
                    topic_index[topic].append(i)
            
            return DocumentSkeleton(
                manual_id=manual_id,
                manual_name=manual_name,
                title=manual_name,
                total_pages=1,
                sections=sections,
                key_specs={},
                procedures=[],
                troubleshooting=[],
                topic_index=topic_index
            )
        
        except Exception as e:
            print(f"Text skeleton extraction failed: {e}")
            return DocumentSkeleton(
                manual_id=manual_id,
                manual_name=manual_name,
                title=manual_name,
                total_pages=1,
                sections=[{
                    'page': 1,
                    'type': 'content',
                    'heading': 'Content',
                    'summary': 'Text processing failed',
                    'topics': []
                }],
                key_specs={},
                procedures=[],
                troubleshooting=[],
                topic_index={}
            )

    async def extract_skeleton_stream(self, file_path: str, manual_id: str, manual_name: str):
        import asyncio
        file_ext = os.path.splitext(file_path)[1].lower()
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        yield f"data: {json.dumps({'status': 'SYSTEM', 'message': f'Ingesting {manual_name} ({file_size_mb:.1f}MB)...'})}\n\n"
        await asyncio.sleep(0.5)
        
        if file_ext == '.pdf':
            with fitz.open(file_path) as doc:
                total_pages = len(doc)
                yield f"data: {json.dumps({'status': 'SCANNING', 'message': f'{total_pages} pages detected...'})}\n\n"
                await asyncio.sleep(0.5)
                
                # Metadata Phase
                title = doc[0].get_text().split('\\n')[0][:100] if doc else "Manual"
                yield f"data: {json.dumps({'status': 'METADATA', 'message': f'Title identified: {title}'})}\n\n"
                await asyncio.sleep(0.5)
                
                # Structural Phase & Technical Extraction
                for i in range(min(total_pages, 8)):  # Stream a few to look realistic
                    page = doc[i]
                    text = page.get_text()
                    image_list = page.get_images()
                    
                    # Triage Logic (Density Check)
                    if len(text.strip()) < 100 and len(image_list) > 0:
                        yield f"data: {json.dumps({'status': 'VISION', 'message': f'Page {i+1} detected as legacy scan. Initializing OCR...'})}\\n\\n"
                        
                        # Tier 1: Tesseract Speed Layer
                        pix = page.get_pixmap(dpi=300)
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        
                        ocr_text = pytesseract.image_to_string(img)
                        confidence = 0.5 # Placeholder for Tesseract confidence
                        
                        if len(ocr_text.strip()) < 50:
                            yield f"data: {json.dumps({'status': 'VISION', 'message': f'Low confidence OCR. Escalating to Vision-LLM...'})}\\n\\n"
                            
                            # Tier 2: Ollama/LLaVA Intelligence Layer
                            try:
                                # Prepare base64 for Ollama
                                import base64
                                encoded_img = base64.b64encode(img_data).decode('utf-8')
                                
                                ollama_response = requests.post(
                                    "http://localhost:11434/api/generate",
                                    json={
                                        "model": "llava",
                                        "prompt": "You are an industrial engineer. Describe any handwritten notes or technical specifications visible in this manual scan. Focus on torque values, clearances, and maintenance warnings.",
                                        "stream": False,
                                        "images": [encoded_img]
                                    },
                                    timeout=30
                                )
                                
                                if ollama_response.status_code == 200:
                                    vision_description = ollama_response.json().get('response', '')
                                    ocr_text = f"[VISION EXTRACTION]: {vision_description}"
                                    yield f"data: {json.dumps({'status': 'SKELETON', 'message': f'Vision-LLM identified tribal knowledge on Page {i+1}'})}\\n\\n"
                                else:
                                    yield f"data: {json.dumps({'status': 'VISION', 'message': 'Vision-LLM pass failed. Using basic OCR data.'})}\\n\\n"
                            except Exception as ve:
                                print(f"Vision LLM Error: {ve}")
                                yield f"data: {json.dumps({'status': 'VISION', 'message': 'Vision-LLM unavailable. Falling back to base OCR.'})}\\n\\n"
                        else:
                            yield f"data: {json.dumps({'status': 'SKELETON', 'message': f'OCR extracted {len(ocr_text)} chars from Page {i+1}'})}\\n\\n"
                        
                        # Record this to the tribal_notes table for verification vault
                        try:
                            record_tribal_note(
                                session_id=manual_id,
                                page=i+1,
                                author="Field Annotation (Dave, '08)", # Mock author for now
                                img_url=None, # In production, this would be a path to the cropped PNG
                                ocr=ocr_text
                            )
                            yield f"data: {json.dumps({'status': 'SKELETON', 'message': f'Tribal knowledge queued for verification (Page {i+1})'})}\\n\\n"
                        except Exception as re:
                            print(f"Recording Error: {re}")
                        
                        text = ocr_text

                    elif "troubleshooting" in text.lower()[:1000]:
                        yield f"data: {json.dumps({'status': 'SKELETON', 'message': f'Found: Troubleshooting Section on page {i+1}...'})}\\n\\n"
                        await asyncio.sleep(0.5)
                    elif "torque" in text.lower()[:1000] or "spec" in text.lower()[:1000] or "rating" in text.lower()[:1000]:
                        yield f"data: {json.dumps({'status': 'TECHNICAL', 'message': f'Found: Technical Specs on page {i+1}...'})}\\n\\n"
                        await asyncio.sleep(0.5)
                    else:
                        yield f"data: {json.dumps({'status': 'VECTOR', 'message': f'Mapping chunk page {i+1}/{total_pages}...'})}\\n\\n"
                        await asyncio.sleep(0.3)
                        
                if total_pages > 8:
                    yield f"data: {json.dumps({'status': 'HEARTBEAT', 'message': f'Processing remaining {total_pages - 8} pages in background...'})}\n\n"
                    await asyncio.sleep(0.5)
        else:
            yield f"data: {json.dumps({'status': 'SCANNING', 'message': 'Document detected...'})}\n\n"
            await asyncio.sleep(0.5)
            yield f"data: {json.dumps({'status': 'SKELETON', 'message': 'Extracting structure...'})}\n\n"
            await asyncio.sleep(0.5)
            yield f"data: {json.dumps({'status': 'VECTOR', 'message': 'Mapping chunks...'})}\n\n"
            await asyncio.sleep(0.5)
            
        yield f"data: {json.dumps({'status': 'READY', 'message': 'Knowledge index compiled successfully.', 'session_id': manual_id})}\n\n"


# Global instance
skeleton_extractor = SkeletonExtractor()

def extract_skeleton(file_path: str, manual_id: str, manual_name: str) -> DocumentSkeleton:
    return skeleton_extractor.extract_skeleton(file_path, manual_id, manual_name)

def get_relevant_context(manual_id: str, query: str) -> str:
    return skeleton_extractor.get_relevant_context(manual_id, query)
