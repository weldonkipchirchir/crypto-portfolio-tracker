"""Bounded, account-scoped saved valuation history. No historical reconstruction."""
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def init(c):
    pass


def _points(rows, source):
    points = []
    for row in reversed(rows):
        try:
            d = json.loads(row['data'])
            stamp = int(d['observed_at'] if source == 'connected' else d['created_at'])
            value = Decimal(str(d['value'] if source == 'connected' else d['value_usd']))
            if not value.is_finite() or value < 0 or value.adjusted() > 78 or stamp < 0:
                continue
            day = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
            points.append({'timestamp': stamp, 'date': day, 'value': str(value),
                           'partial': bool(d.get('partial') or d.get('unpriced', 0) or d.get('unpriced_count', 0) or d.get('truncated')),
                           'stale': bool(d.get('stale_count')),
                           'freshness_verified': d.get('freshness_verified') is True if 'freshness_verified' in d else source=='wallets' and 'stale_count' in d,
                           'balances_changed': bool(d.get('balances_changed')),
                           'membership_changed': bool(d.get('membership_changed')),
                           'balance_fingerprint': d.get('balance_fingerprint'),
                           'coverage_fingerprint': d.get('coverage_fingerprint')})
        except (ValueError, TypeError, KeyError, OverflowError, OSError, InvalidOperation):
            continue
    for previous, current in zip(points, points[1:]):
        if previous.get('balance_fingerprint') and current.get('balance_fingerprint'):
            current['balances_changed'] |= previous['balance_fingerprint'] != current['balance_fingerprint']
        current['coverage_changed'] = bool(previous.get('coverage_fingerprint') and current.get('coverage_fingerprint') and previous['coverage_fingerprint'] != current['coverage_fingerprint'])
    return points


def read(c, uid, raw):
    # Existing collectors own these tables; this reader never samples today's holdings.
    daily = list(c.execute('SELECT data FROM portfolio_daily_values WHERE user_id=? ORDER BY day DESC LIMIT 2001', (uid,)))
    checkpoints = list(c.execute('SELECT data FROM portfolio_checkpoints WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 366', (uid,)))
    return {'series': {'connected': _points(daily[:2000], 'connected'), 'wallets': _points(checkpoints[:365], 'wallets')},
            'truncated': len(daily) > 2000 or len(checkpoints) > 365,
            'coverage': 'Actual saved USD observations only. Connected history includes wallets and exchanges; checkpoints cover wallets only. Series have different coverage and are never joined. Missing dates are gaps, never zero. Daily history retains the last saved value per UTC day; today can change. Changes include deposits, withdrawals and account membership changes; they are not investment returns. Unpriced assets are excluded. No per-asset history is available.'}
