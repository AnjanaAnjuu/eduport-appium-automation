"""Coin/problem-quiz interactions. Unknown UI selectors come from test data.

No invented resource IDs, guessed answers, clock changes, or coin resets.
"""
from dataclasses import dataclass
from datetime import datetime
import re
from zoneinfo import ZoneInfo

from appium.webdriver.common.appiumby import AppiumBy
from pages.base_page import BasePage
from utils.waits import Waits


class CoinConfigurationError(ValueError):
    """The test-data contract is incomplete or unsafe."""


@dataclass(frozen=True)
class CoinBalances:
    home: int
    today: int
    weekly: int
    all_time: int

    def delta(self, before):
        return CoinBalances(*(getattr(self, key) - getattr(before, key)
                              for key in ('home', 'today', 'weekly', 'all_time')))


@dataclass(frozen=True)
class QuizResult:
    total: int
    correct: int
    wrong: int
    unknown: int
    coins: int


@dataclass(frozen=True)
class CoinTransaction:
    transaction_id: str
    coins: int
    recorded_at: datetime


def parse_integer(text, pattern=None):
    """Reject ambiguous labels (e.g. Correct 2 / Wrong 3) without a field regex."""
    text = text.replace('\u2212', '-').replace('\u00a0', ' ')
    if pattern:
        if re.compile(pattern).groups != 1:
            raise CoinConfigurationError('Count pattern must have exactly one capture group')
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1 or matches[0].lastindex != 1:
            raise CoinConfigurationError('Count pattern must match once with one capture group')
        value = matches[0].group(1)
    else:
        values = re.findall(r'(?<![\w.])[+-]?\d+(?:,\d{3})*(?![\w.])', text)
        if len(values) != 1:
            raise CoinConfigurationError(f'Expected one integer in {text!r}; configure a field pattern')
        value = values[0]
    if not re.fullmatch(r'[+-]?\d+(?:,\d{3})*', value.strip()):
        raise CoinConfigurationError(f'Not an integer coin/count value: {value!r}')
    return int(value.replace(',', ''))


def answer_counts(answers):
    """Expected counts come from the authored answer key, not the app's result.

    Last selection wins when the same question is answered again (TC017).
    """
    latest = {}
    for answer in answers:
        if not answer.get('question_id') or answer.get('outcome') not in ('correct', 'wrong', 'unknown'):
            raise CoinConfigurationError('Answers need question_id and correct/wrong/unknown outcome')
        latest[answer['question_id']] = answer['outcome']
    return {kind: list(latest.values()).count(kind) for kind in ('correct', 'wrong', 'unknown')}


