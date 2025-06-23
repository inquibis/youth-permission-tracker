import pytest

@pytest.mark.asyncio
async def test_parental_permission_ui(page, base_url="http://localhost:8000"):
    token = "validtoken123"  # this should be seeded in DB for test

    await page.goto(f"{base_url}/parental-permission.html?token={token}")
    await page.wait_for_selector("#userName")

    # Confirm fields appear
    assert await page.locator("#userName").text_content() != ""
    assert await page.locator("#activityName").text_content() != ""

    # Check button initially disabled
    assert await page.locator("#submitBtn").is_disabled()

    # Click confirm checkbox
    await page.click("#confirmCheck")

    # Now button should be enabled
    assert not await page.locator("#submitBtn").is_disabled()

    # Click submit
    await page.click("#submitBtn")

    # Wait for success message
    await page.wait_for_selector("#success")
    assert "Thank you" in await page.locator("#success").text_content()
