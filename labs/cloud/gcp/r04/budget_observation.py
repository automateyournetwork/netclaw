"""Validate an observed preexisting project-wide budget without modifying it."""
import hashlib
import json
import re
from decimal import Decimal


def verify(raw, project_number, budget_name):
    def need(test, code):
        if not test: raise ValueError(code)
    need(re.fullmatch(r'[0-9]{6,20}', project_number), 'project_number_invalid')
    need(re.fullmatch(r'billingAccounts/[A-Fa-f0-9-]+/budgets/[A-Za-z0-9-]+', budget_name), 'budget_name_invalid')
    data = json.loads(raw)
    need(isinstance(data, dict) and isinstance(data.get('budgets'), list)
         and not data.get('nextPageToken'), 'incomplete_budget_observation')
    matches = [b for b in data['budgets'] if b.get('name') == budget_name]
    need(len(matches) == 1, 'budget_observation_ambiguous')
    budget = matches[0]; filters = budget.get('budgetFilter')
    need(filters == {'projects': ['projects/' + project_number], 'creditTypesTreatment': 'EXCLUDE_ALL_CREDITS',
                     'calendarPeriod': 'MONTH'}, 'budget_scope_invalid')
    amount = budget.get('amount', {}).get('specifiedAmount', {})
    need(set(amount) <= {'currencyCode', 'units', 'nanos'} and amount.get('currencyCode') == 'CAD', 'budget_currency_invalid')
    value = Decimal(amount.get('units', '0')) + Decimal(amount.get('nanos', 0)) / Decimal(10**9)
    need(0 < value <= 100, 'budget_amount_invalid')
    thresholds = budget.get('thresholdRules', [])
    need(len(thresholds) == 3 and all(set(t) <= {'thresholdPercent', 'spendBasis'}
         and t.get('spendBasis', 'CURRENT_SPEND') == 'CURRENT_SPEND' for t in thresholds)
         and {Decimal(str(t['thresholdPercent'])) for t in thresholds} == {Decimal('.5'), Decimal('.9'), Decimal(1)}, 'budget_thresholds_invalid')
    need(budget.get('notificationsRule', {}) == {}, 'default_budget_notifications_required')
    return {'budget_name': budget_name, 'observation_sha256': hashlib.sha256(raw).hexdigest(),
            'project_number': project_number, 'currency': 'CAD', 'amount': str(value),
            'project_wide': True, 'gross_cost': True, 'mutated': False, 'hard_cap': False,
            'ownership': 'preexisting_preserved'}