class CoinProblemQuizPage(BasePage):
    """One page object for Home, leaderboard/logs, and problem-based quizzes."""

    STRATEGIES = {
        'accessibility id': AppiumBy.ACCESSIBILITY_ID, 'id': AppiumBy.ID,
        'xpath': AppiumBy.XPATH, 'class name': AppiumBy.CLASS_NAME,
        '-android uiautomator': AppiumBy.ANDROID_UIAUTOMATOR,
    }

    def __init__(self, driver, data, timeout=15):
        super().__init__(driver, timeout)
        self.data = data
        self.selectors = data['selectors']
        self.zone = ZoneInfo(data['server_timezone'])

    def locator(self, target):
        spec = self.selectors.get(target) if isinstance(target, str) else target
        if isinstance(spec, dict):
            spec = spec.get('locator')
        if not isinstance(spec, (list, tuple)) or len(spec) != 2 or spec[0] not in self.STRATEGIES or not spec[1]:
            raise CoinConfigurationError(f'Provide the inspected locator for {target!r}')
        return self.STRATEGIES[spec[0]], spec[1]

    def text(self, target):
        element = self.element(self.locator(target))
        # Flutter uses content-desc; normal Android labels often use text.
        return element.get_attribute('content-desc') or element.get_attribute('text') or element.text or ''

    def number(self, target):
        spec = self.selectors.get(target, {})
        pattern = spec.get('pattern') if isinstance(spec, dict) else None
        return parse_integer(self.text(target), pattern)

    def visible(self, target, timeout=2):
        return self.is_visible(self.locator(target), timeout)

    def actionable(self, target):
        if not self.visible(target):
            return False
        element = self.element(self.locator(target))
        return element.is_enabled() and element.get_attribute('clickable') == 'true'

    def validate_steps(self, actions):
        if not isinstance(actions, list):
            raise CoinConfigurationError('UI steps must be a list')
        supported = {'tap', 'enter_text', 'wait_visible', 'wait_absent', 'back', 'hide_keyboard', 'scroll'}
        for step in actions:
            if not isinstance(step, dict) or step.get('action') not in supported:
                raise CoinConfigurationError(f'Unsupported UI action: {step!r}')
            if step['action'] not in ('back', 'hide_keyboard'):
                self.locator(step.get('target'))
            if step['action'] == 'enter_text' and not isinstance(step.get('text'), str):
                raise CoinConfigurationError('enter_text needs a string text value')
            if step['action'] == 'scroll' and (step.get('direction', 'down') not in ('up', 'down', 'left', 'right')
                                               or not 0 < step.get('percent', .8) <= 1):
                raise CoinConfigurationError('Scroll needs a valid direction and percent in (0, 1]')

    def steps(self, actions):
        """Execute authored UI steps only; no arbitrary scripts or shell hooks."""
        self.validate_steps(actions)
        for step in actions:
            action = step.get('action')
            target = step.get('target')
            if action == 'tap':
                self.click(self.locator(target))
            elif action == 'enter_text':
                self.enter_text(self.locator(target), step['text'])
            elif action == 'wait_visible':
                self.element(self.locator(target))
            elif action == 'wait_absent':
                self.wait.invisible(self.locator(target))
            elif action == 'back':
                self.driver.back()
            elif action == 'hide_keyboard':
                if self.driver.is_keyboard_shown():
                    self.driver.hide_keyboard()
            elif action == 'scroll':
                element = self.element(self.locator(target))
                self.driver.execute_script('mobile: scrollGesture', {
                    'elementId': element.id, 'direction': step.get('direction', 'down'),
                    'percent': step.get('percent', .8),
                })
            else:
                raise CoinConfigurationError(f'Unsupported UI action: {action!r}')

    def path(self, name):
        actions = self.data.get('paths', {}).get(name)
        if not actions:
            raise CoinConfigurationError(f'Configure nonempty paths.{name}')
        self.steps(actions)

    def phase(self, scenario, name):
        actions = scenario.get('phases', {}).get(name)
        if not actions:
            raise CoinConfigurationError(f'Configure phases.{name} for this scenario')
        self.steps(actions)

    def select_course(self):
        self.path('course')
        actual = ' '.join(self.text('course_title').split()).casefold()
        expected = ' '.join(self.data['course_name'].split()).casefold()
        if expected not in actual:
            raise AssertionError(f'Expected course {self.data["course_name"]!r}, found {actual!r}')

    def balances(self):
        self.path('home')
        home = self.number('home_coins')
        self.path('leaderboard')
        values = {}
        for key in ('today', 'weekly', 'all_time'):
            self.path('balance_' + key)
            values[key] = self.number(key + '_coins')
        return CoinBalances(home, **values)

    def wait_balances(self, expected, timeout=20):
        last = None

        def matches(_):
            nonlocal last
            last = self.balances()
            return last if last == expected else False

        try:
            return Waits(self.driver, timeout).until(matches)
        except Exception as error:
            # Preserve assertion/runtime/config errors; annotate timeouts only.
            from selenium.common.exceptions import TimeoutException
            if not isinstance(error, TimeoutException):
                raise
            raise AssertionError(f'Coin balances did not update: expected {expected}; last observed {last}') from error

    def result(self):
        values = {key: self.number('result_' + key)
                  for key in ('total', 'correct', 'wrong', 'unknown', 'coins')}
        result = QuizResult(**values)
        if any(getattr(result, key) < 0 for key in ('total', 'correct', 'wrong', 'unknown')):
            raise AssertionError(f'Negative question counts: {result}')
        if result.correct + result.wrong + result.unknown != result.total:
            raise AssertionError(f'Result question counts do not sum to total: {result}')
        return result

    def answer(self, answers):
        answer_counts(answers)  # Validate the independently authored oracle.
        for answer in answers:
            self.validate_steps(answer['steps'])
        for answer in answers:
            self.steps(answer['steps'])

    def complete(self, scenario):
        self.select_course()
        self.phase(scenario, 'open')
        self.answer(scenario['answers'])
        self.phase(scenario, 'submit')
        result = self.result()
        expected = answer_counts(scenario['answers'])
        for key, value in expected.items():
            assert getattr(result, key) == value, f'{key} count differs from answer key'
        assert result.total == scenario['expected_total']
        assert result.coins == scenario['expected_coins']
        return result

    def collect(self, scenario):
        if not self.actionable('collect_coins'):
            raise AssertionError('Collect Coins is not enabled/clickable for a positive result')
        self.phase(scenario, 'collect')

    def close_result(self, scenario):
        self.phase(scenario, 'close')

    def history(self, period):
        """Read every log row through an inspected end-of-list sentinel.

        Never treat only visible rows as complete Today/This Week/All Time history.
        """
        self.path('history_' + period)
        spec = self.data.get('history', {})
        pattern = spec.get('row_pattern')
        if not pattern:
            raise CoinConfigurationError('history.row_pattern needs id, coins, recorded_at named groups')
        rows = {}
        for _ in range(spec.get('max_pages', 20)):
            for element in self.driver.find_elements(*self.locator('log_rows')):
                label = element.get_attribute('content-desc') or element.get_attribute('text') or element.text or ''
                match = re.fullmatch(pattern, label, re.DOTALL)
                if not match or not {'id', 'coins', 'recorded_at'} <= set(match.groupdict()):
                    raise CoinConfigurationError(f'Log row does not match the configured schema: {label!r}')
                recorded = datetime.fromisoformat(match['recorded_at'])
                if recorded.tzinfo is None:
                    raise CoinConfigurationError('Log timestamps must include a timezone offset')
                item = CoinTransaction(match['id'], parse_integer(match['coins']), recorded)
                if item.transaction_id in rows and rows[item.transaction_id] != item:
                    raise AssertionError('Conflicting values for a repeated transaction ID')
                rows[item.transaction_id] = item
            if self.visible('log_end', timeout=1):
                return list(rows.values())
            self.steps([{'action': 'scroll', 'target': 'log_scroll_container'}])
        raise AssertionError('Coin history did not reach its end; completeness cannot be verified')

    def now(self):
        return datetime.now(self.zone)

    def wait_calendar_boundary(self, kind):
        """Observe a real boundary; never change emulator/server date or time."""
        from datetime import timedelta
        now = self.now()
        boundary = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if kind == 'weekly':
            scheduled = self.data.get('weekly_refresh_time')
            if not scheduled or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', scheduled):
                raise CoinConfigurationError('Confirm weekly_refresh_time (HH:MM on Tuesday in server_timezone)')
            hour, minute = map(int, scheduled.split(':'))
            boundary = (now + timedelta(days=(1 - now.weekday()) % 7)).replace(
                hour=hour, minute=minute, second=0, microsecond=0)
            if boundary <= now:
                boundary += timedelta(days=7)
        remaining = (boundary - now).total_seconds()
        budget = self.data['boundary_max_wait_seconds']
        if remaining > budget:
            raise CoinConfigurationError(f'Run near the real {kind} boundary; it is {remaining:.0f}s away, budget is {budget}s')
        Waits(self.driver, budget + 2).until(lambda _: self.now() >= boundary)
        return boundary
