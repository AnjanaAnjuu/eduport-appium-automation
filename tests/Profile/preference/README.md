# Preferences acceptance suite

The six requested files are under `pages/Profile/preference` and
`tests/Profile/preference`. Common interactions and fixtures support the three
suites. TC_001–TC_060 occur once each; TC_025 and TC_026 each run seven quality
variants, for 72 collected tests. All original IDs are retained in reports.

```sh
venv/bin/python -m pytest tests/Profile/preference --collect-only -q
PREFERENCE_TEST_DATA=/absolute/path/preferences.json \
  venv/bin/python -m pytest tests/Profile/preference
```

## Configuration

Set `PREFERENCE_TEST_DATA` to independently authored JSON:

```json
{
  "app_id": "your.application.id",
  "selectors": {},
  "routes": {},
  "quality_labels": {
    "Auto": "Auto", "High Quality": "High quality", "Data Saver": "Data Saver",
    "720p": "720p", "480p": "480p", "360p": "360p", "240p": "240p"
  },
  "toggle_attribute": "checked",
  "selected_attribute": "selected",
  "accessibility_attribute": "content-desc",
  "notification_controls": [],
  "videos": {},
  "cases": {"TC_001": {"ready": false}}
}
```

Populate selectors from Appium Inspector. Values are `[strategy,value]` or
`{"locator":[strategy,value],"attribute":"content-desc"}` for Flutter text.
Quality labels must match the current build's displayed spelling. Missing or
malformed configured selectors fail; this suite does not invent resource IDs.

Common keys: `title`, `back`, `previous_screen`, `video_section`, `audio_section`,
`notification_section`, `loading`, `error`, `mobile_network`, `wifi_network`,
`mobile_quality`, `wifi_quality`, `quality_sheet`, `advanced_sheet`, `auto`,
`high_quality`, `data_saver`, `advanced`, `720p`, `480p`, `360p`, `240p`,
`sheet_backdrop`, `player`, `video_title`, `global_quality_prompt`,
`sound_effects`, `app_launch_sound`, `stickers`, `app_icon_change`. Quality
option locators must select the actual option/selection semantics; the network
value must not match a sheet option. Toggle locators must select the switch.

Routes are nonempty lists of selector names to tap. Required as applicable:
`preferences` (from relevant states to Settings → Preferences), `show_video`,
`show_audio`, `show_notification`, `reload`, `player_override`,
`player_global_change`, `prompt_to_preferences`, `offline_change`, and each
video route. Section routes must scroll to their section when necessary, using
an inspected UiScrollable target on Android or app-specific controls. Extend
`route()` with platform-specific scrolling if the app has no such targets.
Use an iOS configuration with actual XCUITest locators/attributes.

## Named Chemistry videos and real playback evidence

`videos` has `mobile` and `wifi` entries, each containing `subtopic` and
`resource` records with `id`, exact UI `title`, `route`, and `curriculum`:

- Mobile: `["Chemistry", "Some Basic Concepts of Chemistry", "Importance of Chemistry"]`
- Wi-Fi: `["Chemistry", "Some Basic Concepts of Chemistry", "Laws of Chemical Combinations"]`

These normalized curriculum names identify the user-requested content. `title`
must match the actual app text, including any spelling differences. IDs must be
verified against the seeded catalogue. Each kind must really navigate through
Resources or Subtopics respectively; do not map both to an unrelated video.
If the named content is unavailable through one path, leave TC_027/028 unready
until the proper content/path can be provided.

For TC_025/026 all seven quality policies are checked. The OTHER network is
configured differently so using the wrong preference can be detected. Playback
verification requires at least two settled samples with advancing position,
nonzero rendered frames, correct media ID and verified network. Fixed quality
requires actual decoded heights of 720/480/360/240. Unsupported renditions are a
fixture/content problem to resolve; do not pass by reading the quality label.

