import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import io
import os
import urllib.request
import zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import textwrap

# ページ全体の設定
st.set_page_config(page_title="AI自動鑑定システム", page_icon="🔮", layout="centered")

# --- パスワード設定 ---
# ここにお好きなパスワードを設定してください。納品時に相手に教える鍵になります。
APP_PASSWORD = "uranai_shuuhei_2026"

# サイドバー（設定画面）
st.sidebar.header("⚙️ システムログイン")
input_password = st.sidebar.text_input("システムパスワードを入力", type="password")

# パスワードチェック
if input_password != APP_PASSWORD:
    st.warning("正しいパスワードを入力してください。")
    st.info("※このシステムは許可されたユーザーのみが利用可能です。")
    st.stop() # パスワードが違う場合はここで処理を止める

# --- 以下、ログイン成功時のみ表示される中身 ---
st.sidebar.markdown("---")
st.sidebar.header("🔧 API・占術設定")
api_key = st.sidebar.text_input("Gemini APIキーを入力してください", type="password")
tone = st.sidebar.selectbox("鑑定の雰囲気", ["優しく寄り添う", "論理的で説得力がある", "ズバッと断言する", "神秘的でスピリチュアル"])
st.sidebar.markdown("---")
st.sidebar.subheader("使用する占術")
use_tarot = st.sidebar.checkbox("タロット", value=True)
use_four_pillars = st.sidebar.checkbox("四柱推命", value=True)
use_numerology = st.sidebar.checkbox("数秘術", value=True)

# メイン画面
st.title("🔮 AI自動鑑定システム")
st.write("情報を入力し、鑑定書を生成してください。")

with st.form("input_form"):
    col1, col2 = st.columns(2)
    with col1:
        user_name = st.text_input("相談者のお名前")
        birth_date = st.date_input("生年月日", min_value=datetime(1920, 1, 1))
    with col2:
        gender = st.selectbox("性性", ["女性", "男性", "その他"])
        location = st.text_input("出生地")
    
    consultation = st.text_area("ご相談内容", height=150)
    submit_button = st.form_submit_button("✨ 鑑定書を生成する")

# 各占術の計算ロジック（簡易版）
def calculate_numerology(dob):
    total = sum(int(d) for d in dob.strftime("%Y%m%d"))
    while total > 9 and total not in [11, 22, 33]:
        total = sum(int(d) for d in str(total))
    return total

def draw_tarot():
    cards = ["魔術師", "女教皇", "皇帝", "運命の輪", "太陽", "世界"]
    return [f"{c}({random.choice(['正', '逆'])})" for c in random.sample(cards, 3)]

# フォント自動セットアップ機能
def setup_font():
    font_path = "ipaexg.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexg00401.zip"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with zipfile.ZipFile(io.BytesIO(response.read())) as z:
                    for info in z.infolist():
                        if info.filename.endswith('ipaexg.ttf'):
                            with open(font_path, 'wb') as f:
                                f.write(z.read(info.filename))
                            break
        except Exception:
            return None
    return font_path

# PDF生成
def create_pdf(text, user_name):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    font_path = setup_font()
    if not font_path:
        return None
    pdfmetrics.registerFont(TTFont('IPAexGothic', font_path))
    c.setFont('IPAexGothic', 18)
    c.drawString(50, height - 50, f"【特別鑑定書】 {user_name} 様")
    c.line(50, height - 60, width - 50, height - 60)
    c.setFont('IPAexGothic', 11)
    text_object = c.beginText(50, height - 100)
    text_object.setLeading(16)
    for line in text.split("\n"):
        wrapped = textwrap.wrap(line, width=40)
        for w_line in wrapped:
            if text_object.getY() < 50:
                c.drawText(text_object)
                c.showPage()
                c.setFont('IPAexGothic', 11)
                text_object = c.beginText(50, height - 50)
                text_object.setLeading(16)
            text_object.textLine(w_line)
    c.drawText(text_object)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

if submit_button:
    if not api_key:
        st.error("APIキーを入力してください。")
    else:
        with st.spinner("AIが鑑定中..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                results = f"【占術】"
                if use_numerology: results += f" 数秘:{calculate_numerology(birth_date)}"
                if use_tarot: results += f" タロット:{draw_tarot()}"
                prompt = f"{user_name}様への鑑定書を「{tone}」で作成。相談:{consultation} データ:{results}"
                response = model.generate_content(prompt)
                st.text_area("鑑定結果", response.text, height=300)
                pdf_buffer = create_pdf(response.text, user_name)
                if pdf_buffer:
                    st.download_button("📄 PDFをダウンロード", pdf_buffer, f"{user_name}_鑑定書.pdf", "application/pdf")
            except Exception as e:
                st.error(f"エラー: {e}")
