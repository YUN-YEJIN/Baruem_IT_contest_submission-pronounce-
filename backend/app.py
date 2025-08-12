from flask import Flask, request, jsonify, send_from_directory, send_file
import os, tempfile, traceback
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from flask_cors import CORS

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"]
)

@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
TRANSCRIPT_PATH = os.path.join(UPLOAD_FOLDER, "transcript.txt")
AUDIO_PATH = os.path.join(UPLOAD_FOLDER, "recording.webm")  # ★ 명시적 경로 변수
CORRECTION_PATH = os.path.join(UPLOAD_FOLDER, "correction.txt")

@app.route('/')
@app.route('/speech.html')
def serve_html():
    return send_from_directory('.', 'speech.html')


@app.route("/speak", methods=["POST"])
def speak():
    text = request.json.get("text")
    if not text:
        return jsonify({"error": "text field is required"}), 400
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "Missing OPENAI_API_KEY"}), 500
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.audio.speech.create(
            model="tts-1-hd",
            voice="shimmer",
            input=text
        )
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.write(resp.content)
        tmp.close()
        return send_file(tmp.name, mimetype="audio/mpeg")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/upload", methods=["POST"])
def upload_audio():
    audio = request.files.get("audio")
    transcript = request.form.get("transcript", "")
    if audio is None:
        return jsonify({"error": "No audio file provided"}), 400

    # 오디오 저장
    audio.save(AUDIO_PATH)
    print(f"[UPLOAD] 오디오 저장: {AUDIO_PATH} ({os.path.getsize(AUDIO_PATH)} bytes)")

    # STT 저장
    with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(transcript)
    print(f"[UPLOAD] STT 저장: {transcript}")

    if os.path.exists(CORRECTION_PATH):
        try:
            os.remove(CORRECTION_PATH)
        except OSError:
            pass
    return jsonify({"raw_transcript": transcript})

@app.route("/audio")
def get_audio():
    # 저장된 원본 오디오 서빙
    if not os.path.exists(AUDIO_PATH):
        return jsonify({"error": "No audio found"}), 404
    return send_from_directory(UPLOAD_FOLDER, "recording.webm")

def generate_correct_sentence(user_text: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    prompt = (
        f"사용자의 실제 발음: \"{user_text}\"\n\n"
        "1. 사용자가 의도했을 가능성이 높은 자연스러운 한국어 문장 3개를 1. 2. 3. 순서로 제시해줘.\n"
        "2. 각 문장 아래에 해당 문장을 어떻게 발음하면 정확하게 들리는지, 발음은 영어표기로 팁은 사용자 문장 각 음절마다 혀의 위치나 입 모양 등 잘 발음하기 위한 자세한 설명을 한 문장으로 제공해줘.\n"
        "3. 외국인을 위한 발음 가이드야. 이해하고 쉽게 발음 할 수 있도록 자세하게 설명해줘.\n\n"
        "4. 답변 텍스트에 ### 이나 ** 같은 특수문자는 사용하지 말아줘. "
    )

    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 한국어 발음 교사야. "
                    "사용자의 잘못된 발음을 듣고 교정 및 발음 팁을 자세하게 제공해줘. "
                    "특수문자(###, **)는 쓰지 마."
                )
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.3,
    )
    corrected = resp.choices[0].message.content.strip()
    print(f"[OPENAI OK] {corrected[:120]}...")
    return corrected

def safe_generate_and_cache(transcript: str):
    try:
        ans = generate_correct_sentence(transcript)
        if ans and ans.strip():
            with open(CORRECTION_PATH, "w", encoding="utf-8") as f:
                f.write(ans.strip())
            return ans.strip()
        return None
    except Exception as e:
        print("[GENERATE ERROR]", e)
        traceback.print_exc()
        return None

@app.route("/result", methods=["GET"])
def get_result():
    """
    - 저장된 STT(uploads/transcript.txt)를 읽어 교정 생성/반환
    - ?text=... 로 직접 입력 테스트 가능
    - ?regenerate=1 로 강제 재생성 가능
    """
    override = request.args.get("text")
    force = request.args.get("regenerate") == "1"

    # 1) transcript 결정
    if override is not None:
        transcript = override.strip()
    else:
        if not os.path.exists(TRANSCRIPT_PATH):
            return jsonify({"error": "No transcript found"}), 404
        with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
            transcript = f.read().strip()

    # 2) 캐시 사용/재생성
    answer = None
    if not force and os.path.exists(CORRECTION_PATH):
        with open(CORRECTION_PATH, "r", encoding="utf-8") as f:
            cached = f.read().strip()
            answer = cached if cached else None

    if force or not answer:
        print(f"[/result] generate (force={force})")
        answer = safe_generate_and_cache(transcript)

    # 3) 결과 반환 (answer가 None이면 프런트에서 재시도 버튼 보여줄 수 있음)
    return jsonify({
        "raw_transcript": transcript,
        "answer": answer,
        "cached": bool(answer and os.path.exists(CORRECTION_PATH))
    })

if __name__ == "__main__":
    # Live Server가 127.0.0.1:5501이면, 프런트에서 BACKEND_URL도 127.0.0.1로 맞춰 주는 것을 권장
    app.run(host="0.0.0.0", port=5000, debug=True)
