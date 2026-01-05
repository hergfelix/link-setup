#!/usr/bin/env python3
"""
ORBIT Link Setup - TikTok Account Deployment Tool
Deploys Netlify landing pages and Cloudflare Workers for click tracking
"""

from flask import Flask, Response, request, jsonify
import requests as http_requests
import hashlib
import os

app = Flask(__name__)

# Configuration
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = "ac958f158fdec62e9941d8de02bf2ac2"
NETLIFY_API_TOKEN = os.environ.get("NETLIFY_API_TOKEN", "")
SUPABASE_URL = "https://utzkvosladgdsbpujozu.supabase.co"
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Active creators with their OF URLs
CREATORS_CONFIG = {
    "miriam": {"of_us": "https://onlyfans.com/milosmiriam", "of_de": "https://onlyfans.com/miriamxde", "has_dach": True},
    "aurelia": {"of_us": "https://onlyfans.com/aurelialuv", "of_de": "https://onlyfans.com/aureliaxde", "has_dach": True},
    "naomi": {"of_us": "https://onlyfans.com/naomidoee", "of_de": None, "has_dach": False},
    "mara": {"of_us": "https://onlyfans.com/maraxluv", "of_de": None, "has_dach": False},
    "megan": {"of_us": "https://onlyfans.com/megluuvvv", "of_de": None, "has_dach": False},
    "selena": {"of_us": "https://onlyfans.com/selenawrld", "of_de": None, "has_dach": False},
    "sofia": {"of_us": "https://onlyfans.com/sofiasynn", "of_de": None, "has_dach": False},
    "nalani": {"of_us": "https://onlyfans.com/nalaniluv", "of_de": None, "has_dach": False},
    "suki": {"of_us": "https://onlyfans.com/sukixdarling", "of_de": None, "has_dach": False},
    "mira": {"of_us": "https://onlyfans.com/miraswrld", "of_de": None, "has_dach": False},
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


def generate_netlify_html(worker_url, tiktok_handle, creator_name):
    """Generate Netlify landing page HTML - only redirects on mobile + real browser"""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Open in Browser</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #0f0f1a 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
            padding: 20px;
        }}
        .container {{
            text-align: center;
            max-width: 360px;
            width: 100%;
        }}
        .gif-card {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(0, 255, 136, 0.2);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 0 40px rgba(0, 255, 136, 0.1);
        }}
        .gif-container {{
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 16px;
        }}
        .gif-container img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .instructions {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
        }}
        .step {{
            display: flex;
            align-items: center;
            text-align: left;
            margin-bottom: 16px;
        }}
        .step:last-child {{ margin-bottom: 0; }}
        .step-number {{
            width: 28px;
            height: 28px;
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14px;
            color: #0f0f1a;
            margin-right: 14px;
            flex-shrink: 0;
            box-shadow: 0 0 15px rgba(0, 255, 136, 0.4);
        }}
        .step-text {{
            font-size: 15px;
            color: rgba(255, 255, 255, 0.9);
            line-height: 1.4;
        }}
        .step-text strong {{
            color: #00ff88;
        }}
        .cta-button {{
            display: block;
            width: 100%;
            padding: 18px 32px;
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #0f0f1a;
            text-decoration: none;
            border-radius: 14px;
            font-weight: 700;
            font-size: 17px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 20px rgba(0, 255, 136, 0.3);
        }}
        .cta-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 255, 136, 0.5);
        }}
        .cta-button:active {{
            transform: translateY(0);
        }}
        .footer-text {{
            margin-top: 20px;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.4);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="gif-card">
            <div class="gif-container">
                <img src="https://i.imgur.com/qJyqv6V.gif" alt="How to open in browser">
            </div>
        </div>

        <div class="instructions">
            <div class="step">
                <div class="step-number">1</div>
                <div class="step-text">Tap the <strong>three dots</strong> (...) in the top right</div>
            </div>
            <div class="step">
                <div class="step-number">2</div>
                <div class="step-text">Select <strong>"Open in Browser"</strong></div>
            </div>
            <div class="step">
                <div class="step-number">3</div>
                <div class="step-text">Then tap the button below</div>
            </div>
        </div>

        <a href="{worker_url}?acc={tiktok_handle}" class="cta-button" id="ctaButton">
            Continue
        </a>

        <p class="footer-text">Works best in Safari or Chrome</p>
    </div>

    <script>
        function isLikelyAppBrowser(ua) {{
            const keywords = [
                "instagram", "fbav", "fban", "facebook", "tiktok", "musically",
                "inapp", "wv", "webview", "line", "snapchat", "pinterest", "linkedin"
            ];
            return keywords.some(kw => ua.toLowerCase().includes(kw));
        }}

        function isLikelyBot(ua) {{
            const botKeywords = [
                "bot", "crawl", "preview", "spider", "dalvik", "discord", "telegram",
                "curl", "wget", "python", "slack", "embed", "facebookexternalhit"
            ];
            return botKeywords.some(kw => ua.toLowerCase().includes(kw));
        }}

        function checkBrowser() {{
            const ua = navigator.userAgent || navigator.vendor || window.opera;
            const isApp = isLikelyAppBrowser(ua);
            const isBot = isLikelyBot(ua);
            const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(ua);
            const isBrowserLike = /chrome|safari|firefox|samsungbrowser|edg/i.test(ua);

            // Only redirect on: mobile + real browser (not in-app, not bot)
            const isRealBrowser = isMobile && isBrowserLike && !isApp && !isBot;

            if (isRealBrowser) {{
                window.location.href = "{worker_url}?acc={tiktok_handle}";
            }}
        }}

        window.onload = checkBrowser;
    </script>
</body>
</html>'''


@app.route('/')
def index():
    """Render the Link Setup admin panel"""
    creators_options = ''.join([f'<option value="{name}">{name.title()}</option>' for name in sorted(CREATORS_CONFIG.keys())])

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
    </style>
</head>
<body>
    <div class="container">
        <h1>Link Setup</h1>
        <p class="subtitle">TikTok Account mit Click-Tracking verbinden</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('existing')">Bestehender Creator</div>
            <div class="tab" onclick="switchTab('new')">Neuer Creator</div>
        </div>

        <!-- TAB: Existing Creator -->
        <div id="tab-existing" class="tab-content active">
            <div class="card">
                <h2>Neuen TikTok Account hinzufugen</h2>

                <div class="info-box">
                    Erstellt eine Netlify Landing Page fur den TikTok Account.<br>
                    Der Cloudflare Worker fur diesen Creator existiert bereits.
                </div>

                <div class="form-group">
                    <label>Creator auswahlen</label>
                    <select id="creator-select">
                        <option value="">-- Wahle Creator --</option>
                        {creators_options}
                    </select>
                </div>

                <div class="form-group">
                    <label>TikTok Handle (ohne @)</label>
                    <input type="text" id="tiktok-handle" placeholder="z.B. glowingmiriam">
                </div>

                <button class="btn btn-primary" onclick="deployNetlify()">
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
        function switchTab(tab) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }}

        async function deployNetlify() {{
            const creator = document.getElementById('creator-select').value;
            const handle = document.getElementById('tiktok-handle').value.trim().toLowerCase().replace('@', '');
            const statusEl = document.getElementById('status-existing');

            if (!creator || !handle) {{
                statusEl.className = 'status error';
                statusEl.innerHTML = 'Bitte Creator und TikTok Handle eingeben';
                return;
            }}

            statusEl.className = 'status loading';
            statusEl.innerHTML = 'Deploying...';

            try {{
                const resp = await fetch('/api/deploy-netlify', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ creator, handle }})
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

        if not creator or not handle:
            return jsonify({'success': False, 'error': 'Creator and handle required'})

        if creator not in CREATORS_CONFIG:
            return jsonify({'success': False, 'error': f'Unknown creator: {creator}'})

        if not NETLIFY_API_TOKEN:
            return jsonify({'success': False, 'error': 'NETLIFY_API_TOKEN not configured'})

        worker_url = f"https://{creator}2.signaturenorthwest.workers.dev"
        html_content = generate_netlify_html(worker_url, handle, creator)

        site_name = f"tt-{handle}"

        # Step 1: Create site
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

        # Step 2: Deploy HTML content
        file_hash = hashlib.sha1(html_content.encode()).hexdigest()

        deploy_resp = http_requests.post(
            f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
            headers={
                "Authorization": f"Bearer {NETLIFY_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"files": {"/index.html": file_hash}}
        )

        if deploy_resp.status_code not in [200, 201]:
            return jsonify({'success': False, 'error': f'Failed to create deploy: {deploy_resp.text}'})

        deploy_id = deploy_resp.json()['id']

        # Step 3: Upload the file
        upload_resp = http_requests.put(
            f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/index.html",
            headers={
                "Authorization": f"Bearer {NETLIFY_API_TOKEN}",
                "Content-Type": "application/octet-stream"
            },
            data=html_content.encode()
        )

        if upload_resp.status_code not in [200, 201]:
            return jsonify({'success': False, 'error': f'Failed to upload file: {upload_resp.text}'})

        netlify_url = f"https://{site_name}.netlify.app"

        return jsonify({
            'success': True,
            'netlify_url': netlify_url,
            'worker_url': f"{worker_url}?acc={handle}&model={creator}",
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
