#!/usr/bin/env python3
"""
ORBIT Link Setup - TikTok Account Deployment Tool
Deploys Netlify landing pages and Cloudflare Workers for click tracking
"""

from flask import Flask, Response, request, jsonify
import requests as http_requests
import hashlib
import base64
import os

app = Flask(__name__)

# Configuration
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = "ac958f158fdec62e9941d8de02bf2ac2"
NETLIFY_API_TOKEN = os.environ.get("NETLIFY_API_TOKEN", "")
SUPABASE_URL = "https://utzkvosladgdsbpujozu.supabase.co"
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Active creators with their OF URLs and background images
# background: URL to default background image (None = needs upload)
CREATORS_CONFIG = {
    "miriam": {"of_us": "https://onlyfans.com/milosmiriam", "of_de": "https://onlyfans.com/miriamxde", "has_dach": True, "worker": "miri2", "background": "https://i.imgur.com/miriam_bg.jpg"},
    "aurelia": {"of_us": "https://onlyfans.com/aurelialuv", "of_de": "https://onlyfans.com/aureliaxde", "has_dach": True, "background": None},
    "naomi": {"of_us": "https://onlyfans.com/naomidoee", "of_de": None, "has_dach": False, "background": None},
    "mara": {"of_us": "https://onlyfans.com/maraxluv", "of_de": None, "has_dach": False, "background": None},
    "megan": {"of_us": "https://onlyfans.com/megluuvvv", "of_de": None, "has_dach": False, "background": None},
    "selena": {"of_us": "https://onlyfans.com/selenawrld", "of_de": None, "has_dach": False, "background": None},
    "sofia": {"of_us": "https://onlyfans.com/sofiasynn", "of_de": None, "has_dach": False, "background": None},
    "nalani": {"of_us": "https://onlyfans.com/nalaniluv", "of_de": None, "has_dach": False, "background": None},
    "suki": {"of_us": "https://onlyfans.com/sukixdarling", "of_de": None, "has_dach": False, "background": None},
    "mira": {"of_us": "https://onlyfans.com/miraswrld", "of_de": None, "has_dach": False, "background": None},
}


