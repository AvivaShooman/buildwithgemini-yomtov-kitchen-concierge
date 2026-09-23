#!/usr/bin/env python3
"""Automate browser interaction and record a high-definition demo video of YomTov Kitchen Concierge."""

import os
import shutil
import subprocess
import time
from playwright.sync_api import sync_playwright

RECORD_DIR = "/config/Desktop/BuildWithGemini/yomtov-kitchen-concierge/recorded_video_raw"
OUTPUT_MP4 = "/config/Desktop/BuildWithGemini/yomtov-kitchen-concierge/demo_video.mp4"
ARTIFACT_MP4 = "/config/.gemini/antigravity/brain/5314d775-9241-451d-885e-dc46e2dd5e0a/demo_video.mp4"
TARGET_URL = "http://127.0.0.1:8080"


def smooth_type(page, selector: str, text: str, delay_ms: int = 18):
    """Type text into a field with natural human rhythm."""
    page.click(selector)
    for char in text:
        page.type(selector, char, delay=delay_ms)


def smooth_scroll_bottom(page, duration_sec: float = 2.0):
    """Smoothly scroll the chat container to the bottom."""
    page.evaluate("""
        const l = document.getElementById("log");
        const c = document.getElementById("chat-container");
        if (l) l.scrollTo({ top: l.scrollHeight, behavior: 'smooth' });
        if (c) c.scrollTo({ top: c.scrollHeight, behavior: 'smooth' });
        const lastMsg = document.querySelector(".msg-row:last-child");
        if (lastMsg) lastMsg.scrollIntoView({ behavior: 'smooth', block: 'end' });
    """)
    time.sleep(duration_sec)


def scroll_to_element(page, selector: str, block: str = "center", duration_sec: float = 2.0):
    """Smoothly scroll an element into view."""
    page.evaluate(f"""
        const el = document.querySelector("{selector}");
        if (el) {{
            el.scrollIntoView({{ behavior: 'smooth', block: '{block}' }});
        }}
    """)
    time.sleep(duration_sec)


def send_and_wait(page, prompt_text: str, timeout: int = 120):
    """Submit a prompt and wait until the agent finishes streaming its response."""
    initial_agent_count = page.locator(".msg-row.agent").count()

    print(f"✍️  Typing: \"{prompt_text[:70]}...\"")
    smooth_type(page, "#input", prompt_text, delay_ms=18)
    time.sleep(0.8)

    print("🚀 Submitting message...")
    page.click("#send-btn")

    print("⏳ Waiting for agent response...")
    start = time.time()
    while time.time() - start < timeout:
        current_count = page.locator(".msg-row.agent").count()
        if current_count > initial_agent_count:
            last_agent = page.locator(".msg-row.agent").last
            is_typing = last_agent.locator(".typing-indicator, .typing-dot").count() > 0
            if not is_typing:
                has_content = last_agent.locator(".markdown-body, .rich, img").count() > 0
                if has_content:
                    print("✅ Agent reply fully received and rendered!")
                    return
        time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for reply to: {prompt_text[:40]}")


