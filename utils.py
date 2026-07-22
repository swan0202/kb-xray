"""파일 처리 및 텍스트 전처리 유틸리티"""

import re
import io
import tempfile
import PyPDF2
import numpy as np

def extract_text_from_pdf(uploaded_file):
    """PDF 파일에서 텍스트 추출"""
    text = ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        return f"[PDF 추출 오류] {str(e)}"
    return clean_text(text)

def clean_text(text):
    """텍스트 정제"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)  # 연속 공백 제거
    text = re.sub(r'[^\w\s.,?!;:()\[\]{}「」【】『』《》]', '', text)  # 특수문자 정리
    text = re.sub(r'([.]{2,})', '.', text)
    return text.strip()

def split_sentences(text):
    """문장 단위 분할"""
    if not text:
        return []
    # 한국어 문장 종결 패턴
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    return sentences

def split_into_chunks(text, chunk_size=300, overlap=50):
    """문맥 유지를 위한 슬라이딩 윈도우 청크 분할"""
    if not text:
        return []
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i+chunk_size])
        if len(chunk) > 20:
            chunks.append(chunk)
    return chunks

def softmax(x):
    """SHAP/Attention 가중치 계산용"""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

def highlight_text(sentence, keywords, color="#ff6b6b"):
    """검출된 키워드 하이라이트"""
    if not sentence or not keywords:
        return sentence
    pattern = re.compile(
        "(" + "|".join(re.escape(k) for k in keywords) + ")", re.IGNORECASE
    )
    return pattern.sub(
        lambda m: f"<mark style='background-color: {color}; padding:2px;'>{m.group(0)}</mark>",
        sentence,
    )
