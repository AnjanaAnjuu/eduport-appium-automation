"""Network quality selection and independently measured video playback."""
from pages.Profile.preference.preferences_page import PreferencesPage


class VideoQualityPreferencePage(PreferencesPage):
    QUALITIES = ('Auto', 'High Quality', 'Data Saver', '720p', '480p', '360p', '240p')
    OPTIONS = ('auto', 'high_quality', 'data_saver', 'advanced')
    VIDEOS = {
        'mobile': ('Chemistry', 'Some Basic Concepts of Chemistry', 'Importance of Chemistry'),
        'wifi': ('Chemistry', 'Some Basic Concepts of Chemistry', 'Laws of Chemical Combinations'),
    }

    @staticmethod
    def option(quality):
        return {'Auto': 'auto', 'High Quality': 'high_quality', 'Data Saver': 'data_saver'}.get(quality, quality)

    def quality(self, network):
        assert network in ('mobile', 'wifi')
        self.section('video')
        return self.text(f'{network}_quality')

    def open_quality(self, network):
        assert network in ('mobile', 'wifi')
        self.section('video')
        self.tap(f'{network}_network')
        self.target('quality_sheet')

    def select(self, network, quality):
        assert quality in self.QUALITIES
        self.open_quality(network)
        if quality.endswith('p'):
            self.tap('advanced')
            self.target('advanced_sheet')
        self.tap(self.option(quality))
        self.wait.invisible(self.locator('quality_sheet'))
        self.wait.invisible(self.locator('advanced_sheet'))
        self.wait.until(lambda _: self.quality(network) == self.data['quality_labels'][quality])

    def selected(self, key):
        return str(self.target(key).get_attribute(self.data.get('selected_attribute', 'selected'))).lower() == 'true'

    def assert_selection(self, network, quality):
        self.open_quality(network)
        expected = 'advanced' if quality.endswith('p') else self.option(quality)
        assert [key for key in self.OPTIONS if self.selected(key)] == [expected]
        if quality.endswith('p'):
            self.tap('advanced')
            assert [key for key in self.QUALITIES[3:] if self.selected(key)] == [quality]

    def open_video(self, network, kind='subtopic'):
        video = self.data['videos'][network][kind]
        assert tuple(video['curriculum']) == self.VIDEOS[network], 'Configure the Chemistry video requested by the user'
        self.route(video['route'])
        assert self.text('video_title') == video['title']
        self.target('player')
        return video

    def verify_playback(self, probe, network, video, quality, case):
        """Probe samples must come from the active decoder/player, not settings."""
        samples = probe.samples(self.driver, video, case)
        assert len(samples) >= 2, 'Need playback progress evidence'
        assert all(s['network'] == network and s['video_id'] == video['id'] for s in samples)
        assert samples[-1]['position_seconds'] > samples[0]['position_seconds']
        assert all(s['rendered_frames'] > 0 and s['height'] > 0 for s in samples)
        if quality.endswith('p'):
            assert all(s['height'] == int(quality[:-1]) for s in samples), 'Actual decoded resolution differs'
        else:
            # Adaptive policy expectations must come from confirmed product rules
            # under a controlled bandwidth profile; Auto has no fixed resolution.
            policy = case['playback_policies'][quality]
            assert policy['rule'] and policy['allowed_heights']
            assert all(s['mode'] == quality and s['height'] in policy['allowed_heights'] for s in samples)