def record_demo():
    if os.path.exists(RECORD_DIR):
        shutil.rmtree(RECORD_DIR)
    os.makedirs(RECORD_DIR, exist_ok=True)

    print(f"🎬 Starting Playwright browser recording pointing to {TARGET_URL}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--window-size=1280,800",
            ],
        )

        context = browser.new_context(
            record_video_dir=RECORD_DIR,
            record_video_size={"width": 1280, "height": 800},
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1.0,
        )

        page = context.new_page()

        # 1. Navigate to YomTov Kitchen Concierge UI
        print("🌐 Loading YomTov Kitchen Concierge UI...")
        page.goto(TARGET_URL, wait_until="networkidle")
        time.sleep(2.0)

        # 2. Showcase Header, Holiday Selector, & Dietary Filter Chips
        print("✨ Demonstrating UI features: Holiday Selector & Filter Chips...")
        page.hover(".header-title")
        time.sleep(1.0)

        # Select 'Rosh Hashanah' from the holiday context dropdown
        page.select_option("#holiday-select", "Rosh Hashanah")
        time.sleep(1.2)

        # Toggle 'Gluten-Free' filter chip
        gf_chip = page.locator('.toggle-chip[data-pref="Gluten-Free"]')
        if gf_chip.count() > 0:
            gf_chip.click()
            time.sleep(0.7)

        # Toggle 'Blech Setup' filter chip
        blech_chip = page.locator('.toggle-chip[data-pref="Blech Setup"]')
        if blech_chip.count() > 0:
            blech_chip.click()
            time.sleep(0.7)

        time.sleep(1.0)

        # 3. SCENE 1: WHAT THE APP DOES BEST
        # Core strength: Yom Tov & Shabbat menu planning with strict allergy restrictions,
        # Hebcal Jewish calendar integration, and blech staging schedule.
        prompt_1 = (
            "I have 8 guests for Rosh Hashanah & Shabbat in Brooklyn, NY. "
            "Two guests are strictly gluten-free, nut-free, and sesame-free. "
            "Can you design a warming-friendly Friday night dinner menu and calculate "
            "when each dish needs to go on the blech before candle lighting?"
        )
        send_and_wait(page, prompt_1, timeout=120)
        time.sleep(1.5)

        print("📜 Scrolling through Blech Warming Schedule & Halachic Deadlines...")
        scroll_to_element(page, ".msg-row.agent:nth-of-type(1)", block="start", duration_sec=2.0)
        time.sleep(4.0)
        smooth_scroll_bottom(page, duration_sec=2.5)
        time.sleep(4.0)

        # 4. SCENE 2: RICHER PROMPT (TOOL CALL + GENERATED IMAGE)
        # Demonstrates gemini-3.1-flash-lite-image holiday visual generation
        prompt_2 = (
            "Can you generate a photo of our festive Rosh Hashanah dinner table "
            "with the braised brisket, apples & honey, and lit Shabbat candles?"
        )
        send_and_wait(page, prompt_2, timeout=120)
        time.sleep(1.5)

        print("🖼️ Scrolling down to showcase the generated holiday table image...")
        scroll_to_element(page, ".msg-row.agent:nth-of-type(2)", block="center", duration_sec=2.0)
        time.sleep(6.0)

        # 5. SCENE 3: RICHER PROMPT (TOOL CALL + DATABASE LOOKUP + FIRESTORE PERSISTENCE)
        # Demonstrates multi-recipe grocery list scaling across supermarket aisles & Firestore storage
        prompt_3 = (
            "This is wonderful! Now please generate the consolidated grocery list for our 8 guests "
            "for this dinner menu and save it to Firestore."
        )
        send_and_wait(page, prompt_3, timeout=120)
        time.sleep(1.5)

        print("🛒 Scrolling down to showcase the consolidated scaled grocery list...")
        scroll_to_element(page, ".msg-row.agent:nth-of-type(3)", block="center", duration_sec=2.0)
        time.sleep(5.0)
        smooth_scroll_bottom(page, duration_sec=2.5)
        time.sleep(6.0)

        # Final pause on the complete workspace
        time.sleep(2.0)

        print("🏁 Finalizing video capture...")
        page.close()
        context.close()
        browser.close()

    # Find recorded webm file
    webm_files = [f for f in os.listdir(RECORD_DIR) if f.endswith(".webm")]
    if not webm_files:
        raise RuntimeError(f"No webm video found in {RECORD_DIR}")

    raw_video_path = os.path.join(RECORD_DIR, webm_files[0])
    print(f"📹 Raw video recorded: {raw_video_path} ({os.path.getsize(raw_video_path)} bytes)")

    # Convert to MP4 with H.264 video codec
    print("🔄 Encoding to universal MP4 (H.264) with ffmpeg...")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        raw_video_path,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        OUTPUT_MP4,
    ]
    subprocess.run(cmd, check=True)

    # Copy to artifacts directory
    shutil.copy2(OUTPUT_MP4, ARTIFACT_MP4)

    print(f"🎉 Demo video successfully generated!")
    print(f"   Saved to: {OUTPUT_MP4} ({os.path.getsize(OUTPUT_MP4)} bytes)")
    print(f"   Artifact: {ARTIFACT_MP4}")


if __name__ == "__main__":
    record_demo()
