"""Notification cases; supply actual controls from the target app build."""


def test_tc_005_notification_heading(pref):
    pref.notification.section('notification')


def test_tc_039_notification_controls(pref):
    pref.notification.controls()


def test_tc_040_notification_update(pref):
    pref.notification.update_and_verify()
