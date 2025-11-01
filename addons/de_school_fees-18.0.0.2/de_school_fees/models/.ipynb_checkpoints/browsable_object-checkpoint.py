#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields


class BrowsableObject(object):
    def __init__(self, employee_id, dict, env):
        self.employee_id = employee_id
        self.dict = dict
        self.env = env

    def __getattr__(self, attr):
        return attr in self.dict and self.dict.__getitem__(attr) or 0.0

    def __getitem__(self, key):
        return self.dict[key] or 0.0

class ResultRules(BrowsableObject):
    def __getattr__(self, attr):
        return attr in self.dict and self.dict.__getitem__(attr) or {'total': 0, 'amount': 0, 'quantity': 0}

    def __getitem__(self, key):
        return self.dict[key] if key in self.dict else {'total': 0, 'amount': 0, 'quantity': 0}

class InputLine(BrowsableObject):
    """a class that will be used into the python code, mainly for usability purposes"""
    def sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute("""
            SELECT sum(amount) as sum
            FROM oe_feeslip as hp, oe_feeslip_input as pi
            WHERE hp.student_id = %s AND hp.state = 'done'
            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.feeslip_id AND pi.code = %s""",
            (self.student_id, from_date, to_date, code))
        return self.env.cr.fetchone()[0] or 0.0



class Feeslips(BrowsableObject):
    """a class that will be used into the python code, mainly for usability purposes"""

    def sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute("""
            SELECT sum(pl.total)
            FROM oe_feeslip as hp, oe_feeslip_line as pl
            WHERE hp.student_id = %s
            AND hp.state = 'done'
            AND hp.date_from >= %s
            AND hp.date_to <= %s
            AND hp.id = pl.feeslip_id
            AND pl.code = %s""", (self.student_id, from_date, to_date, code))
        res = self.env.cr.fetchone()
        return res and res[0] or 0.0

    def rule_parameter(self, code):
        return self.env['hr.rule.parameter']._get_parameter_from_code(code, self.dict.date_to)

    def sum_category(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()

        self.env['oe.feeslip'].flush_model(['student_id', 'state', 'date_from', 'date_to'])
        self.env['oe.feeslip.line'].flush_model(['total', 'feeslip_id', 'category_id'])
        self.env['oe.fee.category'].flush_model(['code'])

        self.env.cr.execute("""
            SELECT sum(pl.total)
            FROM oe_feeslip as hp, oe_feeslip_line as pl, oe_fee_category as rc
            WHERE hp.student_id = %s
            AND hp.state = 'done'
            AND hp.date_from >= %s
            AND hp.date_to <= %s
            AND hp.id = pl.feeslip_id
            AND rc.id = pl.category_id
            AND rc.code = %s""", (self.student_id, from_date, to_date, code))
        res = self.env.cr.fetchone()
        return res and res[0] or 0.0

    @property
    def paid_amount(self):
        return self.dict._get_paid_amount()

    @property
    def is_outside_contract(self):
        return self.dict._is_outside_contract_dates()
