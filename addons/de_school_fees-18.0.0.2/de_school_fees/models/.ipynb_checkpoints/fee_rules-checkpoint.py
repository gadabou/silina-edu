# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class FeeRule(models.Model):
    _name = 'oe.fee.rule'
    _order = 'sequence, id'
    _description = 'Fee Rule'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True,
        help="The code of fee rules can be used as reference in computation of other rules. "
             "In that case, it is case sensitive.")
    fee_struct_id = fields.Many2one('oe.fee.struct', string="Fee Structure", required=True)
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('tri-annually', 'Tri-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
        ('one-time', 'One Time'),
    ], store=True, readonly=False, required=True, default='monthly',
    string='Frequency', index=True, help="Defines the frequency of fee.")
    
    sequence = fields.Integer(required=True, index=True, default=5,
        help='Use to arrange calculation sequence')
    quantity = fields.Char(default='1.0',
        help="It is used in computation for percentage and fixed amount. "
             "E.g. a rule for Meal Voucher having fixed amount of "
             u"1€ per worked day can have its quantity defined in expression "
             "like worked_days.WORK100.number_of_days.")
    category_id = fields.Many2one('oe.fee.category', string='Category', required=True)
    active = fields.Boolean(default=True,
        help="If the active field is set to false, it will allow you to hide the fee rule without removing it.")
    appears_on_feeslip = fields.Boolean(string='Appears on Feeslip', default=True,
        help="Used to display the fee rule on payslip.")
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression')
    ], string="Condition Based on", default='none', required=True)
    condition_range = fields.Char(string='Range Based on', default='contract.wage',
        help='This will be used to compute the % fields values; in general it is on basic, '
             'but you can also use categories code fields in lowercase as a variable names '
             '(hra, ma, lta, etc.) and the variable basic.')
    condition_python = fields.Text(string='Python Condition', required=True,
        default='''
# Available variables:
#----------------------
# feeslip: object containing the feeslips
# student: res.partner object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed fee rule categories (sum of amount of all rules belonging to that category).
# inputs: object containing the computed inputs.

# Note: returned value have to be set in the variable 'result'

result = rules.NET > categories.NET * 0.10''',
        help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.')
    condition_range_min = fields.Float(string='Minimum Range', help="The minimum amount, applied for this rule.")
    condition_range_max = fields.Float(string='Maximum Range', help="The maximum amount, applied for this rule.")
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ], string='Amount Type', index=True, required=True, default='fix', help="The computation method for the rule amount.")
    amount_fix = fields.Float(string='Fixed Amount', digits='Fee')
    amount_total = fields.Float(string='Total', digits='Fee', compute='_compute_amount_total')
    amount_percentage = fields.Float(string='Percentage (%)', digits='Fee Rate',
        help='For example, enter 50.0 to apply a percentage of 50%')
    amount_python_compute = fields.Text(string='Python Code',
        default='''
                    # Available variables:
                    #----------------------
                    # payslip: object containing the payslips
                    # employee: hr.employee object
                    # contract: hr.contract object
                    # rules: object containing the rules code (previously computed)
                    # categories: object containing the computed fee rule categories (sum of amount of all rules belonging to that category).
                    # worked_days: object containing the computed worked days.
                    # inputs: object containing the computed inputs.

                    # Note: returned value have to be set in the variable 'result'

                    result = contract.wage * 0.10''')
    amount_percentage_base = fields.Char(string='Percentage based on', help='result will be affected to a variable')
    partner_id = fields.Many2one('res.partner', string='Partner',
        help="Eventual third party involved in the fee payment of the employees.")
    note = fields.Html(string='Description')

    def _raise_error(self, localdict, error_type, e):
        raise UserError(_("""%s:
- Employee: %s
- Contract: %s
- Payslip: %s
- fee rule: %s (%s)
- Error: %s""") % (
            error_type,
            localdict['employee'].name,
            localdict['contract'].name,
            localdict['payslip'].dict.name,
            self.name,
            self.code,
            e))

    def _compute_rule(self, localdict):

        """
        :param localdict: dictionary containing the current computation environment
        :return: returns a tuple (amount, qty, rate)
        :rtype: (float, float, float)
        """
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix or 0.0, float(safe_eval(self.quantity, localdict)), 100.0
            except Exception as e:
                self._raise_error(localdict, _("Wrong quantity defined for:"), e)
        if self.amount_select == 'percentage':
            try:
                return (float(safe_eval(self.amount_percentage_base, localdict)),
                        float(safe_eval(self.quantity, localdict)),
                        self.amount_percentage or 0.0)
            except Exception as e:
                self._raise_error(localdict, _("Wrong percentage base or quantity defined for:"), e)
        else:  # python code
            try:
                safe_eval(self.amount_python_compute or 0.0, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), localdict.get('result_qty', 1.0), localdict.get('result_rate', 100.0)
            except Exception as e:
                self._raise_error(localdict, _("Wrong python code defined for:"), e)

    def _satisfy_condition(self, localdict):
        self.ensure_one()
        if self.condition_select == 'none':
            return True
        if self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result <= self.condition_range_max
            except Exception as e:
                self._raise_error(localdict, _("Wrong range condition defined for:"), e)
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return localdict.get('result', False)
            except Exception as e:
                self._raise_error(localdict, _("Wrong python condition defined for:"), e)

    def _compute_amount_total(self):
        for record in self:
            record.amount_total = record.amount_fix * float(record.quantity)