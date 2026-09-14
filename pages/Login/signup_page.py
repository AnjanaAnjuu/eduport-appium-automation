"""Enter Your Details page object; label defaults follow the supplied UI contract.

Confirm these defaults in Inspector before a live run. Override locators/selected
markers through signup_data.json when Flutter exposes different semantics.
"""
from dataclasses import dataclass

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from pages.base_page import BasePage


@dataclass(frozen=True)
class SignupSubmissionEvidence:
    successful_submissions: int
    course_navigations: int
    profiles_created: int

    @classmethod
    def from_mapping(cls, values):
        keys = ('successful_submissions', 'course_navigations', 'profiles_created')
        if any(type(values.get(key)) is not int or values[key] < 0 for key in keys):
            raise ValueError('Submission probe must return nonnegative integer authoritative counters')
        return cls(*(values[key] for key in keys))

    def delta(self, before):
        return SignupSubmissionEvidence(*(getattr(self, key) - getattr(before, key)
            for key in ('successful_submissions', 'course_navigations', 'profiles_created')))


class SignupPage(BasePage):
    SCREEN = (AppiumBy.XPATH, "//*[@content-desc='Enter Your Details' or @text='Enter Your Details']")
    NAME_FIELD = (AppiumBy.CLASS_NAME, 'android.widget.EditText')
    FEMALE = (AppiumBy.XPATH, "//*[@content-desc='Female' or @text='Female']")
    MALE = (AppiumBy.XPATH, "//*[@content-desc='Male' or @text='Male']")
    SAVE_CONTINUE = (AppiumBy.XPATH, "//*[@content-desc='Save & Continue' or @text='Save & Continue']")
    COURSE_SELECTION = (AppiumBy.XPATH, "//*[@content-desc='Course Selection' or @text='Course Selection']")
    DEFAULTS = {'screen': SCREEN, 'name_field': NAME_FIELD, 'female': FEMALE,
                'male': MALE, 'save_continue': SAVE_CONTINUE, 'course_selection': COURSE_SELECTION}
    STRATEGIES = {'accessibility id': AppiumBy.ACCESSIBILITY_ID, 'id': AppiumBy.ID,
                  'xpath': AppiumBy.XPATH, 'class name': AppiumBy.CLASS_NAME,
                  '-android uiautomator': AppiumBy.ANDROID_UIAUTOMATOR}

    def __init__(self, driver, selectors=None, timeout=15):
        super().__init__(driver, timeout)
        self.overrides = selectors or {}
        self.allow_validation_submission = False

    def locator(self, key):
        spec = self.overrides.get(key)
        if spec is None:
            if key not in self.DEFAULTS:
                raise ValueError(f'Configure an inspected locator for {key}')
            return self.DEFAULTS[key]
        if not isinstance(spec, (list, tuple)) or len(spec) != 2 or spec[0] not in self.STRATEGIES or not spec[1]:
            raise ValueError(f'Invalid signup locator {key}: {spec!r}')
        return self.STRATEGIES[spec[0]], spec[1]

    def wait_until_loaded(self):
        self.element(self.locator('screen'))
        fields = self.driver.find_elements(*self.locator('name_field'))
        if len(fields) != 1:
            raise AssertionError(f'Expected one unambiguous name input, found {len(fields)}; configure name_field locator')
        for key in ('name_field', 'female', 'male', 'save_continue'):
            self.element(self.locator(key))

    def is_displayed(self):
        return self.is_visible(self.locator('screen'))

    def enter_name(self, name):
        self.enter_text(self.locator('name_field'), name)

    def name_value(self):
        return self.element(self.locator('name_field')).get_attribute('text') or ''

    def name_prompt(self):
        field = self.element(self.locator('name_field'))
        return field.get_attribute('hint') or field.get_attribute('content-desc') or field.get_attribute('text') or ''

    def select_gender(self, gender):
        key = gender.casefold()
        if key not in ('female', 'male'):
            raise ValueError('Gender must be Female or Male for this screen')
        self.click(self.locator(key))

    def gender_selected(self, gender):
        key = gender.casefold()
        if key not in ('female', 'male'):
            raise ValueError('Gender must be Female or Male for this screen')
        marker = key + '_selected'
        if self.overrides.get(marker) is not None:
            return self.is_visible(self.locator(marker), timeout=1)
        # Read real UI evidence; never remember the last tap as selection state.
        field = self.element(self.locator(key))
        return any(field.get_attribute(attribute) == 'true' for attribute in ('checked', 'selected'))

    def wait_gender_selected(self, gender):
        self.wait.until(lambda _: self.gender_selected(gender), message=f'{gender} selection not exposed; inspect selected marker')

    def can_continue(self):
        button = self.element(self.locator('save_continue'))
        return button.is_enabled() and button.get_attribute('clickable') == 'true'

    def wait_continue(self, enabled):
        self.wait.until(lambda _: self.can_continue() == enabled,
                        message=f'Save & Continue did not become enabled={enabled}')

    def hide_keyboard(self):
        if self.driver.is_keyboard_shown():
            self.driver.hide_keyboard()
            self.wait.until(lambda driver: not driver.is_keyboard_shown())

    def save(self):
        self.hide_keyboard()
        self.wait_continue(True)
        self.click(self.locator('save_continue'))

    def is_course_selection_displayed(self, timeout=2):
        return self.is_visible(self.locator('course_selection'), timeout)

    def wait_course_selection(self):
        self.element(self.locator('course_selection'))
        self.wait.invisible(self.locator('screen'))

    def validation_visible(self, kind):
        key = kind + '_error'
        if self.overrides.get(key) is None:
            return False  # No fabricated error accessibility ID.
        return self.is_visible(self.locator(key), timeout=2)

    def assert_submission_blocked(self, kind='name'):
        self.hide_keyboard()
        if self.can_continue():
            if not self.allow_validation_submission:
                # An unexpectedly enabled invalid form could create a real account.
                # Report the unmet prerequisite, not a fabricated validation pass.
                import pytest
                pytest.skip('Enabled invalid submission needs an approved isolated signup account; configure staging reset/restore')
            self.save()
            self.wait.until(lambda _: self.is_course_selection_displayed(timeout=1)
                            or self.validation_visible(kind) or not self.can_continue(),
                            message='Enabled invalid submission did not show validation or disable Continue')
        assert not self.is_course_selection_displayed(), 'Invalid signup unexpectedly reached Course Selection'
        assert self.is_displayed(), 'Invalid signup left Enter Your Details'
        assert not self.can_continue() or self.validation_visible(kind), 'Expected disabled Continue or actual validation'

    def rapid_save_taps(self, count=5):
        """Tap only the original Save element, never coordinates on the next page."""
        if type(count) is not int or not 2 <= count <= 10:
            raise ValueError('Use 2–10 taps')
        self.hide_keyboard()
        self.wait_continue(True)
        original = self.element(self.locator('save_continue'))
        accepted = 0
        for _ in range(count):
            if self.driver.find_elements(*self.locator('course_selection')):
                break
            try:
                self.driver.execute_script('mobile: clickGesture', {'elementId': original.id})
                accepted += 1
            except (StaleElementReferenceException, NoSuchElementException):
                # A removed Save control is safe only if navigation really happened.
                self.wait_course_selection()
                break
        assert accepted >= 1, 'No signup tap was issued'
        return accepted
