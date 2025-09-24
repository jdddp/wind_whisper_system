import os
import asyncio
from typing import Optional
from pathlib import Path
import mimetypes
import logging

# 文本提取相关库
try:
    import PyPDF2
    import pdfplumber
except ImportError:
    PyPDF2 = None
    pdfplumber = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

logger = logging.getLogger(__name__)

class TextExtractionService:
    """文本提取服务，支持多种文件格式"""
    
    def __init__(self):
        self.supported_types = {
            'application/pdf': self._extract_from_pdf,
            'text/plain': self._extract_from_text,
            'text/csv': self._extract_from_csv,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._extract_from_docx,
            'application/msword': self._extract_from_doc,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': self._extract_from_excel,
            'application/vnd.ms-excel': self._extract_from_excel,
            'image/jpeg': self._extract_from_image,
            'image/png': self._extract_from_image,
            'image/gif': self._extract_from_image,
            'image/bmp': self._extract_from_image,
            'image/tiff': self._extract_from_image,
            'audio/mpeg': self._extract_from_audio,
            'audio/wav': self._extract_from_audio,
            'audio/ogg': self._extract_from_audio,
        }
    
    async def extract_text(self, file_path: str, content_type: str) -> Optional[str]:
        """
        从文件中提取文本内容
        
        Args:
            file_path: 文件路径
            content_type: MIME类型
            
        Returns:
            提取的文本内容，如果失败返回None
        """
        try:
            if content_type not in self.supported_types:
                logger.warning(f"Unsupported content type: {content_type}")
                return None
            
            extractor = self.supported_types[content_type]
            
            # 在线程池中运行提取操作，避免阻塞
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, extractor, file_path)
            
            return text
            
        except Exception as e:
            logger.error(f"Text extraction failed for {file_path}: {str(e)}")
            return None
    
    def _extract_from_pdf(self, file_path: str) -> Optional[str]:
        """从PDF文件提取文本"""
        if not pdfplumber:
            logger.warning("pdfplumber not available for PDF extraction")
            return None
        
        try:
            text_content = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
            
            return '\n\n'.join(text_content) if text_content else None
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            # 尝试使用PyPDF2作为备选
            if PyPDF2:
                try:
                    text_content = []
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        for page in pdf_reader.pages:
                            text = page.extract_text()
                            if text:
                                text_content.append(text)
                    
                    return '\n\n'.join(text_content) if text_content else None
                except Exception as e2:
                    logger.error(f"PyPDF2 extraction also failed: {str(e2)}")
            
            return None
    
    def _extract_from_text(self, file_path: str) -> Optional[str]:
        """从纯文本文件提取内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        return file.read()
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            logger.error(f"Text file extraction failed: {str(e)}")
        
        return None
    
    def _extract_from_csv(self, file_path: str) -> Optional[str]:
        """从CSV文件提取内容"""
        if not pd:
            logger.warning("pandas not available for CSV extraction")
            return None
        
        try:
            df = pd.read_csv(file_path)
            # 将DataFrame转换为文本格式
            return df.to_string(index=False)
        except Exception as e:
            logger.error(f"CSV extraction failed: {str(e)}")
            return None
    
    def _extract_from_docx(self, file_path: str) -> Optional[str]:
        """从DOCX文件提取文本"""
        if not Document:
            logger.warning("python-docx not available for DOCX extraction")
            return None
        
        try:
            doc = Document(file_path)
            text_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            # 提取表格内容
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_content.append(' | '.join(row_text))
            
            return '\n\n'.join(text_content) if text_content else None
            
        except Exception as e:
            logger.error(f"DOCX extraction failed: {str(e)}")
            return None
    
    def _extract_from_doc(self, file_path: str) -> Optional[str]:
        """从DOC文件提取文本（需要额外工具）"""
        logger.warning("DOC format extraction not implemented")
        return None
    
    def _extract_from_excel(self, file_path: str) -> Optional[str]:
        """从Excel文件提取内容"""
        if not pd:
            logger.warning("pandas not available for Excel extraction")
            return None
        
        try:
            # 读取所有工作表
            excel_file = pd.ExcelFile(file_path)
            text_content = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_text = f"工作表: {sheet_name}\n{df.to_string(index=False)}"
                text_content.append(sheet_text)
            
            return '\n\n'.join(text_content) if text_content else None
            
        except Exception as e:
            logger.error(f"Excel extraction failed: {str(e)}")
            return None
    
    def _extract_from_image(self, file_path: str) -> Optional[str]:
        """从图像文件提取文本（OCR）"""
        if not Image or not pytesseract:
            logger.warning("PIL or pytesseract not available for image OCR")
            return None
        
        try:
            image = Image.open(file_path)
            # 使用中英文OCR
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            return text.strip() if text.strip() else None
            
        except Exception as e:
            logger.error(f"Image OCR failed: {str(e)}")
            return None
    
    def _extract_from_audio(self, file_path: str) -> Optional[str]:
        """从音频文件提取文本（语音识别）"""
        if not sr:
            logger.warning("speech_recognition not available for audio transcription")
            return None
        
        try:
            r = sr.Recognizer()
            
            # 支持WAV格式
            if file_path.lower().endswith('.wav'):
                with sr.AudioFile(file_path) as source:
                    audio = r.record(source)
                    # 尝试使用Google语音识别
                    text = r.recognize_google(audio, language='zh-CN')
                    return text
            else:
                logger.warning(f"Audio format not supported for transcription: {file_path}")
                return None
                
        except sr.UnknownValueError:
            logger.warning("Speech recognition could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}")
            return None
    
    def get_supported_types(self) -> list:
        """获取支持的文件类型列表"""
        return list(self.supported_types.keys())
    
    def is_supported(self, content_type: str) -> bool:
        """检查是否支持指定的文件类型"""
        return content_type in self.supported_types