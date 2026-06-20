try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except Exception:
    fitz = None
    HAS_PYMUPDF = False
    print("[WARN] PyMuPDF not available — PDF features disabled.")
from typing import List, Dict, Any
from dataclasses import dataclass
import re
import os
import base64
from PIL import Image
import pytesseract
import io
import json
import csv

@dataclass
class DocumentChunk:
    text: str
    page_number: int
    chunk_index: int
    manual_id: str
    manual_name: str
    metadata: dict = None

class DocumentProcessor:
    """Extract and chunk various document types for vector storage."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.supported_extensions = {'.pdf', '.txt', '.csv', '.docx'}
    
    def process_pdf(self, file_path: str, manual_id: str, manual_name: str) -> List[DocumentChunk]:
        """Extract text from PDF and create chunks with metadata."""
        chunks = []
        chunk_index = 0
        
        if not HAS_PYMUPDF:
            print(f"[WARN] process_pdf called but PyMuPDF not installed: {file_path}")
            # Fallback: return a single placeholder chunk indicating PDF couldn't be parsed
            chunk = DocumentChunk(
                text=f"[PDF file: {os.path.basename(file_path)} - PDF parsing unavailable. Install PyMuPDF to enable full parsing.]",
                page_number=0,
                chunk_index=0,
                manual_id=manual_id,
                manual_name=manual_name,
                metadata={"file_type": "pdf", "parsed": False}
            )
            return [chunk]

        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                # Extract text from page
                text = page.get_text()
                
                # Clean text
                text = self._clean_text(text)
                
                if not text.strip():
                    continue
                
                # Split into chunks
                page_chunks = self._chunk_text(text)
                
                for chunk_text in page_chunks:
                    chunk = DocumentChunk(
                        text=chunk_text,
                        page_number=page_num,
                        chunk_index=chunk_index,
                        manual_id=manual_id,
                        manual_name=manual_name,
                        metadata={
                            "total_pages": len(doc),
                            "char_count": len(chunk_text),
                            "has_numbers": bool(re.search(r'\d+', chunk_text)),
                            "has_tables": "table" in chunk_text.lower() or "spec" in chunk_text.lower()
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1
        
        return chunks
    
    def process_document(self, file_path: str, manual_id: str, manual_name: str) -> List[DocumentChunk]:
        """Process various document types and extract content."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return self.process_pdf(file_path, manual_id, manual_name)
        elif file_ext in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}:
            return self.process_image(file_path, manual_id, manual_name)
        elif file_ext == '.txt':
            return self.process_text_file(file_path, manual_id, manual_name)
        elif file_ext == '.json':
            return self.process_json_file(file_path, manual_id, manual_name)
        elif file_ext == '.csv':
            return self.process_csv_file(file_path, manual_id, manual_name)
        else:
            # Try to process as text fallback
            return self.process_text_file(file_path, manual_id, manual_name)
    
    def process_image(self, file_path: str, manual_id: str, manual_name: str) -> List[DocumentChunk]:
        """Extract text from images using OCR."""
        chunks = []
        
        try:
            # Open image and extract text using OCR
            with Image.open(file_path) as img:
                # Extract text using pytesseract
                text = pytesseract.image_to_string(img)
                
                # Clean and process the extracted text
                text = self._clean_text(text)
                
                if text.strip():
                    # Create chunks from extracted text
                    text_chunks = self._chunk_text(text)
                    
                    for i, chunk_text in enumerate(text_chunks):
                        chunk = DocumentChunk(
                            text=chunk_text,
                            page_number=1,
                            chunk_index=i,
                            manual_id=manual_id,
                            manual_name=manual_name,
                            metadata={
                                "file_type": "image",
                                "ocr_extracted": True,
                                "char_count": len(chunk_text),
                                "image_path": file_path
                            }
                        )
                        chunks.append(chunk)
        
        except Exception as e:
            print(f"OCR failed for {file_path}: {e}")
            # Create a chunk indicating the image was processed
            chunk = DocumentChunk(
                text=f"[Image file: {os.path.basename(file_path)} - OCR processing failed. Manual review recommended.]",
                page_number=1,
                chunk_index=0,
                manual_id=manual_id,
                manual_name=manual_name,
                metadata={
                    "file_type": "image",
                    "ocr_failed": True,
                    "image_path": file_path
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def process_text_file(self, file_path: str, manual_id: str, manual_name: str) -> List[DocumentChunk]:
        """Process plain text files."""
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            text = self._clean_text(text)
            
            if text.strip():
                text_chunks = self._chunk_text(text)
                
                for i, chunk_text in enumerate(text_chunks):
                    chunk = DocumentChunk(
                        text=chunk_text,
                        page_number=1,
                        chunk_index=i,
                        manual_id=manual_id,
                        manual_name=manual_name,
                        metadata={
                            "file_type": "text",
                            "char_count": len(chunk_text)
                        }
                    )
                    chunks.append(chunk)
        
        except Exception as e:
            print(f"Text processing failed for {file_path}: {e}")
        
        return chunks
    
    def process_json_file(self, file_path: str, manual_id: str, manual_name: str) -> List[DocumentChunk]:
        """Process JSON files by extracting structured data."""
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert JSON to readable text
            json_text = json.dumps(data, indent=2, ensure_ascii=False)
            text = self._clean_text(json_text)
            
            if text.strip():
                text_chunks = self._chunk_text(text)
                
                for i, chunk_text in enumerate(text_chunks):
                    chunk = DocumentChunk(
                        text=chunk_text,
                        page_number=1,
                        chunk_index=i,
                        manual_id=manual_id,
                        manual_name=manual_name,
                        metadata={
                            "file_type": "json",
                            "char_count": len(chunk_text),
                            "structured_data": True
                        }
                    )
                    chunks.append(chunk)
        
        except Exception as e:
            print(f"JSON processing failed for {file_path}: {e}")
        
        return chunks
    
    def process_csv_file(self, file_path: str, manual_id: str, manual_name: str) -> List[DocumentChunk]:
        """Process CSV files by extracting tabular data."""
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                rows = list(csv_reader)
                
                # Convert CSV to readable text
                csv_text = f"CSV Data: {os.path.basename(file_path)}\n\n"
                csv_text += f"Columns: {', '.join(csv_reader.fieldnames)}\n\n"
                
                for i, row in enumerate(rows[:100]):  # Limit to first 100 rows
                    csv_text += f"Row {i+1}: {dict(row)}\n"
                
                text = self._clean_text(csv_text)
                text_chunks = self._chunk_text(text)
                
                for i, chunk_text in enumerate(text_chunks):
                    chunk = DocumentChunk(
                        text=chunk_text,
                        page_number=1,
                        chunk_index=i,
                        manual_id=manual_id,
                        manual_name=manual_name,
                        metadata={
                            "file_type": "csv",
                            "char_count": len(chunk_text),
                            "tabular_data": True,
                            "total_rows": len(rows)
                        }
                    )
                    chunks.append(chunk)
        
        except Exception as e:
            print(f"CSV processing failed for {file_path}: {e}")
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep technical symbols
        text = re.sub(r'[^\w\s\-.,;:!?()\[\]{}<>/\\°±²³"\'&@#$%*+=]', '', text)
        return text.strip()
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence or word boundary
            if end < len(text):
                # Look for sentence break
                sentence_break = text.rfind('. ', start, end)
                if sentence_break > start + self.chunk_size // 2:
                    end = sentence_break + 1
                else:
                    # Look for word break
                    word_break = text.rfind(' ', start, end)
                    if word_break > start:
                        end = word_break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move with overlap
            start = end - self.chunk_overlap
            if start >= len(text) - self.chunk_overlap:
                break
        
        return chunks
    
    def extract_tables(self, file_path: str, page_num: int) -> List[dict]:
        """Extract table data from a specific page."""
        tables = []
        if not HAS_PYMUPDF:
            print(f"[WARN] extract_tables called but PyMuPDF not installed: {file_path}")
            return tables

        with fitz.open(file_path) as doc:
            if page_num <= len(doc):
                page = doc[page_num - 1]
                tab = page.find_tables()
                if tab and tab.tables:
                    for table in tab.tables:
                        tables.append({
                            "page": page_num,
                            "rows": table.rows,
                            "columns": table.columns,
                            "data": table.extract()
                        })
        
        return tables
