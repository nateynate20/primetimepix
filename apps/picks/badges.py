"""Derived achievement badges.

Badges aren't a stored model — they're computed on the fly from the numbers we
already track in ``UserStats`` (picks made, best streak, accuracy, primetime
hits). Each badge is either earned or shown locked with a little progress hint,
so the dashboard has a lightweight gamification layer with zero new tables.
"""


def _pct(value, goal):
    """Clamp a 0..goal progress string like '2/3'."""
    return f"{min(int(value), goal)}/{goal}"


def _bar(current, target):
    """0..100 fill for a progress bar."""
    if target <= 0:
        return 100
    return max(0, min(100, round(current / target * 100)))


def _count_badge(key, icon, label, desc, current, target, unit):
    """A simple 'reach N' badge with unit-labelled progress."""
    current = int(current or 0)
    shown = min(current, target)
    return {
        'key': key, 'icon': icon, 'label': label, 'desc': desc,
        'earned': current >= target,
        'progress': _pct(current, target),          # e.g. '4/10' (kept for tests)
        'progress_pct': _bar(current, target),      # bar fill
        'progress_label': f"{shown}/{target} {unit}",  # e.g. '4/10 picks'
    }


def compute_badges(stats):
    """Return the ordered badge list for a ``UserStats`` instance.

    Each entry: ``{key, icon, label, desc, earned, progress, progress_pct,
    progress_label}``. ``progress`` stays as the bare ``'4/10'`` form; the
    template uses ``progress_label`` (unit-labelled) and ``progress_pct`` (bar).
    Streak badges key off ``best_streak`` so they stay earned once achieved (a
    later loss doesn't revoke them); the live ``current_streak`` is separate.
    """
    picks = stats.total_picks or 0
    best = stats.best_streak or 0
    win_pct = stats.win_percentage or 0
    pt_correct = stats.primetime_correct or 0

    # Sharpshooter needs BOTH a real sample (10+ picks) AND 65%+ accuracy, so a
    # perfect record on 3 picks isn't enough. Surface the *limiting* factor as
    # progress so it never reads a misleading "100%" while still locked.
    sharp_earned = picks >= 10 and win_pct >= 65
    if picks < 10:
        sharp_label = f"{picks}/10 picks (then 65%+)"
        sharp_bar = _bar(picks, 10)
        sharp_progress = _pct(picks, 10)
    else:
        sharp_label = f"{round(win_pct)}%/65% accuracy"
        sharp_bar = _bar(win_pct, 65)
        sharp_progress = f"{round(win_pct)}%"

    badges = [
        _count_badge('on_board', '\U0001F3C8', 'On the Board',
                     'Make your first pick', picks, 1, 'pick'),
        _count_badge('regular', '\U0001F4C5', 'Regular',
                     'Make 10 picks', picks, 10, 'picks'),
        _count_badge('hot_hand', '\U0001F525', 'Hot Hand',
                     'Win 3 picks in a row', best, 3, 'in a row'),
        _count_badge('unstoppable', '\U0001F680', 'Unstoppable',
                     'Win 5 picks in a row', best, 5, 'in a row'),
        {
            'key': 'sharpshooter', 'icon': '\U0001F3AF', 'label': 'Sharpshooter',
            'desc': 'Hit 65%+ accuracy over 10+ picks',
            'earned': sharp_earned,
            'progress': sharp_progress,
            'progress_pct': sharp_bar,
            'progress_label': sharp_label,
        },
        _count_badge('primetime_pro', '\U0001F31F', 'Primetime Pro',
                     'Win 10 primetime picks', pt_correct, 10, 'wins'),
        _count_badge('perfectionist', '\U0001F4AF', 'Perfectionist',
                     'Win 10 picks in a row', best, 10, 'in a row'),
    ]
    return badges
