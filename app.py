"""KB 약관 X-Ray 프로토타입 메인 애플리케이션"""

import streamlit as st
import analyzer
import utils
import config
import datetime
import uuid
import pandas as pd
import time
import base64
import os
import json

# ====== 데이터 영속성 (로컬 저장소) ======
HISTORY_FILE = "kb_xray_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"기록 로드 에러: {e}")
            return []
    return []

def save_history(history_data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"기록 저장 에러: {e}")

st.set_page_config(
    page_title="KB 약관 X-Ray | AI 컴플라이언스 솔루션",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====== 로컬 OTF 폰트 로드 ======
@st.cache_data
def get_base64_of_bin_file(filename):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                data = f.read()
            return base64.b64encode(data).decode()
    except Exception as e:
        print(f"폰트 로드 에러: {e}")
    return None

font_light_b64 = get_base64_of_bin_file("KBFGText-Light.otf")
font_medium_b64 = get_base64_of_bin_file("KBFGText-Medium.otf")

if font_light_b64 and font_medium_b64:
    font_face_css = f"""
    @font-face {{ font-family: 'KBFGText'; src: url(data:font/opentype;charset=utf-8;base64,{font_light_b64}) format('opentype'); font-weight: 400; font-style: normal; }}
    @font-face {{ font-family: 'KBFGText'; src: url(data:font/opentype;charset=utf-8;base64,{font_medium_b64}) format('opentype'); font-weight: 500; font-style: normal; }}
    @font-face {{ font-family: 'KBFGText'; src: url(data:font/opentype;charset=utf-8;base64,{font_medium_b64}) format('opentype'); font-weight: 600; font-style: normal; }}
    @font-face {{ font-family: 'KBFGText'; src: url(data:font/opentype;charset=utf-8;base64,{font_medium_b64}) format('opentype'); font-weight: 700; font-style: normal; }}
    @font-face {{ font-family: 'KBFGText'; src: url(data:font/opentype;charset=utf-8;base64,{font_medium_b64}) format('opentype'); font-weight: 800; font-style: normal; }}
    
    html, body, p, h1, h2, h3, h4, h5, h6, a, ul, ol, li, label, table, th, td, .stMarkdown, .stText, button {{
        font-family: 'KBFGText', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }}
    
    div[class*="st-"] {{
        font-family: 'KBFGText', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    
    i, em, span.material-symbols-rounded, span.material-icons, span[class*="icon"], div[data-testid="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    }}
    """
else:
    font_face_css = """
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, p, h1, h2, h3, h4, h5, h6, a, ul, ol, li, label, table, th, td, button, .stMarkdown, .stText {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
    }
    i, em, span.material-symbols-rounded, span.material-icons, div[data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    }
    """

# ====== 전역 CSS 적용 ======
st.markdown(f"""
<style>
    {font_face_css}
    .stApp {{ background-color: #F8F9FA; }}
    .hero-banner {{ background: #1A1D24; padding: 40px 50px; border-radius: 12px; margin-bottom: 35px; border-left: 6px solid #FFCC00; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
    .hero-banner h1 {{ color: #FFFFFF !important; font-size: 2.4rem; font-weight: 800; margin: 0 0 10px 0; letter-spacing: -0.5px; }}
    .hero-banner h1 span {{ color: #FFCC00 !important; font-family: 'KBFGText', sans-serif !important; }}
    .hero-banner p {{ color: #A0AEC0 !important; font-size: 1.05rem; margin: 0; line-height: 1.5; font-family: 'KBFGText', sans-serif !important; }}
    .score-card {{ padding: 30px 20px; border-radius: 10px; color: #FFFFFF !important; text-align: center; margin: 20px 0; }}
    .score-card p {{ color: #FFFFFF !important; margin-bottom:5px; }}
    .score-card.high {{ background: #E53E3E; }}
    .score-card.medium {{ background: #D97706; }}
    .score-card.low {{ background: #16A34A; }}
    .score-card h2 {{ color: #FFFFFF !important; font-size: 2.2rem; font-weight: 800; margin: 5px 0 0 0; }}
    div[data-testid="stVerticalBlock"] div.stContainer {{ background: #FFFFFF; border-radius: 10px; padding: 25px; border: 1px solid #E2E8F0; box-shadow: 0 2px 6px rgba(0,0,0,0.02); }}
    .step-header {{ font-size: 1.1rem; font-weight: 700; color: #2D3748; margin-bottom: 5px; }}
    .step-header span.num {{ background: #F1F5F9; color: #475569; padding: 2px 8px; border-radius: 6px; font-size: 0.9rem; margin-right: 8px; font-weight: 600; }}
    .step-desc {{ color: #718096; font-size: 0.9rem; margin-bottom: 15px; }}
    div.stButton > button[kind="primary"] {{ background-color: #FFCC00; color: #1A1D24 !important; font-size: 1.1rem; font-weight: 700; border-radius: 8px; height: 55px; border: 1px solid #E5B800; }}
    div.stButton > button[kind="primary"]:hover {{ background-color: #F5B900; }}
    .status-badge {{ padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; font-weight: 600; margin-right: 6px; display: inline-block; }}
    .badge-high {{ background-color: #FFF5F5; color: #C53030; border: 1px solid #FEB2B2; }}
    .badge-medium {{ background-color: #FFFFF0; color: #B7791F; border: 1px solid #F6E05E; }}
    .badge-low {{ background-color: #F0FFF4; color: #276749; border: 1px solid #9AE6B4; }}
    .badge-gray {{ background-color: #F7FAFC; color: #4A5568; border: 1px solid #E2E8F0; }}
    .highlight-box {{ background: #F8F9FA; border-left: 3px solid #FFCC00; padding: 16px; border-radius: 0 6px 6px 0; margin: 12px 0; font-size: 0.95rem; line-height: 1.6; color: #2D3748; }}
    .executive-summary {{ background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 24px; border-radius: 12px; font-size: 1rem; color: #334155; line-height: 1.6; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }}
</style>
""", unsafe_allow_html=True)

# ====== 세션 상태 초기화 ======
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "terms_text" not in st.session_state:
    st.session_state.terms_text = ""
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "current_view" not in st.session_state:
    st.session_state.current_view = None

# ====== 모델 로드 ======
@st.cache_resource(show_spinner=False)
def load_analyzers():
    return analyzer.ClauseAnalyzer(), analyzer.SalesRiskAnalyzer()

clause_analyzer, sales_analyzer = load_analyzers()

# ====== 법률 용어 설명 딕셔너리 ======
EASY_EXPLANATIONS = {
    "TC001": "회사의 과실로 고객이 손해를 입었음에도 불구하고, 배상 책임을 축소하거나 면책하려는 조항입니다.",
    "TC002": "고객의 사전 동의 절차 없이, 회사가 일방적으로 서비스 규정이나 혜택을 변경할 수 있도록 하는 조항입니다.",
    "TC003": "고객의 명시적 의사 확인 없이 계약이 자동 연장되거나, 회사가 임의로 서비스를 해지할 수 있도록 하는 조항입니다.",
    "TC004": "계약 중도 해지 시, 실제 발생한 손해액을 초과하는 과도한 위약금이나 배상을 고객에게 청구하는 조항입니다.",
    "TC005": "가입 시점에는 존재하지 않았던 고객에게 불리한 조건을 사후에 일방적으로 추가할 수 있는 조항입니다."
}

# ====== 공통 렌더링 함수 ======
def render_analysis_result(record, tab_prefix="main"):
    report = record["report"]
    toxic_results = record["toxic_results"]
    score = record["score"]
    mode = record["mode"]
    
    high_threshold = st.session_state.get('high_threshold', 70)
    medium_threshold = st.session_state.get('medium_threshold', 40)

    if score >= high_threshold:
        board_class = "score-card high"
        status_text = "위험 (High Risk)"
    elif score >= medium_threshold:
        board_class = "score-card medium"
        status_text = "주의 (Warning)"
    else:
        board_class = "score-card low"
        status_text = "양호 (Safe)"

    st.markdown(f"""
    <div class="{board_class}">
        <p>AI 종합 리스크 판정 ({mode})</p>
        <h2>{status_text} <span style='font-size:1.4rem; font-weight:500; opacity:0.9;'>({score} / 100)</span></h2>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        c1, c2, c3 = st.columns(3)
        c1.metric("통합 위험 점수", f"{score}점")
        if mode in ["약관 리스크 스캔", "통합 리포트"]:
            c2.metric("약관 독소조항 점수", f"{report.get('term_risk_score', 0)}점")
        else:
            c2.metric("약관 독소조항 점수", "N/A (분석제외)")
        if mode in ["상담 녹취 대조", "통합 리포트"]:
            c3.metric("불완전판매 위험 점수", f"{report.get('sales_risk_score', 0)}점")
        else:
            c3.metric("불완전판매 위험 점수", "N/A (분석제외)")

    # --- 1. 요약 리포트 ---
    st.markdown("<h3 style='margin-top:30px; font-weight:700; color:#1A1D24; font-size:1.3rem;'>AI 분석 결과 요약</h3>", unsafe_allow_html=True)
    
    if score >= high_threshold:
        summary_title = "<strong style='color:#E53E3E; font-size:1.15rem;'>조치 권고: 고위험 요소 감지</strong>"
        summary_desc = "분석 데이터 내에 금융소비자보호법 위반 소지가 있거나 <b>고객에게 불리하게 해석될 수 있는 중대한 리스크 요소</b>가 포함되어 있습니다. 향후 법적 분쟁의 소지가 있으므로 검출된 내역을 중심으로 즉각적인 조치가 권장됩니다."
    elif score >= medium_threshold:
        summary_title = "<strong style='color:#D97706; font-size:1.15rem;'>검토 권장: 주의 요소 감지</strong>"
        summary_desc = "전반적인 내용은 양호하나, <b>오해를 유발하거나 불완전판매로 간주될 수 있는 주의 요소</b>가 일부 발견되었습니다. 문구의 명확성을 높이기 위한 내부 검토를 권장합니다."
    else:
        summary_title = "<strong style='color:#16A34A; font-size:1.15rem;'>적합 판정: 특이사항 없음</strong>"
        summary_desc = "현재 분석된 데이터에서는 금융소비자보호 가이드라인에 위배되는 <b>특별한 리스크 요인이 발견되지 않았습니다.</b>"

    issue_bullets = ""
    if toxic_results or (mode in ["상담 녹취 대조", "통합 리포트"] and record["has_transcript"] and report.get("sales_analysis", {}).get("signals")):
        issue_bullets += "<div style='margin-top:15px; padding-top:15px; border-top:1px dashed #CBD5E1;'>"
        issue_bullets += "<strong style='color:#475569; font-size:1.05rem;'>발견된 주요 리스크 요인:</strong><ul style='margin-top:8px; margin-bottom:0; color:#334155; font-size:0.95rem; line-height:1.7;'>"
        
        if toxic_results:
            categories = list(set([item['category'] for item in toxic_results]))
            issue_bullets += f"<li><b>약관 문서:</b> {', '.join(categories)} 규정과 관련된 조항에서 주의가 필요합니다.</li>"
        
        sr = report.get("sales_analysis", {})
        if sr.get("signals"):
            keywords = list(set([sig['keyword'] for sig in sr['signals']]))
            issue_bullets += f"<li><b>상담 녹취:</b> '{', '.join(keywords)}' 등 고객에게 단정적인 기대를 유발할 수 있는 단어가 사용되었습니다.</li>"
            
        issue_bullets += "</ul></div>"

    st.markdown(f"""
    <div class='executive-summary'>
        {summary_title}<br>
        <div style='margin-top:8px;'>{summary_desc}</div>
        {issue_bullets}
    </div>
    """, unsafe_allow_html=True)

    # --- 2. 독소조항 분석 내역 ---
    if mode in ["약관 리스크 스캔", "통합 리포트"]:
        st.markdown("<h3 style='margin-top:35px; font-weight:700; color:#1A1D24; font-size:1.2rem;'>검출된 약관 리스크 상세 내역</h3>", unsafe_allow_html=True)
        with st.container():
            if not toxic_results:
                st.info("검출된 독소조항이 없습니다. 규정 가이드라인을 준수하고 있습니다.")
            else:
                easy_mode = st.toggle("법률 용어 쉬운 설명 모드", key=f"easy_toggle_{tab_prefix}_{record['id']}")
                
                for i, item in enumerate(toxic_results, 1):
                    with st.expander(f"[{item['category']}] 리스크 점수: {item['top_risk_score']}점", expanded=(i==1)):
                        if easy_mode:
                            easy_text = EASY_EXPLANATIONS.get(item['id'], "해당 조항은 해석에 따라 고객에게 불리한 영향을 미칠 수 있습니다.")
                            st.info(f"**해설:** {easy_text}")
                        
                        st.markdown(f"<div style='color:#4A5568; font-size:0.9rem; margin-bottom:10px;'><b>Rule ID:</b> <code style='background:#F1F5F9; padding:2px 6px; border-radius:4px;'>{item['id']}</code> &nbsp;|&nbsp; <b>권장 가이드:</b> {item['guide']}</div>", unsafe_allow_html=True)
                        for match in item["matches"]:
                            highlighted = utils.highlight_text(match["text"], match["keyword_hits"], color="#FEF08A")
                            st.markdown(f"<div class='highlight-box'>{highlighted}</div>", unsafe_allow_html=True)
                        st.markdown("<hr style='border:0; border-top:1px solid #E2E8F0; margin:15px 0;'>", unsafe_allow_html=True)
                        st.markdown(f"**AI 리스크 분류:** <span class='status-badge badge-gray'>{item['cls_result']['label']} (신뢰도: {item['cls_result']['confidence']})</span>", unsafe_allow_html=True)
                        
                        if item["attn"] and not easy_mode:
                            attn_html = " <span style='color:#CBD5E0; margin:0 4px;'>/</span> ".join(
                                [f"<span style='color:#2B6CB0; font-weight:600;'>{tok} <span style='color:#718096; font-weight:400; font-size:0.85em;'>({s:.2f})</span></span>" for tok, s in item["attn"][:6]]
                            )
                            st.markdown(f"<div style='margin-top:10px;'><b>판별 근거 (XAI 주요 인자):</b><br><div style='margin-top:5px; font-size:0.95rem;'>{attn_html}</div></div>", unsafe_allow_html=True)

    # --- 3. 불완전판매 분석 내역 ---
    if mode in ["상담 녹취 대조", "통합 리포트"] and record["has_transcript"]:
        st.markdown("<h3 style='margin-top:35px; font-weight:700; color:#1A1D24; font-size:1.2rem;'>상담 불완전판매 감지 내역</h3>", unsafe_allow_html=True)
        with st.container():
            sr = report.get("sales_analysis", {})
            risk_score = sr.get("risk_score", 0)
            st.markdown(f"<p style='font-size:1.05rem; color:#4A5568;'>스크립트 위험 점수: <b style='color:#E53E3E;'>{risk_score}점</b></p>", unsafe_allow_html=True)

            if sr.get("signals"):
                signal_html = ""
                for sig in sr["signals"]:
                    badge_class = "badge-high" if sig["level"] == "high_risk" else ("badge-medium" if sig["level"] == "medium_risk" else "badge-low")
                    signal_html += f"<span class='status-badge {badge_class}'>{sig['keyword']} (+{sig['score']})</span> "
                st.markdown(f"<div style='margin-top: 10px;'>{signal_html}</div>", unsafe_allow_html=True)
            else:
                st.info("스크립트 분석 결과, 불완전판매 위험 신호가 감지되지 않았습니다.")

# ====== 사이드바 ======
with st.sidebar:
    st.markdown("""
    <div style='padding:10px 0 20px 0;'>
        <h2 style='font-weight:800; color:#1A1D24; margin:0; letter-spacing:-0.5px;'>KB <span style='color:#D97706;'>X-Ray</span></h2>
        <p style='color:#718096; font-size:0.8rem; font-weight:600; margin-top:2px; letter-spacing:0.5px;'>AI COMPLIANCE AGENT</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    st.markdown("<b>분석 모드 선택</b>", unsafe_allow_html=True)
    analysis_mode = st.radio("분석 모드", ["통합 리포트", "약관 리스크 스캔", "상담 녹취 대조"], label_visibility="collapsed")
    
    with st.expander("고급 설정 (리스크 민감도)"):
        st.session_state.high_threshold = st.slider("고위험(High) 판단 기준점", 50, 90, 70)
        st.session_state.medium_threshold = st.slider("주의(Warning) 판단 기준점", 20, 60, 40)
        st.caption("※ 기준점을 낮추면 더 보수적으로 리스크를 탐지합니다.")
    
    st.divider()
    
    st.markdown("<h4 style='color:#2D3748; font-weight:700; font-size:1rem;'>누적 스캔 통계</h4>", unsafe_allow_html=True)
    total_runs = len(st.session_state.history)
    st.metric("총 분석 건수", f"{total_runs}건")
    if total_runs > 0:
        avg_score = sum(item['score'] for item in st.session_state.history) / total_runs
        st.metric("평균 위험도", f"{avg_score:.1f}점")
        
        history_df = pd.DataFrame([{
            'ID': r['id'], 'Date': r['date'], 'Mode': r['mode'], 'File': r['file_name'], 'Score': r['score'], 'Status': r['level']
        } for r in st.session_state.history])
        csv = history_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("감사 로그 다운로드 (CSV)", data=csv, file_name="KB_Audit_Log.csv", mime="text/csv", use_container_width=True)
        
        if st.button("전체 기록 초기화", use_container_width=True):
            st.session_state.history = []
            st.session_state.current_view = None
            save_history([])
            st.rerun()

# ====== 메인 히어로 배너 ======
st.markdown(f"""
<div class="hero-banner">
    <h1>KB <span>X-Ray</span></h1>
    <p>금융 판례 및 소비자보호 가이드라인 기반 AI 컴플라이언스 진단 솔루션.<br>약관과 상담 스크립트 내 잠재적 법률 리스크를 식별하고 종합 의견을 제시합니다.</p>
</div>
""", unsafe_allow_html=True)

# ====== 메인 탭 ======
tab_main, tab_history = st.tabs(["새로운 리스크 스캔", "분석 기록 대시보드"])

with tab_main:
    if analysis_mode == "통합 리포트":
        col1, col2 = st.columns(2)
        show_terms, show_audio = True, True
    elif analysis_mode == "약관 리스크 스캔":
        col1 = st.container()
        col2 = st.empty()
        show_terms, show_audio = True, False
    elif analysis_mode == "상담 녹취 대조":
        col1, col2 = st.columns(2)
        show_terms, show_audio = True, True

    if show_terms:
        with col1:
            with st.container():
                st.markdown("<div class='step-header'><span class='num'>01</span> 기준 문서 (약관/가이드) 업로드</div><div class='step-desc'>분석의 기준이 되는 약관 파일을 업로드해주십시오. (PDF, TXT)</div>", unsafe_allow_html=True)
                terms_file = st.file_uploader("", type=["pdf", "txt"], key="file_terms", label_visibility="collapsed")
                if terms_file:
                    if terms_file.type == "application/pdf":
                        terms_text = utils.extract_text_from_pdf(terms_file)
                    else:
                        terms_text = utils.clean_text(terms_file.read().decode("utf-8", errors="ignore"))
                    st.session_state.terms_text = terms_text
                    st.success(f"문서 데이터 로드 완료 ({len(terms_text):,}자)")

    if show_audio:
        with col2:
            with st.container():
                required_text = "(필수)" if analysis_mode == "상담 녹취 대조" else "(선택)"
                st.markdown(f"<div class='step-header'><span class='num'>02</span> 상담 녹취 업로드 <span style='color:#D97706; font-size:0.85rem;'>{required_text}</span></div><div class='step-desc'>불완전판매 대조 분석을 위한 고객 상담 음성 파일입니다.</div>", unsafe_allow_html=True)
                audio_file = st.file_uploader("", type=["mp3", "wav", "m4a"], key="file_audio", label_visibility="collapsed")
                if audio_file:
                    with st.spinner("음성 텍스트 변환(STT) 진행 중..."):
                        import whisper, tempfile, os
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.name.split('.')[-1]}") as tmp:
                            tmp.write(audio_file.getvalue())
                            tmp_path = tmp.name
                        model = whisper.load_model("base")
                        result = model.transcribe(tmp_path, language="ko")
                        transcript = result["text"]
                        os.remove(tmp_path)
                    st.session_state.transcript = transcript
                    st.success("녹취 텍스트 변환 및 로드 완료")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("AI 컴플라이언스 분석 실행", type="primary", use_container_width=True):
        if not st.session_state.terms_text:
            st.warning("분석을 위해 기준 문서(약관)를 먼저 업로드해주십시오.")
        elif analysis_mode == "상담 녹취 대조" and not st.session_state.transcript:
            st.warning("상담 녹취 대조 모드에서는 녹취 파일 업로드가 필수입니다.")
        else:
            with st.spinner(f"[{analysis_mode}] AI 모델이 법률 리스크를 심층 분석 중입니다..."):
                progress_bar = st.progress(0)
                
                toxic_results = []
                sales_risk = {"risk_score": 0, "signals": [], "missed_disclosures": []}
                
                progress_bar.progress(30)
                time.sleep(0.5)

                if analysis_mode in ["약관 리스크 스캔", "통합 리포트"]:
                    toxic_results = clause_analyzer.detect_toxic_clauses(st.session_state.terms_text)
                    for item in toxic_results:
                        top_text = item["matches"][0]["text"]
                        item["cls_result"] = clause_analyzer.classify_clause_risk(top_text)
                        item["attn"] = clause_analyzer.explain_with_attention(top_text)
                
                progress_bar.progress(70)
                time.sleep(0.5)

                if analysis_mode in ["상담 녹취 대조", "통합 리포트"] and st.session_state.transcript:
                    sales_risk = sales_analyzer.analyze(st.session_state.transcript, st.session_state.terms_text)

                progress_bar.progress(90)
                
                report = analyzer.build_risk_report(toxic_results, sales_risk)
                
                if analysis_mode == "약관 리스크 스캔":
                    final_score = report["term_risk_score"]
                elif analysis_mode == "상담 녹취 대조":
                    final_score = report["sales_risk_score"]
                else:
                    final_score = report["final_risk_score"]

                progress_bar.progress(100)
                time.sleep(0.2)
                progress_bar.empty()
                
                record = {
                    "id": f"KB-{str(uuid.uuid4())[:8].upper()}",
                    "date": datetime.datetime.now().strftime("%Y.%m.%d %H:%M"),
                    "mode": analysis_mode,
                    "file_name": terms_file.name if 'terms_file' in locals() and terms_file else "직접 입력 데이터",
                    "score": final_score,
                    "level": report["risk_level"],
                    "toxic_results": toxic_results,
                    "report": report,
                    "has_transcript": bool(st.session_state.transcript)
                }
                
                st.session_state.history.insert(0, record)
                save_history(st.session_state.history)
                
                st.session_state.current_view = record
                st.rerun()

    if st.session_state.current_view:
        st.markdown("<hr style='margin: 40px 0;'>", unsafe_allow_html=True)
        render_analysis_result(st.session_state.current_view, tab_prefix="main")

# ====== 분석 기록 대시보드 탭 ======
with tab_history:
    st.markdown("<h3 style='font-weight:700; color:#1A1D24; font-size:1.3rem; margin-bottom:5px;'>리스크 모니터링 대시보드</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#718096; font-size:0.95rem; margin-bottom:20px;'>누적된 분석 결과의 트렌드를 파악하고 과거 리포트를 열람합니다.</p>", unsafe_allow_html=True)
    
    if not st.session_state.history:
        st.info("분석된 기록이 없습니다. 새로운 분석을 실행해 주십시오.")
    else:
        df = pd.DataFrame(st.session_state.history)
        df['date_parsed'] = pd.to_datetime(df['date'])
        df = df.sort_values('date_parsed')
        
        st.markdown("<b>최근 리스크 점수 추이</b>", unsafe_allow_html=True)
        chart_data = df.set_index('date')['score']
        st.line_chart(chart_data, use_container_width=True, color="#D97706")
        
        st.markdown("<hr style='border:0; border-top:1px solid #E2E8F0; margin:20px 0;'>", unsafe_allow_html=True)
        st.markdown("<b>상세 분석 로그</b>", unsafe_allow_html=True)

        for idx, rec in enumerate(st.session_state.history):
            status_label = "[고위험]" if rec['score'] >= st.session_state.get('high_threshold', 70) else ("[주의]" if rec['score'] >= st.session_state.get('medium_threshold', 40) else "[양호]")
            expander_title = f"{status_label} {rec['date']} | {rec['mode']} - {rec['file_name']} (위험도: {rec['score']}점)"
            
            with st.expander(expander_title):
                st.markdown(f"<div style='color:#718096; font-size:0.9rem; margin-bottom:10px;'><b>분석 ID:</b> `{rec['id']}`</div>", unsafe_allow_html=True)
                render_analysis_result(rec, tab_prefix="history")

# ====== 공통 푸터 ======
st.markdown("""
<div style='text-align:center; padding: 30px 0; color:#A0AEC0; font-size:0.85rem; margin-top:50px; border-top:1px solid #E2E8F0;'>
    <b>© 2026 KB Future Finance AI Challenge. Prototype Demo.</b><br>
    본 시스템은 AI 컴플라이언스 진단 프로토타입으로, 실제 법적 구속력 및 효력을 갖지 않습니다.
</div>
""", unsafe_allow_html=True)