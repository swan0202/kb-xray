"""KB 약관 X-Ray 프로토타입 설정"""

# 서비스 설정
APP_TITLE = "KB 약관 X-Ray: 불완전판매 AI 검증 에이전트"
APP_DESCRIPTION = """
KB 금융 특화 AI가 약관과 상담 녹취를 교차 분석하여  
독소조항, 불완전판매 위험도, 그리고 판단 근거를 한눈에 보여드립니다.
"""

# 독소조항 패턴 사전
Toxic_CLAUSE_PATTERNS = [
    {
        "id": "TC001",
        "category": "손해배상 면제/제한",
        "keywords": ["면책", "손해배상", "책임의 한도", "책임을 지지 않는다", "배상의 책임"],
        "risk_score": 85,
        "guide": "금융사의 고의·과실로 인한 손해까지 면책하는 조항은 금융소비자보호법상 문제가 될 수 있습니다.",
    },
    {
        "id": "TC002",
        "category": "일방적 계약 변경",
        "keywords": ["일방적", "변경할 수 있다", "수정할 수 있다", "통지", "동의 없이"],
        "risk_score": 80,
        "guide": "금융사와 소비자 간 계임 불균형을 초래할 수 있는 조항입니다.",
    },
    {
        "id": "TC003",
        "category": "자동 갱신/해지",
        "keywords": ["자동 갱신", "자동연장", "자동해지", "갱신", "해지"],
        "risk_score": 70,
        "guide": "소비자의 의사확인 없이 자동 갱신되거나 해지될 수 있는 조항입니다.",
    },
    {
        "id": "TC004",
        "category": "과도한 위약금/손해배상",
        "keywords": ["위약금", "손해배상", "배상", "과다", "손해배상액"],
        "risk_score": 75,
        "guide": "위약금이 실제 손해를 초과할 경우 형법상 과다이득으로 다투어질 수 있습니다.",
    },
    {
        "id": "TC005",
        "category": "불합리한 불이익 변경",
        "keywords": ["불이익", "부당", "불리하게", "변경", "개정"],
        "risk_score": 78,
        "guide": "이미 체결된 계약에 대해 소비자에게 불리하게 내용을 변경하는 조항은 제한됩니다.",
    },
]

# 불완전판매 의심 신호
SALES_RISK_SIGNALS = {
    "high_risk": {
        "keywords": ["원금 보장", "무조건", "확실", "부동산", "부채", "고위험"],
        "score": 30,
    },
    "medium_risk": {
        "keywords": ["수익률", "수익", "좋은 기회", "한정", "오늘만"],
        "score": 15,
    },
    "low_risk": {
        "keywords": ["설명", "확인", "동의", "이해"],
        "score": -10,
    },
}

# KB-ALBERT 대신 사용할 공개 한국어 금융 특화 모델
SENTENCE_MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
CLASSIFIER_MODEL_NAME = "beomi/kcbert-base"
