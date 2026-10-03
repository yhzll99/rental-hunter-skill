import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/rental-finder-cn/scripts'))
import rental_core as core

NOW = datetime(2026, 10, 3, 10, tzinfo=timezone.utc)

def fact(value):
    return {'value': value, 'evidence': '模拟页面明确记载该值'}

def req():
    return {'city': '杭州', 'budget': {'max': 3500, 'basis': 'fixed_total'},
            'hard': {'district': {'op': 'eq', 'value': '滨江'},
                     'rental_type': {'op': 'eq', 'value': '整租'},
                     'orientation': {'op': 'eq', 'value': '南'},
                     'private_bathroom': {'op': 'eq', 'value': True}},
            'preferences': {'elevator': {'op': 'eq', 'value': True}}}

def listing():
    return {'id': 'a', 'title': '模拟房源', 'url': 'https://example.com/a',
            'source': '模拟平台', 'observed_at': '2026-10-03T10:00:00+00:00',
            'evidence_level': 'detail', 'facts': {k: fact(v) for k, v in {
                'city': '杭州', 'district': '滨江', 'rental_type': '整租',
                'orientation': '南', 'private_bathroom': True, 'rent_monthly': 3200,
                'mandatory_recurring_monthly': 100, 'elevator': True}.items()}}

def result(r=None, ls=None):
    return core.evaluate(r or req(), ls or [listing()], NOW)['results'][0]

class CoreTests(unittest.TestCase):
    def test_known_match(self):
        r = result()
        self.assertEqual(r['status'], 'meets_documented')
        self.assertEqual(r['cost']['known_min'], 3300)
    def test_unknown_fee_not_zero(self):
        x = listing(); del x['facts']['mandatory_recurring_monthly']
        self.assertEqual(result(ls=[x])['status'], 'needs_verification')
    def test_over_budget_excluded(self):
        x = listing(); x['facts']['mandatory_recurring_monthly'] = fact(400)
        self.assertEqual(result(ls=[x])['status'], 'excluded')
    def test_no_evidence_is_unknown(self):
        x = listing(); x['facts']['orientation']['evidence'] = ''
        self.assertEqual(result(ls=[x])['status'], 'needs_verification')
    def test_orientation_exact(self):
        x = listing(); x['facts']['orientation'] = fact('南北')
        self.assertEqual(result(ls=[x])['status'], 'excluded')
    def test_orientation_explicit_alternatives(self):
        r = req(); r['hard']['orientation'] = {'op': 'in', 'value': ['南', '南北']}
        x = listing(); x['facts']['orientation'] = fact('南北')
        self.assertEqual(result(r, [x])['status'], 'meets_documented')
    def test_snippet_never_match(self):
        x = listing(); x['evidence_level'] = 'snippet'
        self.assertEqual(result(ls=[x])['status'], 'needs_verification')
    def test_old_or_future_never_match(self):
        for date in ('2020-01-01T00:00:00Z', '2030-01-01T00:00:00Z'):
            x = listing(); x['observed_at'] = date
            self.assertEqual(result(ls=[x])['status'], 'needs_verification')
    def test_wrong_city_excluded(self):
        x = listing(); x['facts']['city'] = fact('苏州')
        self.assertEqual(result(ls=[x])['status'], 'excluded')
    def test_soft_not_hard(self):
        x = listing(); x['facts']['elevator'] = fact(False)
        self.assertEqual(result(ls=[x])['status'], 'meets_documented')
        self.assertEqual(result(ls=[x])['preference_matches'], 0)
    def test_total_requires_variable_cost(self):
        r = req(); r['budget']['basis'] = 'total_monthly'
        self.assertEqual(result(r)['status'], 'needs_verification')
    def test_duplicate_tracking_links_collapsed(self):
        a = listing(); b = copy.deepcopy(a); b['id'] = 'b'; b['url'] += '?utm_source=test'
        data = core.evaluate(req(), [a,b], NOW)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(len(data['results'][0]['observations']), 2)
    def test_different_room_query_not_collapsed(self):
        a = listing(); b = copy.deepcopy(a); b['id'] = 'b'; b['url'] += '?room=2'
        self.assertEqual(len(core.evaluate(req(), [a,b], NOW)['results']), 2)
    def test_conflicting_duplicates_not_trusted(self):
        a = listing(); b = copy.deepcopy(a); b['id'] = 'b'; b['facts']['orientation'] = fact('北')
        self.assertEqual(core.evaluate(req(), [a,b], NOW)['results'][0]['status'], 'needs_verification')
    def test_preference_conflict_keeps_certain_budget_exclusion(self):
        a = listing(); a['facts']['rent_monthly'] = fact(4000)
        b = copy.deepcopy(a); b['id'] = 'b'; b['facts']['elevator'] = fact(False)
        self.assertEqual(core.evaluate(req(), [a,b], NOW)['results'][0]['status'], 'excluded')
    def test_price_conflict_both_over_budget_still_excluded(self):
        a = listing(); a['facts']['rent_monthly'] = fact(4000)
        b = copy.deepcopy(a); b['id'] = 'b'; b['facts']['rent_monthly'] = fact(4100)
        self.assertEqual(core.evaluate(req(), [a,b], NOW)['results'][0]['status'], 'excluded')
    def test_different_hard_failures_cannot_prove_common_exclusion(self):
        a = listing(); a['facts']['orientation'] = fact('北')
        b = listing(); b['id'] = 'b'; b['facts']['rent_monthly'] = fact(4000)
        self.assertEqual(core.evaluate(req(), [a,b], NOW)['results'][0]['status'], 'needs_verification')
    def test_equal_numeric_observations_are_not_conflicts(self):
        a = listing(); b = copy.deepcopy(a); b['id'] = 'b'
        b['facts']['rent_monthly'] = fact(3200.0)
        self.assertEqual(core.evaluate(req(), [a,b], NOW)['results'][0]['status'], 'meets_documented')
    def test_number_bool_and_negative_invalid(self):
        for val in (-1, True, float('nan')):
            x = listing(); x['facts']['rent_monthly'] = fact(val)
            with self.assertRaises(ValueError): core.evaluate(req(), [x], NOW)
    def test_invalid_url(self):
        x = listing(); x['url'] = 'javascript:alert(1)'
        with self.assertRaises(ValueError): core.evaluate(req(), [x], NOW)
    def test_unknown_fields_rejected(self):
        r = req(); r['hard']['orientaton'] = {'op': 'eq', 'value': '南'}
        with self.assertRaises(ValueError): core.plan(r)
    def test_nationwide_fallback(self):
        r = req(); r['city'] = '成都'; r['hard'] = {}
        p = core.plan(r)
        self.assertEqual(p['coverage'], 'nationwide_discovery')
        self.assertTrue(all('成都' in q['query'] for q in p['queries']))
    def test_jzh_25_cities_and_group_diversity(self):
        self.assertEqual(len(core.CATALOG['cities']), 25)
        p = core.plan(req())
        self.assertGreaterEqual(len({q['group'] for q in p['queries']}), 3)
    def test_report_empty_and_escape(self):
        data = core.evaluate(req(), [], NOW)
        self.assertIn('暂无', core.report(data))
        x = listing(); x['title'] = '[假](javascript:bad)|x\n# evil'
        self.assertNotIn('](javascript:bad)', core.report(core.evaluate(req(), [x], NOW)))

if __name__ == '__main__': unittest.main()
