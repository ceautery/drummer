from playwright.sync_api import Page, expect


def test_app_loads(page: Page, server_url: str) -> None:
    page.goto(server_url)
    expect(page.get_by_test_id("request-tree")).to_be_visible(timeout=10_000)


def test_select_request_populates_editor(page: Page, server_url: str) -> None:
    page.goto(server_url)
    expect(page.get_by_test_id("request-tree")).to_be_visible(timeout=10_000)
    page.get_by_test_id("tree-node-hello/get-hello.md").click()
    expect(page.get_by_test_id("url-input")).to_be_visible()


def test_send_request_shows_status(page: Page, server_url: str) -> None:
    page.goto(server_url)
    expect(page.get_by_test_id("request-tree")).to_be_visible(timeout=10_000)
    page.get_by_test_id("tree-node-hello/get-hello.md").click()
    page.get_by_test_id("send-button").click()
    expect(page.get_by_test_id("response-status")).to_be_visible(timeout=15_000)
