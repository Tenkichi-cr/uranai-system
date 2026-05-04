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

# ページ全体の設定
st.set_page_config(page_title="AI自動鑑定システム", page_icon="🔮", layout="centered")

# --- パスワード設定 ---
# ※納品時に設定したパスワード（合言葉）に書き換えてください。
APP_PASSWORD = "123456789"

# サイドバー（設定画面）
st.sidebar.header("⚙️ システムログイン")
input_password = st.sidebar.text_input("システムパスワードを入力", type="password")

if input_password != APP_PASSWORD:
    st.warning("正しいパスワードを入力してください。")
    st.stop()

# --- ログイン成功時 ---
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
        gender = st.selectbox("性別", ["女性", "男性", "その他"])
        location = st.text_input("出生地")
    
    consultation = st.text_area("ご相談内容", height=150)
    submit_button = st.form_submit_button("✨ 鑑定書を生成する")

# 各占術のロジック
def calculate_numerology(dob):
    total = sum(int(d) for d in dob.strftime("%Y%m%d"))
    while total > 9 and total not in [11, 22, 33]:
        total = sum(int(d) for d in str(total))
    return total

def draw_tarot():
    cards = ["魔術師", "女教皇", "皇帝", "運命の輪", "太陽", "世界", "星", "月", "恋人", "隠者"]
    return [f"{c}({random.choice(['正位置', '逆位置'])})" for c in random.sample(cards, 3)]

def calculate_four_pillars():
    elements = ["木", "火", "土", "金", "水"]
    return f"日干：{random.choice(elements)}の性質"

# フォント自動セットアップ
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

# 日本語専用の美しいテキスト折り返し処理（禁則処理付き）
def wrap_japanese_text(text, width=40):
    lines = []
    while text:
        if len(text) <= width:
            lines.append(text)
            break
        
        line = text[:width]
        remainder = text[width:]
        
        # 句読点が行の先頭に来ないようにする処理（禁則処理）
        kinsoku_chars = "、。，．！？)]}〉》」』】〕"
        if remainder and remainder[0] in kinsoku_chars:
            line += remainder[0]
            remainder = remainder[1:]
            
        lines.append(line)
        text = remainder
    return lines

# PDF生成（改行・文字抜け不具合を完全修正）
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
    
    clean_text = text.replace("#", "").replace("**", "").replace("*", "")
    for line in clean_text.split("\n"):
        # 空行（段落の間のスペース）を保持する
        if line.strip() == "":
            text_object.textLine("")
            continue
            
        # 英語のtextwrapをやめて、自作の日本語専用処理を使う
        wrapped = wrap_japanese_text(line, 40)
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
                
                results = f"【占術データ】\n"
                if use_four_pillars: 
                    results += f"・四柱推命: {calculate_four_pillars()}\n"
                if use_numerology: 
                    results += f"・数秘術: ライフパスナンバー {calculate_numerology(birth_date)}\n"
                if use_tarot: 
                    results += f"・タロット: {', '.join(draw_tarot())}\n"

                prompt = f"""
                あなたはプロの熟練鑑定士です。以下の相談者情報と占術データに基づき、最高品質の長文鑑定書を作成してください。
                
                【相談者情報】
                名前: {user_name}
                相談内容: {consultation}
                
                {results}
                
                【絶対厳守の執筆条件】
                1. 指定された雰囲気：「{tone}」のトーンで一貫して記述すること。
                2. 提供された「すべての占術データ」に必ず言及し、結果を自然に文中に織り交ぜて解説すること。
                3. 「#」や「*」などのマークダウン記法は【一切使用禁止】です。箇条書きや見出しの記号も使わず、プレーンな美しい日本語の段落分けのみで出力してください。
                """
                
                response = model.generate_content(prompt)
                
                display_text = response.text.replace("#", "").replace("**", "").replace("*", "")
                st.text_area("鑑定結果", display_text, height=300)
                
                pdf_buffer = create_pdf(display_text, user_name)
                if pdf_buffer:
                    st.download_button("📄 PDFをダウンロード", pdf_buffer, f"{user_name}_鑑定書.pdf", "application/pdf")
            except Exception as e:
                st.error(f"エラー: {e}")
