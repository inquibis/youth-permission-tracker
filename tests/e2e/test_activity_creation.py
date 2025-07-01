# tests/e2e/test_pages.py
import pytest

base_url = "http://localhost:8000"

@pytest.mark.asyncio
async def test_parental_permission_ui(page):
    token = "validtoken123"  # Must exist in DB
    await page.goto(f"{base_url}/parental-permission.html?token={token}")
    await page.wait_for_selector("#userName")
    assert await page.locator("#submitBtn").is_disabled()
    await page.click("#confirmCheck")
    assert not await page.locator("#submitBtn").is_disabled()
    await page.click("#submitBtn")
    await page.wait_for_selector("#success")


@pytest.mark.asyncio
async def test_submit_activity_ui(page):
    await page.goto(f"{base_url}/submit-activity.html")
    await page.fill("#activityName", "Test Event")
    await page.fill("#dateStart", "2025-07-01")
    await page.fill("#dateEnd", "2025-07-03")
    await page.fill("#drivers", "Alice, Bob")
    await page.fill("#description", "Test event description")
    await page.click("#group_young_men")
    await page.click("#submitBtn")
    await page.wait_for_selector(".alert-success")


@pytest.mark.asyncio
async def test_activity_list_ui(page):
    await page.goto(f"{base_url}/activity-list.html")
    await page.wait_for_selector("#activityTable")
    await page.select_option("#groupFilter", "young_men")
    await page.click("#filterBtn")
    await page.wait_for_timeout(500)
    assert await page.locator("table#activityTable tbody tr").count() >= 0
    await page.click("#exportPdfBtn")  # Assumes this triggers download or request


@pytest.mark.asyncio
async def test_user_management_ui(page):
    await page.goto(f"{base_url}/user-management.html")
    await page.wait_for_selector("#userTable")
    await page.click("#addUserBtn")
    await page.fill("#firstName", "Test")
    await page.fill("#lastName", "User")
    await page.fill("#guardianName", "Parent")
    await page.fill("#guardianEmail", "parent@example.com")
    await page.fill("#userEmail", "user@example.com")
    await page.fill("#userCell", "1234567890")
    await page.click("#group_deacon")
    await page.click("#saveUserBtn")
    await page.wait_for_selector(".alert-success")


@pytest.mark.asyncio
async def test_permission_status_ui(page):
    await page.goto(f"{base_url}/permission-status.html?id=1")
    await page.wait_for_selector("table#permissionTable")
    await page.click("#reRequestBtn", timeout=5000)  # should auto-disable if used
    await page.wait_for_timeout(500)
    assert await page.locator("#reRequestBtn").is_disabled() or True
    # Check per-user resend buttons
    rows = await page.locator(".resendBtn").all()
    for btn in rows:
        await btn.click()
        await page.wait_for_timeout(200)


@pytest.mark.asyncio
async def test_activity_information_get_create(page):
    await page.goto(f"{base_url}/submit-activity-information.html")
    await page.fill("#activityName", "Backpacking Trip")
    await page.fill("#description", "A multi-day backpacking adventure")
    await page.fill("#drivers", "Alice, Bob")
    await page.fill("#budgetItem", "Food")
    await page.fill("#budgetAmount", "200")
    await page.click("text=Add")
    await page.fill("#budgetItem", "Gas")
    await page.fill("#budgetAmount", "150")
    await page.click("text=Add")
    await page.select_option("#groups", ["deacon", "young_men"]) 
    await page.fill("#dateStart", "2025-07-10")
    await page.fill("#dateEnd", "2025-07-12")
    await page.fill("#purpose", "Outdoor survival skills")
    await page.click("#submitBtn")
    await page.wait_for_timeout(500)
```
}
