"""TC001-TC038: Home Search acceptance tests.

Set SEARCH_TEST_DATA to a JSON file containing inspected selectors and stable
course-specific test values. Tests log in once, reuse that authenticated Appium
session for the entire module, and reset navigation to Home before each case.
"""

import pytest


pytestmark = [pytest.mark.home_search, pytest.mark.sends_otp, pytest.mark.requires_valid_otp]


@pytest.fixture
def opened_search(search_page):
    search_page.open()
    return search_page


def expected(search_data, kind):
    values = search_data["results"].get(kind)
    assert values, f"Configure at least one expected {kind} result"
    return values


def assert_matches(page, labels):
    actual = page.result_labels()
    assert actual, "No search results were displayed"
    assert all(any(expected.casefold() in value.casefold() for value in actual)
               for expected in labels)


def search_and_filter(page, data, category, result_kind):
    page.search(data["valid_keyword"])
    page.select_category(category)
    assert_matches(page, expected(data, result_kind))
    assert all(result_kind.rstrip("s").casefold() in item.casefold()
               for item in page.result_types()), f"Non-{result_kind} result displayed"


def test_tc001_search_available_on_home(search_page):
    element = search_page.element(search_page.locator("home_search"))
    assert element.is_displayed() and element.is_enabled()


def test_tc002_click_search_opens_page(search_page):
    search_page.open()
    assert search_page.displayed("search_field")


def test_tc003_default_search_page_ui(opened_search):
    for name in ("back", "search_field", "browse_subjects", "browse_resources"):
        assert opened_search.displayed(name), f"{name} is not displayed"


def test_tc004_default_search_placeholder(opened_search, search_data):
    assert search_data["placeholder"] in opened_search.placeholder()


def test_tc005_browse_subjects(opened_search, search_data):
    assert {opened_search.label(item) for item in opened_search.items("subject_items")} == set(search_data["subjects"])
    assert all(item.find_elements(*opened_search.locator("item_icon")) for item in opened_search.items("subject_items"))


def test_tc006_browse_resources(opened_search, search_data):
    assert {opened_search.label(item) for item in opened_search.items("resource_items")} == set(search_data["resources"])
    assert all(item.find_elements(*opened_search.locator("item_icon")) for item in opened_search.items("resource_items"))


def test_tc007_subject_opens_chapter_list(opened_search, search_data):
    opened_search.open_named(search_data["subjects"][0])
    assert opened_search.named_visible(search_data["destinations"]["chapter_list"])


def test_tc008_resource_opens_resource_page(opened_search, search_data):
    opened_search.open_named(search_data["resources"][0])
    assert opened_search.named_visible(search_data["destinations"]["resource"])


def test_tc009_back_returns_home(opened_search):
    opened_search.back_to_home()
    assert opened_search.displayed("home")


def test_tc010_valid_keyword(opened_search, search_data):
    opened_search.search(search_data["valid_keyword"])
    assert_matches(opened_search, expected(search_data, "all"))


def test_tc011_invalid_keyword(opened_search, search_data):
    opened_search.search(search_data["invalid_keyword"])
    assert opened_search.displayed("no_results")


def test_tc012_partial_content_name(opened_search, search_data):
    opened_search.search(search_data["partial_keyword"])
    assert_matches(opened_search, expected(search_data, "partial"))


def test_tc013_search_is_case_insensitive(opened_search, search_data):
    opened_search.search(search_data["case_keyword"].lower())
    lower = set(opened_search.result_labels())
    opened_search.search(search_data["case_keyword"].upper())
    assert lower == set(opened_search.result_labels()) and lower


def test_tc014_search_trims_spaces(opened_search, search_data):
    keyword = search_data["valid_keyword"]
    opened_search.search(keyword)
    baseline = set(opened_search.result_labels())
    opened_search.search(f"  {keyword}  ")
    assert set(opened_search.result_labels()) == baseline and baseline


def test_tc015_clear_search(opened_search, search_data):
    opened_search.search(search_data["valid_keyword"])
    opened_search.clear_search()
    assert not opened_search.results()
    assert opened_search.displayed("browse_subjects")


def test_tc016_search_result_categories(opened_search, search_data):
    opened_search.search(search_data["valid_keyword"])
    assert all(opened_search.is_visible(opened_search.category_locator(name)) for name in opened_search.CATEGORIES)


