"""AI 분석 엔진: 독소조항 탐지 + 불완전판매 분석 + XAI 설명 + 컴플라이언스 조치 가이드"""

import re
import numpy as np
import torch
import logging
from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.feature_extraction.text import TfidfVectorizer
import config
import utils
import streamlit as st

# 로깅 설정 (공모전 제출 시 안정성 어필)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Compliance_Agent")

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
        """독소조항 탐지: 규칙 + SBERT 의미 기반 유사도 하이브리드 분석 (배치 최적화)"""
        if not text or not text.strip():
            return []

        chunks = utils.split_into_chunks(text, chunk_size=80, overlap=20)
        if not chunks:
            return []

        results = []
        
        try:
            # 병목 개선: 모든 청크를 한 번에 Batch 인코딩하여 속도 극대화
            chunk_embs = self.sbert.encode(chunks, convert_to_tensor=True)
            
            for clause in self.clause_patterns:
                keywords = clause["keywords"]
                # 조항 키워드 인코딩
                clause_emb = self.sbert.encode(" ".join(keywords), convert_to_tensor=True)
                
                # 전체 청크와의 코사인 유사도를 한 번의 행렬 연산으로 계산
                cos_scores = util.pytorch_cos_sim(clause_emb, chunk_embs)[0].cpu().numpy()
                
                top_matches = []
                for idx, chunk in enumerate(chunks):
                    # 1) 키워드 직접 포함 여부 확인
                    keyword_hits = [kw for kw in keywords if kw in chunk]
                    if not keyword_hits:
                        continue

                    # 2) 계산된 유사도 매핑
                    similarity = float(cos_scores[idx])
                    
                    # 3) 최종 리스크 스코어 산출 (키워드 매칭과 의미 유사도 앙상블)
                    score = clause["risk_score"] * (0.6 + 0.4 * max(0, similarity))
                    
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
                        "matches": top_matches[:3],  # 상위 3개 매칭 결과만 반환
                        "top_risk_score": top_matches[0]["risk_score"],
                        "detected": True,
                    })

        except Exception as e:
            logger.error(f"독소조항 탐지 중 오류 발생: {e}")
            return []

        results.sort(key=lambda x: x["top_risk_score"], reverse=True)
        return results

    def classify_clause_risk(self, sentence):
        """딥러닝 모델 기반 위험도 세부 분류 (XAI용 출력)"""
        if not sentence:
             return {"label": "분석 불가", "confidence": 0.0, "probs": [0.33, 0.33, 0.34]}
             
        try:
            inputs = self.tokenizer(
                sentence, return_tensors="pt", truncation=True, max_length=256, padding=True
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
        except RuntimeError as re:
            logger.error(f"모델 추론 에러(Runtime): {re}")
            return {"label": "분석 불가", "confidence": 0.0, "probs": [0.33, 0.33, 0.34]}

    def explain_with_attention(self, sentence):
        """어텐션 가중치 기반의 핵심 판단 근거 토큰 추출 (설명가능한 AI)"""
        try:
            inputs = self.tokenizer(
                sentence, return_tensors="pt", truncation=True, max_length=128
            )
            with torch.no_grad():
                # bert 등 백본 모델 아키텍처에 따라 접근 방식이 다를 수 있음 유의
                outputs = getattr(self.classifier, self.classifier.base_model_prefix)(**inputs, output_attentions=True)
            
            attentions = outputs.attentions[-1][0]  # 마지막 레이어 어텐션
            attn_weights = attentions.mean(dim=(0, 1)).cpu().numpy()

            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
            scores = attn_weights[:len(tokens)]

            # utils.softmax 구현 여부에 따라 NumPy 버전으로 대체 가능
            norm_scores = np.exp(scores) / np.sum(np.exp(scores))
            
            token_importance = {}
            for tok, score in zip(tokens, norm_scores):
                if tok not in ["[CLS]", "[SEP]", "[PAD]"]:
                    cleaned = tok.replace("##", "")
                    if len(cleaned) > 1: # 단일 의미 없는 문자 필터링
                        token_importance[cleaned] = token_importance.get(cleaned, 0) + float(score)
            
            merged = sorted(token_importance.items(), key=lambda x: x[1], reverse=True)
            return merged[:10]
        except AttributeError:
            logger.warning("현재 모델 아키텍처에서 output_attentions를 지원하지 않습니다.")
            return []
        except Exception as e:
            logger.error(f"XAI 어텐션 추출 실패: {e}")
            return []

class SalesRiskAnalyzer:
    def __init__(self):
        self.sbert = load_sentence_model()

    def analyze(self, script_text, terms_text):
        """상담 녹취 스크립트 vs 약관 교차 검증 및 불완전판매 리스크 분석"""
        if not script_text or not terms_text:
            return {"risk_score": 0, "signals": [], "missed_disclosures": []}

        total_score = 0
        found_signals = []

        # 1) 불완전판매 위험 키워드 신호 감지
        for level, data in config.SALES_RISK_SIGNALS.items():
            for keyword in data["keywords"]:
                if keyword in script_text:
                    total_score += data["score"]
                    found_signals.append({
                        "level": level,
                        "keyword": keyword,
                        "score": data["score"],
                    })

        # 2) TF-IDF 기반 약관 핵심 용어 누락 여부 실제 체크
        missed_terms = self._check_missed_terms(script_text, terms_text)

        # 최종 스코어 산정 (0~100점 클리핑)
        final_score = max(0, min(100, total_score + (len(missed_terms) * 10)))

        return {
            "risk_score": final_score,
            "signals": found_signals,
            "missed_disclosures": missed_terms,
        }

    def _check_missed_terms(self, script_text, terms_text):
        """약관 내 중요 복합명사(N-gram) 추출 후 스크립트 누락 여부 교차 검증"""
        try:
            # 단일 문서 한계를 극복하기 위해 ngram_range 추가 및 토큰 패턴 정교화
            vectorizer = TfidfVectorizer(
                max_features=20, 
                ngram_range=(1, 2), 
                token_pattern=r'(?u)\b\w{2,}\b'
            )
            vectorizer.fit([terms_text])
            feature_names = vectorizer.get_feature_names_out()
            
            missed = []
            for word in feature_names:
                # 불필요한 숫자나 너무 짧은 단어 필터링
                if not re.search(r'\d', word) and len(word) >= 2:
                    if word not in script_text:
                        missed.append(word)
                        
            return missed[:5]  # 상위 5개 누락 용어 반환
        except ValueError:
            logger.warning("텍스트 데이터가 부족하여 TF-IDF 벡터화에 실패했습니다.")
            return []

def generate_action_items(toxic_results, sales_risk):
    """검출된 리스크를 바탕으로 기업 실무진을 위한 구체적이고 동적인 컴플라이언스 가이드 생성"""
    action_items = []
    
    if toxic_results:
        # 검출된 가장 위험도 높은 카테고리 추출
        top_category = toxic_results[0].get("category", "일부")
        action_items.append(
            f"1. **약관 정비 권고**: 현재 분석된 약관 중 **[{top_category}]** 규정에 고객에게 불리하게 작용할 수 있는 독소조항이 감지되었습니다. 공정거래위원회 표준약관 기준에 부합하도록 즉각적인 법무 검토를 권장합니다."
        )
    
    if sales_risk.get("signals"):
        high_risk_found = any(s["level"] == "high_risk" for s in sales_risk["signals"])
        keywords_detected = ", ".join(list(set(s["keyword"] for s in sales_risk["signals"]))[:3])
        
        if high_risk_found:
            action_items.append(
                f"2. **금소법 위반 주의**: 스크립트 내에 단정적 표현('{keywords_detected}' 등)이 감지되었습니다. 원금 보장 등으로 오인할 수 있는 표현에 대한 상담원 집중 교육 및 모니터링 스코어 감점이 필요합니다."
            )
        else:
            action_items.append(
                f"2. **설명 의무 강화**: 고객 상담 시 수익률 외에 명확한 위험성 고지가 미흡할 수 있습니다. '{keywords_detected}' 관련 스크립트 진행 시 원금 손실 위험성에 대한 필수 고지 멘트를 추가하십시오."
            )
            
    if sales_risk.get("missed_disclosures"):
        missed = ", ".join(sales_risk["missed_disclosures"])
        action_items.append(
            f"3. **주요 용어 누락**: 약관 핵심 용어인 '{missed}'에 대한 설명이 녹취상에 명확히 등장하지 않습니다. 텔레마케팅(TM) 대본에 해당 키워드를 필수 스크립트로 지정하십시오."
        )
            
    if not action_items:
        action_items.append("✅ **컴플라이언스 준수**: 현재 약관 및 상담 스크립트 모두 금융소비자보호 가이드라인을 적절히 준수하고 있어 특별한 시정 조치가 필요하지 않습니다.")
        
    return action_items

def build_risk_report(toxic_results, sales_risk):
    """최종 리포트 구성 및 종합 위험도 산출"""
    overall_term_risk = 0
    if toxic_results:
        overall_term_risk = sum(r["top_risk_score"] for r in toxic_results) / len(toxic_results)

    overall_sales_risk = sales_risk.get("risk_score", 0)
    final_score = min(100, overall_term_risk * 0.5 + overall_sales_risk * 0.5)

    report = {
        "final_risk_score": round(final_score, 1),
        "term_risk_score": round(overall_term_risk, 1),
        "sales_risk_score": overall_sales_risk,
        "risk_level": "매우 위험" if final_score >= 70 else ("위험" if final_score >= 40 else "양호"),
        "toxic_clauses": toxic_results,
        "sales_analysis": sales_risk,
        "action_items": generate_action_items(toxic_results, sales_risk),
    }

    return report
