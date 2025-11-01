# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FeeCategory(models.Model):
    _name = 'oe.fee.category'
    _description = 'Fee Category'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    parent_id = fields.Many2one('oe.fee.category', string='Parent',
        help="Linking a fee category to its parent is used only for the reporting purpose.")
    children_ids = fields.One2many('oe.fee.category', 'parent_id', string='Children')
    note = fields.Html(string='Description')

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive hierarchy of Fee Category.'))

    def _sum_fee_category(self, localdict, amount):
        self.ensure_one()
        if self.parent_id:
            localdict = self.parent_id._sum_fee_category(localdict, amount)
        localdict['categories'].dict[self.code] = localdict['categories'].dict.get(self.code, 0) + amount
        return localdict
