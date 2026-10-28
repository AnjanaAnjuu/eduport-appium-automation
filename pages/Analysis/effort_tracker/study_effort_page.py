"""UI measurements and authored activity flows for Effort Tracker cases."""
import re

from pages.Analysis.effort_flow import EffortFlowPage


class StudyEffortPage(EffortFlowPage):
    CATEGORIES = ('study', 'practice', 'exam', 'revision', 'total')
    DURATION = re.compile(r'(?:(\d+)h:)?(\d+)m:(\d+)s', re.I)

    def __init__(self, driver, data, timeout=15):
        super().__init__(driver, data.get('selectors', {}), timeout)
        self.data = data

    @classmethod
    def parse_seconds(cls, label):
        matches = list(cls.DURATION.finditer(label))
        if len(matches) != 1:
            raise AssertionError(f'Expected one effort duration in {label!r}')
        hour, minute, second = matches[0].groups()
        if int(second) >= 60 or (hour and int(minute) >= 60):
            raise AssertionError(f'Invalid effort duration in {label!r}')
        return int(hour or 0) * 3600 + int(minute) * 60 + int(second)

    def read(self, name):
        item = self.element(self.locator(name))
        return item.get_attribute('content-desc') or item.get_attribute('text') or item.text or ''

    def tap(self, name):
        self.click(self.locator(name))

    def control_available(self, name):
        """A boundary arrow is unavailable when absent, hidden or disabled."""
        controls = self.driver.find_elements(*self.locator(name))
        return any(item.is_displayed() and item.is_enabled()
                   and item.get_attribute('clickable') != 'false' for item in controls)

    def effort_index(self):
        label = self.read('effort_index')
        numbers = re.findall(r'(?<![\d.])\d+(?:\.\d+)?(?![\d.])', label)
        if len(numbers) != 1:
            raise AssertionError(f'Expected one Effort Index value in {label!r}')
        return float(numbers[0])

    def dated_snapshot(self):
        return {
            'date_label': self.read('date').strip(),
            'effort_index': self.effort_index(),
            **self.snapshot(),
        }

    def snapshot(self):
        fields = self.data.get('tracker_fields', ('study', 'practice', 'exam', 'total'))
        if not fields or 'study' not in fields or 'total' not in fields:
            raise ValueError('tracker_fields must contain at least study and total')
        result = {}
        for name in fields:
            if name not in self.CATEGORIES:
                raise ValueError(f'Unsupported tracker field: {name}')
            result[name] = self.parse_seconds(self.read(name))
        return result

    def assert_total(self, values):
        component_names = [name for name in ('study', 'practice', 'exam') if name in values]
        if len(component_names) == 3:
            assert values['total'] == sum(values[name] for name in component_names), (
                f'Total Time Spent differs from Study + Practice + Exam: {values}'
            )

    def verify_change(self, before, after, expected):
        """Check a case's authored ranges and reject changes in other fields."""
        self.assert_total(before)
        self.assert_total(after)
        if not isinstance(expected, dict) or not expected:
            raise ValueError('Configure expected_delta_seconds by tracker category')
        for name, bounds in expected.items():
            if name not in before or name not in after:
                raise ValueError(f'{name} is missing from tracker_fields')
            if (not isinstance(bounds, list) or len(bounds) != 2
                    or any(type(value) is not int or value < 0 for value in bounds)
                    or bounds[0] > bounds[1]):
                raise ValueError(f'{name} needs nonnegative [minimum, maximum] seconds')
        for name in before:
            if name == 'total':
                continue
            change = after[name] - before[name]
            low, high = expected.get(name, [0, 0])
            assert low <= change <= high, f'{name} changed {change}s; expected {low}–{high}s'
        component_delta = sum(after[name] - before[name] for name in before if name != 'total')
        if 'total' in expected:
            low, high = expected['total']
            change = after['total'] - before['total']
            assert low <= change <= high, f'total changed {change}s; expected {low}–{high}s'
        if 'revision' not in before or self.data.get('revision_in_total') is True:
            assert after['total'] - before['total'] == component_delta, (
                f'Total delta does not match component deltas: {before} -> {after}'
            )

    def verify_observation(self, observed, expected):
        for name, bounds in expected.items():
            if name not in observed:
                raise ValueError(f'{name} missing from tracker_fields')
            if (not isinstance(bounds, list) or len(bounds) != 2
                    or any(type(value) is not int or value < 0 for value in bounds)
                    or bounds[0] > bounds[1]):
                raise ValueError(f'Configure {name} as [minimum, maximum] seconds')
            assert bounds[0] <= observed[name] <= bounds[1], (
                f'{name}: observed {observed[name]}s; expected {bounds}'
            )