def test_tc017_all_category(opened_search, search_data):
    opened_search.search(search_data["valid_keyword"])
    opened_search.select_category("All")
    assert_matches(opened_search, expected(search_data, "all"))


def test_tc018_chapters_category(opened_search, search_data):
    search_and_filter(opened_search, search_data, "Chapters", "chapters")


def test_tc019_topics_category(opened_search, search_data):
    search_and_filter(opened_search, search_data, "Topics", "topics")


def test_tc020_subtopics_category(opened_search, search_data):
    search_and_filter(opened_search, search_data, "Subtopics", "subtopics")


def test_tc021_resources_category(opened_search, search_data):
    search_and_filter(opened_search, search_data, "Resources", "resources")


def assert_result_type(page, data, kind):
    """Verify the result row and its independently exposed right-side type."""
    search_and_filter(page, data, kind.title(), kind)
    assert page.result_types(), "No result type/status values were exposed"
    assert all(kind.rstrip("s").casefold() in value.casefold() for value in page.result_types())


def test_tc022_chapter_result_type_status(opened_search, search_data):
    assert_result_type(opened_search, search_data, "chapters")


def test_tc023_topic_result_type_status(opened_search, search_data):
    assert_result_type(opened_search, search_data, "topics")


def test_tc024_subtopic_result_type_status(opened_search, search_data):
    assert_result_type(opened_search, search_data, "subtopics")


def test_tc025_resource_has_no_right_status(opened_search, search_data):
    opened_search.search(search_data["valid_keyword"])
    opened_search.select_category("Resources")
    assert opened_search.results() and all(not value for value in opened_search.result_types())


def open_result(page, data, kind, destination):
    page.search(data["valid_keyword"])
    page.select_category(kind.title())
    page.open_named(expected(data, kind)[0])
    assert page.named_visible(data["destinations"][destination])


def test_tc026_click_chapter_result(opened_search, search_data):
    open_result(opened_search, search_data, "chapters", "chapter")


def test_tc027_click_topic_result(opened_search, search_data):
    open_result(opened_search, search_data, "topics", "topic")


def test_tc028_click_subtopic_result(opened_search, search_data):
    open_result(opened_search, search_data, "subtopics", "subtopic")


def test_tc029_click_resource_result(opened_search, search_data):
    open_result(opened_search, search_data, "resources", "resource")


def assert_recent(page, data, kind):
    value = data["recent"][kind]
    page.search(value)
    page.open_named(value)
    page.driver.back()
    page.clear_search()
    assert page.displayed("recent_searches") and page.named_visible(value)


def test_tc030_recent_search_subject(opened_search, search_data):
    assert_recent(opened_search, search_data, "subjects")


def test_tc031_recent_search_chapter(opened_search, search_data):
    assert_recent(opened_search, search_data, "chapters")


def test_tc032_recent_search_topic(opened_search, search_data):
    assert_recent(opened_search, search_data, "topics")


def test_tc033_recent_search_subtopic(opened_search, search_data):
    assert_recent(opened_search, search_data, "subtopics")


def test_tc034_resources_not_in_recent_searches(opened_search, search_data):
    value = search_data["recent"]["resources"]
    opened_search.search(value)
    opened_search.open_named(value)
    opened_search.driver.back()
    opened_search.clear_search()
    assert not opened_search.named_visible(value, timeout=2)


def test_tc035_live_content_not_searchable(opened_search, search_data):
    opened_search.search(search_data["live_keyword"])
    assert not any(search_data["live_result"].casefold() in label.casefold()
                   for label in opened_search.result_labels())


def test_tc036_special_characters_do_not_crash(opened_search):
    for value in ("!@#$%^&*()", "'\"<>/\\", "[]{}+=_"):
        opened_search.search(value, wait_for_results=False)
        assert opened_search.displayed("search_field")


def test_tc037_no_internet_error(opened_search, request):
    try:
        controller = request.getfixturevalue("search_network_controller")
    except pytest.FixtureLookupError:
        pytest.skip("Provide search_network_controller to safely disable and restore device networking")
    with controller.offline():
        opened_search.search("network-check", wait_for_results=False)
        assert opened_search.displayed("network_error", timeout=20)


def test_tc038_results_load_once_and_completely(opened_search, search_data):
    opened_search.search(search_data["valid_keyword"], wait_for_results=False)
    opened_search.assert_unique_complete_results(expected(search_data, "all"))
