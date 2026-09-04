"""Derived achievement badges.

Badges aren't a stored model — they're computed on the fly from the numbers we
already track in ``UserStats`` (picks made, best streak, accuracy, primetime
hits). Each badge is either earned or shown locked with a little progress hint,
so the dashboard has a lightweight gamification layer with zero new tables.
"""


def _pct(value, goal):
    """Clamp a 0..goal progress string like '2/3'."""
    return f"{min(int(value), goal)}/{goal}"


def compute_badges(stats):
    """Return the ordered badge list for a ``UserStats`` instance.

    Each entry: ``{key, icon, label, desc, earned, progress}``. Streak badges
    key off ``best_streak`` so they stay earned once achieved (a later loss
    doesn't revoke them); the live ``current_streak`` is surfaced separately.
    """
    picks = stats.total_picks or 0
    best = stats.best_streak or 0
    win_pct = stats.win_percentage or 0
    pt_correct = stats.primetime_correct or 0

    badges = [
        {
            'key': 'on_board', 'icon': '\U0001F3C8', 'label': 'On the Board',
            'desc': 'Make your first pick',
            'earned': picks >= 1, 'progress': _pct(picks, 1),
        },
        {
            'key': 'regular', 'icon': '\U0001F4C5', 'label': 'Regular',
            'desc': 'Make 10 picks',
            'earned': picks >= 10, 'progress': _pct(picks, 10),
        },
        {
            'key': 'hot_hand', 'icon': '\U0001F525', 'label': 'Hot Hand',
            'desc': 'Win 3 picks in a row',
            'earned': best >= 3, 'progress': _pct(best, 3),
        },
        {
            'key': 'unstoppable', 'icon': '\U0001F680', 'label': 'Unstoppable',
            'desc': 'Win 5 picks in a row',
            'earned': best >= 5, 'progress': _pct(best, 5),
        },
        {
            'key': 'sharpshooter', 'icon': '\U0001F3AF', 'label': 'Sharpshooter',
            'desc': 'Hit 65%+ over 10+ picks',
            'earned': picks >= 10 and win_pct >= 65,
            'progress': f"{round(win_pct)}%",
        },
        {
            'key': 'primetime_pro', 'icon': '\U0001F31F', 'label': 'Primetime Pro',
            'desc': 'Nail 10 primetime picks',
            'earned': pt_correct >= 10, 'progress': _pct(pt_correct, 10),
        },
        {
            'key': 'perfectionist', 'icon': '\U0001F4AF', 'label': 'Perfectionist',
            'desc': 'Win 10 picks in a row',
            'earned': best >= 10, 'progress': _pct(best, 10),
        },
    ]
    return badges