For Auto/High Quality/Data Saver, `playback_policies` maps each policy to
`{"rule":"approved rule under controlled bandwidth", "allowed_heights":[...]}`.
The sample's effective player `mode` must match the selected policy as well.
Auto does not imply a fixed resolution. Sampling must start after stabilization,
exclude old-player/old-quality frames, and fail on stalled or unavailable video.

## Integration fixtures

Implement project-owned fixtures in a parent conftest or installed pytest plugin:

- `preference_session`: callable `(data,case)` returning a context manager that
  yields an authenticated Appium driver. Snapshot and independently seed all
  case preferences, authenticate using the existing login/OTP workflow, then
  restore preferences/device state and quit in `finally`, including failures.
  Honor existing SMS controls when sending OTP. Each case/quality parameter
  gets an isolated session. Use an actual Android, iOS or tablet profile as
  applicable. The shared existing driver is Android-only and logs out on setup,
  so this provider handles platform-specific login explicitly.
- `preference_network`: context-manager factory `(driver, 'mobile'|'wifi'|'offline')`.
  It yields `active_transport()` and restores exact prior radios/connectivity
  on exit. Verify effective transport, disable Wi-Fi for mobile, ensure a working
  mobile-data subscription, and disconnect all transports for offline tests.
- `preference_playback`: object with `samples(driver,video,case)` returning
  settled real-player samples: `video_id`, `network`, `height`, `mode`,
  `position_seconds`, `rendered_frames`. Use decoder/debug telemetry or a
  verified player statistics interface. Preference labels, mocked playback,
  or elapsed wall-clock time alone are not acceptable evidence.
- `preference_fault`: context-manager factory `(driver,case)` injecting the actual
  preferences API failure and restoring normal service on exit.
- `preference_visual`: callable `(driver,case,scope) -> bool`, comparing relevant
  screens/scroll positions against approved device/platform baselines. Cover
  text clipping, tick marks and actual full-page design. Store screenshot diffs.
- `preference_relogin`: callable `(driver,case)` performing actual logout,
  verifying the login screen and logging back into the same account.

Missing required providers or unready data skip before opening a device session.
Provider failures propagate. Collection/skipped runs are not live acceptance.

## Case-specific expectations

Each `cases.TC_###` needs `ready:true` after setup is available. Seed data must
support the intended case independently. Additionally:

- 006/007: `baseline` mapping mobile/wifi to independently seeded quality keys.
- 023/024/041/057: `qualities` mapping **both** networks to intended settings.
- 027/028: `quality`; 029: `network`, `quality`, distinct `override_quality`.
  The override route must choose that exact player quality. A second distinct
  named video is then checked on the SAME connection, and global values must
  remain unchanged. 030: `network`, exact `prompt_text`.
- 041: nonempty `audio_baseline` and `notification_baseline` toggle mappings.
- 042: approved `offline_rule`, nonempty `offline_expected_text`, and both
  `reconnected_qualities`. The offline_change route attempts an actual update;
  expectations must explicitly represent allowed local saving or rejection.
- 043/059: positive `max_load_seconds`; 059 also positive `max_save_seconds`.
- 044: exact `error_text`. 045/049/050/051/054/060: approved visual baseline
  identifiers consumed by the visual provider; 045 must exercise long labels.
- 051: boolean `landscape_supported`; unsupported builds skip.
- 054: `device_form_factor: "tablet"`, verified by session device inventory.
- 057: approved `relogin_rule`, `after_login` for both networks, and nonempty
  `audio_after_login`/`notification_after_login` toggle expectations.

Notification screenshot content is incomplete: configure actual switch names
in `notification_controls`. TC_040 assumes auto-saving boolean switches; adapt
the page method if inspection shows a different control or explicit Save button.
Audio cases verify switch state and persistence as requested, not recorded sound
output, sticker animations or special-day launcher artwork. Those behaviors
need separate controlled event/audio evidence if acceptance scope expands.
