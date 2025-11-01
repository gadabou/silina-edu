#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class FeeStructure(models.Model):
    _name = 'oe.fee.struct'
    _description = 'Fee Structure'

    @api.model
    def _get_default_report_id(self):
        return self.env.ref('hr_payroll.action_report_payslip', False)

    
    @api.model
    def _get_default_rule_ids(self):
        return False

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    #type_id = fields.Many2one('hr.payroll.structure.type', required=True)
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.company.country_id)
    note = fields.Html(string='Description')
    rule_ids = fields.One2many(
        'oe.fee.rule', 'fee_struct_id',
        string='Fee Rules', default=_get_default_rule_ids)
    #report_id = fields.Many2one('ir.actions.report', string="Report", domain="[('model','=','hr.payslip'),('report_type','=','qweb-pdf')]", default=_get_default_report_id)
    payslip_name = fields.Char(string="Payslip Name", translate=True,
        help="Name to be set on a payslip. Example: 'End of the year bonus'. If not set, the default value is 'Fee Slip'")
    use_enrollment_contract_lines = fields.Boolean(default=True, help="contract lines won't be computed/displayed in fee slips.")
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('tri-annually', 'Tri-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], compute='_compute_schedule_pay', store=True, readonly=False,
    string='Scheduled Pay', index=True,
    help="Defines the frequency of the wage payment.")
    input_line_type_ids = fields.Many2many('oe.feeslip.input.type', string='Other Input Line')
    
    # Academic Fields
    course_id = fields.Many2one('oe.school.course', string='Course')
    batch_ids = fields.Many2many('oe.school.course.batch', string='Course Batches')


    #@api.depends('type_id')
    def _compute_schedule_pay(self):
        for structure in self:
            #if not structure.type_id:
            structure.schedule_pay = 'monthly'
            #elif not structure.schedule_pay:
            #structure.schedule_pay = structure.type_id.default_schedule_pay
