"""AI 분석 엔진: 독소조항 탐지 + 불완전판매 분석 + XAI 설명"""

import re
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.feature_extraction.text import TfidfVectorizer
import config
import utils
import streamlit as st

@st.cache_resource
def load_sentence_model():
    """문장 임베딩 모델 로드"""
    return SentenceTransformer(config.SENTENCE_MODEL_NAME)

@st.cache_resource
def load_classifier_model():
    """텍스트 분류 모델 로드 (0=중립, 1=위험, 2=안전)"""
    tokenizer = AutoTokenizer.from_pretrained(config.CLASSIFIER_MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.CLASSIFIER_MODEL_NAME,
        num_labels=3,
        ignore_mismatched_sizes=True
    )
    model.eval()
    return tokenizer, model

class ClauseAnalyzer:
    def __init__(self):
        self.sbert = load_sentence_model()
        self.tokenizer, self.classifier = load_classifier_model()
        self.clause_patterns = config.Toxic_CLAUSE_PATTERNS

    def detect_toxic_clauses(self, text):
        """독소조항 탐지: 규칙 + 유사도 하이브리드"""
        if not text:
            return []

        chunks = utils.split_into_chunks(text, chunk_size=80, overlap=20)
        results = []

        for clause in self.clause_patterns:
            keywords = clause["keywords"]
            top_matches = []

            for chunk in chunks:
                # 1) 키워드 직접 포함 여부
                keyword_hits = [kw for kw in keywords if kw in chunk]
                if not keyword_hits:
                    continue

                # 2) SBERT 유사도 추가 검증
                clause_emb = self.sbert.encode(
                    " ".join(keywords), convert_to_tensor=True
                )
                chunk_emb = self.sbert.encode(chunk, convert_to_tensor=True)
                similarity = float(util.pytorch_cos_sim(clause_emb, chunk_emb)[0][0])

                score = clause["risk_score"] * (0.6 + 0.4 * similarity)
                top_matches.append({
                    "text": chunk,
                    "keyword_hits": keyword_hits,
                    "similarity": round(similarity, 3),
                    "risk_score": round(score, 1),
                })

            if top_matches:
                top_matches.sort(key=lambda x: x["risk_score"], reverse=True)
                results.append({
                    **clause,
                    "matches": top_matches[:3],
                    "top_risk_score": top_matches[0]["risk_score"],
                    "detected": True,
                })

        results.sort(key=lambda x: x["top_risk_score"], reverse=True)
        return results

    def classify_clause_risk(self, sentence):
        """딥러닝 모델 기반 위험도 분류 (XAI용 출력)"""
        try:
            inputs = self.tokenizer(
                sentence,
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=True
            )
            with torch.no_grad():
                outputs = self.classifier(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)[0]
                label = int(torch.argmax(probs))
                confidence = float(probs[label])

            labels = {0: "중립", 1: "위험", 2: "안전"}
            return {
                "label": labels.get(label, "중립"),
                "confidence": round(confidence, 3),
                "probs": probs.tolist(),
            }
        except Exception as e:
            return {"label": "분석 불가", "confidence": 0.0, "probs": [0.33, 0.33, 0.34]}

    def explain_with_attention(self, sentence):
        """간단한 Attention 가중치 기반 설명"""
        try:
            inputs = self.tokenizer(
                sentence,
                return_tensors="pt",
                truncation=True,
                max_length=128
            )
            with torch.no_grad():
                outputs = self.classifier.bert(**inputs, output_attentions=True)
            attentions = outputs.attentions[-1][0]  # 마지막 레이어
            attn_weights = attentions.mean(dim=(0, 1)).cpu().numpy()

            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
            scores = attn_weights[:len(tokens)]

            # 토큰별 중요도 정규화
            norm_scores = utils.softmax(scores)
            token_importance = []
            for tok, score in zip(tokens, norm_scores):
                if tok not in ["[CLS]", "[SEP]", "[PAD]"]:
                    cleaned = tok.replace("##", "")
                    token_importance.append((cleaned, float(score)))

            # 토큰별 중요도 병합
            merged = {}
            for tok, score in token_importance:
                merged[tok] = merged.get(tok, 0) + score
            merged = sorted(merged.items(), key=lambda x: x[1], reverse=True)

            return merged[:10]
        except Exception:
            return []

class SalesRiskAnalyzer:
    def __init__(self):
        self.sbert = load_sentence_model()

    def analyze(self, script_text, terms_text):
        """상담 녹취 vs 약관 비교 분석"""
        if not script_text or not terms_text:
            return {"risk_score": 0, "signals": [], "missed_disclosures": []}

        total_score = 0
        found_signals = []

        # 위험 신호 감지
        for level, data in config.SALES_RISK_SIGNALS.items():
            for keyword in data["keywords"]:
                if keyword in script_text:
                    total_score += data["score"]
                    found_signals.append({
                        "level": level,
                        "keyword": keyword,
                        "score": data["score"],
                    })

        # 약관과 녹취 간 핵심 내용 누락 여부 체크
        missed_terms = self._check_missed_terms(script_text, terms_text)

        # 점수는 0~100 사이로 클리핑
        final_score = max(0, min(100, total_score + len(missed_terms) * 10))

        return {
            "risk_score": final_score,
            "signals": found_signals,
            "missed_disclosures": missed_terms,
        }

    def _check_missed_terms(self, script_text, terms_text):
        """약관 핵심 용어가 상담에서 설명되었는지 확인"""
        # 간단한 핵심 약관 용어 추출
        terms_chunks = utils.split_into_chunks(terms_text, chunk_size=100, overlap=0)
        terms_emb = self.sbert.encode(terms_chunks, convert_to_tensor=True)

        # 상담 스크립트에서 문장 추출
        script_sents = utils.split_sentences(script_text)

        missed = []
        for sent in script_sents[:30]:  # 상담 초반 30문장
            if len(sent) < 10:
                continue
            sent_emb = self.sbert.encode(sent, convert_to_tensor=True)
            sims = util.pytorch_cos_sim(sent_emb, terms_emb)[0]
            max_sim = float(sims.max())
            if max_sim < 0.45:  # 약관과 무관한 내용
                continue
            # 임시: 약관에서 핵심 키워드 추출
            # 실제로는 토픽 모델링/키워드 추출 활용
        return missed

def build_risk_report(toxic_results, sales_risk):
    """최종 리포트 구성"""
    overall_term_risk = 0
    if toxic_results:
        overall_term_risk = sum(r["top_risk_score"] for r in toxic_results) / len(toxic_results)

    overall_sales_risk = sales_risk["risk_score"]
    final_score = min(100, overall_term_risk * 0.5 + overall_sales_risk * 0.5)

    report = {
        "final_risk_score": round(final_score, 1),
        "term_risk_score": round(overall_term_risk, 1),
        "sales_risk_score": overall_sales_risk,
        "risk_level": "매우 위험" if final_score >= 70 else ("위험" if final_score >= 40 else "양호"),
        "toxic_clauses": toxic_results,
        "sales_analysis": sales_risk,
    }

    return report
