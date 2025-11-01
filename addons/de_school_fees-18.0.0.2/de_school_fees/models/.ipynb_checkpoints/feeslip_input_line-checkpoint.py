# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FeeslipInput(models.Model):
    _name = 'oe.feeslip.input.line'
    _description = 'Feeslip Input'
    _order = 'feeslip_id, sequence'

    name = fields.Char(string="Description")
    feeslip_id = fields.Many2one('oe.feeslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    input_type_id = fields.Many2one('oe.feeslip.input.type', string='Type', required=True, domain="['|', ('id', 'in', _allowed_input_type_ids), ('struct_ids', '=', False)]")
    _allowed_input_type_ids = fields.Many2many('oe.feeslip.input.type', related='feeslip_id.fee_struct_id.input_line_type_ids')
    code = fields.Char(related='input_type_id.code', required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(
        string="Count",
        help="It is used in computation. E.g. a rule for salesmen having 1%% commission of basic salary per product can defined in expression like: result = inputs.SALEURO.amount * contract.wage * 0.01.")
    #contract_id = fields.Many2one('hr.contract', string='Contract', required=True, help="The contract this input should be applied to")
