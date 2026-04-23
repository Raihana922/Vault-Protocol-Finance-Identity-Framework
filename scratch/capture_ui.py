import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        base_url = "http://127.0.0.1:5002"
        images_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "images")
        
        # Log in as Admin
        await page.goto(f"{base_url}/login")
        await page.fill("input[name='email']", "25177@yenepoya.edu.in")
        await page.fill("input[name='password']", "Rai@yenepoya.")
        await page.click("button[type='submit']")
        await page.wait_for_timeout(1000)
        
        # MFA Setup Page
        await page.goto(f"{base_url}/setup-2fa")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(images_dir, "setup_2fa.png"))
        
        # Logout Admin
        await page.goto(f"{base_url}/logout")
        
        # MFA Verify Page (Triggered by login if 2FA is enabled, but we can force load the template or just use reset/mfa)
        # Actually, let's just trigger reset/mfa
        await page.goto(f"{base_url}/reset-password")
        await page.fill("input[name='email']", "25177@yenepoya.edu.in")
        await page.click("button[type='submit']")
        await page.wait_for_timeout(1000)
        # Assuming admin has no 2FA yet, it goes to fallback. Let's just screenshot setup_2fa for now.
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