def generate_worker_code(model_name, of_url_us, of_url_de):
    """Generate Cloudflare Worker code for a creator"""
    return f'''const MODEL_NAME = "{model_name}";
const REDIRECT_URL_US = "{of_url_us}";
const REDIRECT_URL_DE = "{of_url_de}";

const DACH_COUNTRIES = new Set(["DE", "AT", "CH"]);

const BLOCKED_UA_PATTERNS = [
  "bot", "crawl", "spider", "preview", "scraper", "fetch",
  "googlebot", "bingbot", "slurp", "duckduckbot", "yandex", "baidu",
  "semrush", "ahrefs", "moz", "screaming", "majestic",
  "facebookexternalhit", "twitterbot", "linkedinbot", "pinterest",
  "snapchat", "whatsapp", "telegram", "discord", "tiktok",
  "bytespider", "bytedance", "python", "curl", "wget", "headless",
  "phantomjs", "selenium", "puppeteer", "playwright", "node-fetch",
  "axios", "go-http", "java", "php", "webview"
];

function isLikelyBot(userAgent) {{
  const ua = (userAgent || "").toLowerCase();
  if (!ua || ua.length < 20) return true;
  return BLOCKED_UA_PATTERNS.some((p) => ua.includes(p));
}}

function parseDevice(userAgent) {{
  const ua = (userAgent || "").toLowerCase();
  const isMobile = /iphone|ipad|android|mobile/.test(ua);
  const os = /iphone|ipad|ios/.test(ua) ? "ios"
    : /android/.test(ua) ? "android"
    : /windows/.test(ua) ? "windows"
    : /mac os|macintosh/.test(ua) ? "macos" : "unknown";
  const browser = ua.includes("chrome") && !ua.includes("edg") ? "chrome"
    : ua.includes("safari") && !ua.includes("chrome") ? "safari"
    : ua.includes("firefox") ? "firefox"
    : ua.includes("edg") ? "edge" : "unknown";
  return {{ device_type: isMobile ? "mobile" : "desktop", os, browser }};
}}

function pickTarget(country) {{
  const isDach = DACH_COUNTRIES.has(country);
  return isDach
    ? {{ of_account: MODEL_NAME + "_de", redirected_to: REDIRECT_URL_DE }}
    : {{ of_account: MODEL_NAME + "_us", redirected_to: REDIRECT_URL_US }};
}}

async function logClick(supabaseUrl, serviceKey, payload) {{
  const url = supabaseUrl.replace(/\\/$/, "") + "/rest/v1/link_clicks";
  return fetch(url, {{
    method: "POST",
    headers: {{
      "Content-Type": "application/json",
      apikey: serviceKey,
      Authorization: "Bearer " + serviceKey,
      Prefer: "return=minimal",
    }},
    body: JSON.stringify(payload),
  }}).then((r) => r.arrayBuffer().catch(() => null)).catch(() => null);
}}

export default {{
  async fetch(request, env) {{
    const supabaseUrl = env.SUPABASE_URL;
    const serviceKey = env.SUPABASE_SERVICE_KEY;
    if (!supabaseUrl || !serviceKey) {{
      return new Response("Config error", {{ status: 500 }});
    }}

    const url = new URL(request.url);
    const ua = request.headers.get("user-agent") || "";
    const country = request.cf?.country || "US";
    const acc = (url.searchParams.get("acc") || "unknown").slice(0, 100);

    if (isLikelyBot(ua)) {{
      return new Response("Nothing here", {{ status: 200 }});
    }}

    const target = pickTarget(country);
    const device = parseDevice(ua);

    const payload = {{
      acc, country,
      timestamp: new Date().toISOString(),
      user_agent: ua.toLowerCase().slice(0, 500),
      model: MODEL_NAME,
      of_account: target.of_account,
      tiktok_account: acc,
      redirected_to: target.redirected_to,
      device_type: device.device_type,
      browser: device.browser,
      os: device.os,
    }};

    logClick(supabaseUrl, serviceKey, payload);
    return Response.redirect(target.redirected_to, 302);
  }},
}};'''


def generate_netlify_html(worker_url, tiktok_handle, background_url="background.jpg", gif_url="https://s6.gifyu.com/images/bz27i.gif"):
    """Generate Netlify landing page HTML - Miriam-style design with floating labels"""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<title>Redirect</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔗</text></svg>"/>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;800&display=swap" rel="stylesheet"/>
