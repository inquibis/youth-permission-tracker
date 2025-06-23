import pytest

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Get result of test
    outcome = yield
    rep = outcome.get_result()

    # Only act on failures
    if rep.when == "call" and rep.failed:
        page = item.funcargs.get("page")
        if page:
            screenshot_path = f"screenshots/{item.name}.png"
            page.screenshot(path=screenshot_path)
            print(f"📸 Screenshot saved to {screenshot_path}")