# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FeeslipLine(models.Model):
    _name = 'oe.feeslip.line'
    _description = 'Feeslip Line'
    _order = 'sequence, code'

    name = fields.Char(required=True)
    note = fields.Text(string='Description')
    sequence = fields.Integer(required=True, index=True, default=5,
                              help='Use to arrange calculation sequence')
    code = fields.Char(required=True,
                       help="The code of salary rules can be used as reference in computation of other rules. "
                       "In that case, it is case sensitive.")
    feeslip_id = fields.Many2one('oe.feeslip', string='Fee Slip', required=True, ondelete='cascade')
    fee_rule_id = fields.Many2one('oe.fee.rule', string='Rule', required=True)
    #contract_id = fields.Many2one('hr.contract', string='Contract', required=True, index=True)
    student_id = fields.Many2one('res.partner', string='Student', required=True)
    rate = fields.Float(string='Rate (%)', digits='Payroll Rate', default=100.0)
    amount = fields.Monetary()
    quantity = fields.Float(digits='Fee', default=1.0)
    total = fields.Monetary(compute='_compute_total', string='Total', store=True)

    amount_select = fields.Selection(related='fee_rule_id.amount_select', readonly=True)
    amount_fix = fields.Float(related='fee_rule_id.amount_fix', readonly=True)
    amount_percentage = fields.Float(related='fee_rule_id.amount_percentage', readonly=True)
    appears_on_feeslip = fields.Boolean(related='fee_rule_id.appears_on_feeslip', readonly=True)
    category_id = fields.Many2one(related='fee_rule_id.category_id', readonly=True, store=True)
    partner_id = fields.Many2one(related='fee_rule_id.partner_id', readonly=True, store=True)

    date_from = fields.Date(string='From', related="feeslip_id.date_from", store=True)
    date_to = fields.Date(string='To', related="feeslip_id.date_to", store=True)
    company_id = fields.Many2one(related='feeslip_id.company_id')
    currency_id = fields.Many2one('res.currency', related='feeslip_id.currency_id')

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100

    @api.model_create_multi
    def create1(self, vals_list):
        for values in vals_list:
            if 'student_id' not in values or 'contract_id' not in values:
                feeslip = self.env['oe.fee.slip'].browse(values.get('feeslip_id'))
                values['student_id'] = values.get('student_id') or feeslip.student_id.id
                values['contract_id'] = values.get('contract_id') or feeslip.contract_id and feeslip.contract_id.id
                if not values['contract_id']:
                    raise UserError(_('You must set a contract to create a payslip line.'))
        return super(FeeslipLine, self).create(vals_list)