<style>
  :root{{--fg:#fff;--muted:rgba(255,255,255,.95);--label-bg: rgba(20,20,24,0.62);--label-border: rgba(255,255,255,0.28);--gif-w: clamp(220px, 60vw, 280px);--gif-center: 28%;--num-accent: #00ff66;}}
  *{{ box-sizing:border-box; }}
  html, body{{ height:100vh; overflow:hidden; }}
  body{{margin:0;background: url('{background_url}') no-repeat center center / cover fixed;color: var(--fg);font-family: Poppins, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;}}
  .gif-card{{position: fixed;left: 50%;top: var(--gif-center);transform: translate(-50%, -50%);width: var(--gif-w);height: auto;border-radius: 16px;box-shadow: 0 8px 24px rgba(0,0,0,.45);z-index: 3;background: rgba(0,0,0,.15);-webkit-backdrop-filter: blur(6px);backdrop-filter: blur(6px);border: 1px solid rgba(255,255,255,.18);padding: 10px;}}
  .gif-card img, .gif-card video{{width:100%; height:auto; display:block;border-radius:12px; background:#111;}}
  .corner-label, .below{{position: fixed;display: inline-flex;align-items: center;gap: 8px;padding: 10px 14px;border-radius: 999px;background: var(--label-bg);border: 1px solid var(--label-border);-webkit-backdrop-filter: blur(8px);backdrop-filter: blur(8px);box-shadow: 0 6px 22px rgba(0,0,0,.32);color: rgba(255,255,255,0.96);font-weight: 700;font-size: clamp(14px, 2.1vw, 17px);z-index: 5;}}
  .corner-label .num, .below .num{{color: var(--num-accent);text-shadow: 0 0 8px var(--num-accent), 0 0 16px rgba(0,255,102,.5);font-weight: 800;}}
  .corner-label{{top: calc(14px + env(safe-area-inset-top));right: 12px;}}
  .below{{left: 50%;transform: translateX(-50%);top: calc(var(--gif-center) + (var(--gif-w) / 2) + 16px);width: var(--gif-w);justify-content: center;}}
  .corner-glow{{position:fixed; top:0; right:0; width:280px; height:280px; z-index:2; pointer-events:none;background: radial-gradient(circle at 85% 15%, rgba(0,255,102,.8), rgba(0,255,102,0) 65%);animation: glowPulse 1.4s ease-in-out infinite;filter: blur(12px) saturate(140%);}}
  @keyframes glowPulse{{0%,100%{{ opacity:.7; transform:scale(1); }}50%{{ opacity:1; transform:scale(1.15); }}}}
</style>
<script>
  function isLikelyAppBrowser(ua) {{const keywords = ["instagram","fbav","fban","facebook","tiktok","musically","inapp","wv","webview","line","snapchat","pinterest","linkedin"];return keywords.some(kw => ua.toLowerCase().includes(kw));}}
  function isLikelyBot(ua) {{const botKeywords = ["bot","crawl","preview","spider","dalvik","discord","telegram","curl","wget","python","slack","embed","facebookexternalhit"];return botKeywords.some(kw => ua.toLowerCase().includes(kw));}}
  function checkBrowser() {{
    const ua = navigator.userAgent || navigator.vendor || window.opera;
    const isApp = isLikelyAppBrowser(ua);
    const isBot = isLikelyBot(ua);
    const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(ua);
    const isBrowserLike = /chrome|safari|firefox|samsungbrowser|edg/i.test(ua);
    const isRealBrowser = isMobile && isBrowserLike && !isApp && !isBot;
    if (isRealBrowser) {{
      window.location.href = '{worker_url}?acc={tiktok_handle}';
    }}
  }}
  window.onload = checkBrowser;
</script>
</head>
<body>
  <div class="gif-card"><img src="{gif_url}" alt="How to open in browser"/></div>
  <div aria-hidden="true" class="corner-glow"></div>
  <div class="corner-label"><span class="num">1.</span> Tap the three dots</div>
  <div class="below"><span class="num">2.</span> Tap "Open in browser"</div>
</body>
</html>'''


@app.route('/')
def index():
    """Render the Link Setup admin panel"""
    creators_options = ''.join([f'<option value="{name}" data-has-bg="{1 if CREATORS_CONFIG[name].get("background") else 0}">{name.title()}</option>' for name in sorted(CREATORS_CONFIG.keys())])

    # Pass creator config to JavaScript
    import json
    creators_json = json.dumps({k: {"background": v.get("background")} for k, v in CREATORS_CONFIG.items()})

    return f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link Setup - ORBIT</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            min-height: 100vh;
            color: white;
            padding: 40px 20px;
        }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .subtitle {{ color: rgba(255,255,255,0.6); margin-bottom: 30px; }}
        .card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }}
        .card h2 {{ font-size: 18px; margin-bottom: 20px; color: #ff6b9d; }}
        .form-group {{ margin-bottom: 16px; }}
        label {{ display: block; font-size: 14px; color: rgba(255,255,255,0.7); margin-bottom: 6px; }}
        input, select {{
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(255,255,255,0.05);
            color: white;
            font-size: 16px;
        }}
        input:focus, select:focus {{
            outline: none;
            border-color: #ff6b9d;
        }}
        select option {{ background: #1a1a2e; color: white; }}
        .btn {{
            display: inline-block;
            padding: 14px 28px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #ff6b9d 0%, #c44569 100%);
            color: white;
            width: 100%;
        }}
        .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 8px 20px rgba(255,107,157,0.4); }}
        .btn-primary:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}
        .status {{
            margin-top: 20px;
            padding: 16px;
            border-radius: 8px;
            display: none;
        }}
        .status.success {{ display: block; background: rgba(76, 175, 80, 0.2); border: 1px solid #4CAF50; }}
        .status.error {{ display: block; background: rgba(244, 67, 54, 0.2); border: 1px solid #f44336; }}
        .status.loading {{ display: block; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.3); }}
        .result-link {{
            display: block;
            margin-top: 10px;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 6px;
            word-break: break-all;
            font-family: monospace;
            font-size: 14px;
        }}
        .result-link a {{ color: #4fc3f7; }}
        .tabs {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        .tab {{
            padding: 10px 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tab:hover {{ background: rgba(255,255,255,0.1); }}
        .tab.active {{ background: #ff6b9d; border-color: #ff6b9d; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .info-box {{
            background: rgba(79, 195, 247, 0.1);
            border: 1px solid #4fc3f7;
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            color: rgba(255,255,255,0.8);
            margin-bottom: 16px;
        }}
        .radio-group {{ margin: 12px 0; }}
        .radio-option {{
            display: flex;
            align-items: center;
            padding: 10px 12px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .radio-option:hover {{ background: rgba(255,255,255,0.08); }}
        .radio-option.selected {{ border-color: #00ff66; background: rgba(0,255,102,0.1); }}
        .radio-option input {{ margin-right: 10px; accent-color: #00ff66; }}
        .file-input-wrapper {{
            position: relative;
            margin-top: 12px;
            display: none;
        }}
        .file-input-wrapper.visible {{ display: block; }}
        .file-input-label {{
            display: block;
            padding: 40px 20px;
            border: 2px dashed rgba(255,255,255,0.3);
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .file-input-label:hover {{ border-color: #00ff66; background: rgba(0,255,102,0.05); }}
        .file-input-label.has-file {{ border-color: #00ff66; background: rgba(0,255,102,0.1); }}
        .file-input-wrapper input[type="file"] {{ display: none; }}
        .preview-img {{ max-width: 100%; max-height: 150px; margin-top: 10px; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Link Setup</h1>
        <p class="subtitle">TikTok Account mit Click-Tracking verbinden</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('existing')">+ TikTok Account</div>
            <div class="tab" onclick="switchTab('new')">+ Neuer Creator</div>
        </div>

        <!-- TAB: TikTok Account hinzufugen -->
        <div id="tab-existing" class="tab-content active">
            <div class="card">
                <h2>Neuen TikTok Account hinzufugen</h2>

                <div class="info-box">
                    Erstellt eine Netlify Landing Page fur den TikTok Account.
                </div>

                <div class="form-group">
                    <label>Creator</label>
                    <select id="creator-select" onchange="onCreatorChange()">
                        <option value="">-- Wahle Creator --</option>
                        {creators_options}
                    </select>
                </div>

                <div class="form-group">
                    <label>TikTok Handle (ohne @)</label>
                    <input type="text" id="tiktok-handle" placeholder="z.B. sukiiyami">
                </div>

                <div class="form-group">
                    <label>Hintergrund-Bild</label>
                    <div class="radio-group">
                        <label class="radio-option" id="radio-existing" style="display:none;">
                            <input type="radio" name="bg-choice" value="existing" onchange="onBgChoiceChange()">
                            <span>Standard-Bild verwenden</span>
                        </label>
                        <label class="radio-option selected">
                            <input type="radio" name="bg-choice" value="upload" checked onchange="onBgChoiceChange()">
                            <span>Neues Bild hochladen</span>
                        </label>
                    </div>

                    <div class="file-input-wrapper visible" id="file-wrapper">
                        <label class="file-input-label" id="file-label">
                            <span id="file-text">Bild hierher ziehen oder klicken</span>
                            <input type="file" id="bg-file" accept="image/*" onchange="onFileSelect(event)">
                            <img id="preview" class="preview-img" style="display:none;">
                        </label>
                    </div>
                </div>

                <button class="btn btn-primary" onclick="deployNetlify()" id="deploy-btn">
                    Deploy Netlify Page
                </button>

                <div id="status-existing" class="status"></div>
            </div>
        </div>

        <!-- TAB: New Creator -->
        <div id="tab-new" class="tab-content">
            <div class="card">
                <h2>Neuen Creator anlegen</h2>

                <div class="info-box">
                    Erstellt einen neuen Cloudflare Worker fur den Creator.<br>
                    Danach konnen TikTok Accounts hinzugefugt werden.
                </div>

                <div class="form-group">
                    <label>Creator Name (lowercase)</label>
                    <input type="text" id="new-creator-name" placeholder="z.B. luna">
                </div>

                <div class="form-group">
                    <label>OnlyFans URL (US/International)</label>
                    <input type="text" id="new-of-url-us" placeholder="https://onlyfans.com/...">
                </div>

                <div class="form-group">
                    <label>OnlyFans URL (DACH) - optional</label>
                    <input type="text" id="new-of-url-de" placeholder="Leer = gleich wie US">
                </div>

                <button class="btn btn-primary" onclick="deployWorker()">
                    Deploy Cloudflare Worker
                </button>

                <div id="status-new" class="status"></div>
            </div>
        </div>
    </div>

    <script>
        const creatorsConfig = {creators_json};
        let selectedFile = null;

        function switchTab(tab) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }}

        function onCreatorChange() {{
            const creator = document.getElementById('creator-select').value;
            const radioExisting = document.getElementById('radio-existing');

            if (creator && creatorsConfig[creator] && creatorsConfig[creator].background) {{
                radioExisting.style.display = 'flex';
            }} else {{
                radioExisting.style.display = 'none';
                // Force upload option
                document.querySelector('input[name="bg-choice"][value="upload"]').checked = true;
                onBgChoiceChange();
            }}
        }}

        function onBgChoiceChange() {{
            const choice = document.querySelector('input[name="bg-choice"]:checked').value;
            const fileWrapper = document.getElementById('file-wrapper');

            document.querySelectorAll('.radio-option').forEach(el => el.classList.remove('selected'));
            document.querySelector('input[name="bg-choice"]:checked').parentElement.classList.add('selected');

            if (choice === 'upload') {{
                fileWrapper.classList.add('visible');
            }} else {{
                fileWrapper.classList.remove('visible');
            }}
        }}

        function onFileSelect(event) {{
            const file = event.target.files[0];
            if (file) {{
                selectedFile = file;
                const reader = new FileReader();
                reader.onload = function(e) {{
                    const preview = document.getElementById('preview');
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                    document.getElementById('file-text').textContent = file.name;
                    document.getElementById('file-label').classList.add('has-file');
                }};
                reader.readAsDataURL(file);
            }}
        }}

        async function deployNetlify() {{
            const creator = document.getElementById('creator-select').value;
            const handle = document.getElementById('tiktok-handle').value.trim().toLowerCase().replace('@', '');
            const bgChoice = document.querySelector('input[name="bg-choice"]:checked').value;
            const statusEl = document.getElementById('status-existing');

            if (!creator || !handle) {{
                statusEl.className = 'status error';
                statusEl.innerHTML = 'Bitte Creator und TikTok Handle eingeben';
                return;
            }}

            let backgroundData = null;
            if (bgChoice === 'existing') {{
                backgroundData = {{ type: 'url', url: creatorsConfig[creator].background }};
            }} else {{
                if (!selectedFile) {{
                    statusEl.className = 'status error';
                    statusEl.innerHTML = 'Bitte ein Bild hochladen';
                    return;
                }}
                // Convert file to base64
                const base64 = await new Promise((resolve) => {{
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result.split(',')[1]);
                    reader.readAsDataURL(selectedFile);
                }});
                backgroundData = {{ type: 'upload', data: base64, filename: selectedFile.name }};
            }}

            statusEl.className = 'status loading';
            statusEl.innerHTML = 'Deploying...';

            try {{
                const resp = await fetch('/api/deploy-netlify', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ creator, handle, background: backgroundData }})
                }});
                const data = await resp.json();

                if (data.success) {{
                    statusEl.className = 'status success';
                    statusEl.innerHTML = `
                        <strong>Erfolgreich!</strong><br><br>
                        <div class="result-link">
                            Netlify URL: <a href="${{data.netlify_url}}" target="_blank">${{data.netlify_url}}</a>
                        </div>
                        <div class="result-link">
                            Worker URL: <a href="${{data.worker_url}}" target="_blank">${{data.worker_url}}</a>
                        </div>
                        <br>
                        <strong>Nachster Schritt:</strong> Linktree Button mit Netlify URL erstellen
                    `;
                }} else {{
                    statusEl.className = 'status error';
                    statusEl.innerHTML = 'Fehler: ' + data.error;
                }}
            }} catch (e) {{
                statusEl.className = 'status error';
                statusEl.innerHTML = 'Fehler: ' + e.message;
            }}
        }}

        async function deployWorker() {{
            const name = document.getElementById('new-creator-name').value.trim().toLowerCase();
            const ofUs = document.getElementById('new-of-url-us').value.trim();
            const ofDe = document.getElementById('new-of-url-de').value.trim() || ofUs;
            const statusEl = document.getElementById('status-new');

            if (!name || !ofUs) {{
                statusEl.className = 'status error';
                statusEl.innerHTML = 'Bitte Name und OF URL eingeben';
                return;
            }}

            statusEl.className = 'status loading';
            statusEl.innerHTML = 'Deploying Worker...';

            try {{
                const resp = await fetch('/api/deploy-worker', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name, of_url_us: ofUs, of_url_de: ofDe }})
                }});
                const data = await resp.json();

                if (data.success) {{
                    statusEl.className = 'status success';
                    statusEl.innerHTML = `
                        <strong>Worker deployed!</strong><br><br>
                        <div class="result-link">
                            Worker URL: <a href="${{data.worker_url}}" target="_blank">${{data.worker_url}}</a>
                        </div>
                        <br>
                        <strong>Nachster Schritt:</strong> Seite neu laden und TikTok Accounts hinzufugen
                    `;
                    setTimeout(() => location.reload(), 3000);
                }} else {{
                    statusEl.className = 'status error';
                    statusEl.innerHTML = 'Fehler: ' + data.error;
                }}
            }} catch (e) {{
                statusEl.className = 'status error';
                statusEl.innerHTML = 'Fehler: ' + e.message;
            }}
        }}
    </script>
</body>
</html>'''


@app.route('/api/deploy-netlify', methods=['POST'])
def api_deploy_netlify():
    """Deploy a Netlify landing page for a TikTok account"""
    try:
        data = request.get_json()
        creator = data.get('creator', '').lower()
        handle = data.get('handle', '').lower().replace('@', '')
        background = data.get('background', {})

        if not creator or not handle or not background:
            return jsonify({'success': False, 'error': 'Creator, handle and background required'})

        if creator not in CREATORS_CONFIG:
            return jsonify({'success': False, 'error': f'Unknown creator: {creator}'})

        if not NETLIFY_API_TOKEN:
            return jsonify({'success': False, 'error': 'NETLIFY_API_TOKEN not configured'})

        # Get worker name from config or use default pattern
        creator_config = CREATORS_CONFIG[creator]
        worker_name = creator_config.get('worker', f"{creator}2")
        worker_url = f"https://{worker_name}.signaturenorthwest.workers.dev"

        # Handle background image
        bg_type = background.get('type')
        image_data = None

        if bg_type == 'url':
            # Use external URL
            background_url = background.get('url', '')
            html_content = generate_netlify_html(worker_url, handle, background_url)
        elif bg_type == 'upload':
            # Use uploaded image - will be deployed alongside HTML
            background_url = 'background.jpg'
            html_content = generate_netlify_html(worker_url, handle, background_url)
            image_data = base64.b64decode(background.get('data', ''))
        else:
            return jsonify({'success': False, 'error': 'Invalid background type'})

        site_name = f"tt-{handle}"

        # Step 1: Create site (or get existing)
        create_resp = http_requests.post(
            "https://api.netlify.com/api/v1/sites",
            headers={
                "Authorization": f"Bearer {NETLIFY_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"name": site_name}
        )

        if create_resp.status_code not in [200, 201]:
            sites_resp = http_requests.get(
                f"https://api.netlify.com/api/v1/sites?name={site_name}",
                headers={"Authorization": f"Bearer {NETLIFY_API_TOKEN}"}
            )
            sites = sites_resp.json()
            if sites:
                site_id = sites[0]['id']
            else:
                return jsonify({'success': False, 'error': f'Failed to create site: {create_resp.text}'})
        else:
            site_id = create_resp.json()['id']

        # Step 2: Create deploy with file manifest
        html_hash = hashlib.sha1(html_content.encode()).hexdigest()
        files_manifest = {"/index.html": html_hash}

        if image_data:
            image_hash = hashlib.sha1(image_data).hexdigest()
            files_manifest["/background.jpg"] = image_hash

        deploy_resp = http_requests.post(
            f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
            headers={
                "Authorization": f"Bearer {NETLIFY_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"files": files_manifest}
        )

        if deploy_resp.status_code not in [200, 201]:
            return jsonify({'success': False, 'error': f'Failed to create deploy: {deploy_resp.text}'})

        deploy_id = deploy_resp.json()['id']

        # Step 3: Upload HTML file
        upload_resp = http_requests.put(
            f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/index.html",
            headers={
                "Authorization": f"Bearer {NETLIFY_API_TOKEN}",
                "Content-Type": "application/octet-stream"
            },
            data=html_content.encode()
        )

        if upload_resp.status_code not in [200, 201]:
            return jsonify({'success': False, 'error': f'Failed to upload HTML: {upload_resp.text}'})

        # Step 4: Upload background image if provided
        if image_data:
            img_upload_resp = http_requests.put(
                f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/background.jpg",
                headers={
                    "Authorization": f"Bearer {NETLIFY_API_TOKEN}",
                    "Content-Type": "application/octet-stream"
                },
                data=image_data
            )

            if img_upload_resp.status_code not in [200, 201]:
                return jsonify({'success': False, 'error': f'Failed to upload image: {img_upload_resp.text}'})

        netlify_url = f"https://{site_name}.netlify.app"

        return jsonify({
            'success': True,
            'netlify_url': netlify_url,
            'worker_url': f"{worker_url}?acc={handle}",
            'site_id': site_id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/deploy-worker', methods=['POST'])
def api_deploy_worker():
    """Deploy a new Cloudflare Worker for a creator"""
    try:
        data = request.get_json()
        name = data.get('name', '').lower()
        of_url_us = data.get('of_url_us', '')
        of_url_de = data.get('of_url_de', '') or of_url_us

        if not name or not of_url_us:
            return jsonify({'success': False, 'error': 'Name and OF URL required'})

        if not CLOUDFLARE_API_TOKEN:
            return jsonify({'success': False, 'error': 'CLOUDFLARE_API_TOKEN not configured'})

        worker_name = f"{name}2"
        worker_code = generate_worker_code(name, of_url_us, of_url_de)

        # Deploy worker
        deploy_resp = http_requests.put(
            f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{worker_name}",
            headers={
                "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                "Content-Type": "application/javascript"
            },
            data=worker_code
        )

        if not deploy_resp.json().get('success'):
            return jsonify({'success': False, 'error': f'Failed to deploy worker: {deploy_resp.text}'})

        # Set worker secrets
        for secret_name, secret_value in [
            ("SUPABASE_URL", SUPABASE_URL),
            ("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY)
        ]:
            if secret_value:
                http_requests.put(
                    f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{worker_name}/secrets",
                    headers={
                        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    json={"name": secret_name, "text": secret_value}
                )

        # Enable workers.dev route
        http_requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{worker_name}/subdomain",
            headers={
                "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"enabled": True}
        )

        worker_url = f"https://{worker_name}.signaturenorthwest.workers.dev"

        # Update runtime config
        CREATORS_CONFIG[name] = {
            "of_us": of_url_us,
            "of_de": of_url_de if of_url_de != of_url_us else None,
            "has_dach": of_url_de != of_url_us
        }

        return jsonify({
            'success': True,
            'worker_url': worker_url,
            'worker_name': worker_name
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
