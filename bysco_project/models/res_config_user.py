# -*- coding: utf-8 -*-
import calendar

from odoo import models, fields, api, exceptions, _



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # 每月任务分配明细表
    task_allocation_line_ids = fields.One2many('bysco.task.allocation.detail', 'employee_id', string='每月任务分配明细表')


class ByscoTaskAllocationDetail(models.Model):
    _name = 'bysco.task.allocation.detail'
    _description = "每月任务分配明细表"

    employee_id = fields.Many2one('hr.employee', string='员工')
    # 开始时间，默认取本月1号
    start_date = fields.Date(string='开始时间', default=fields.Date.today().replace(day=1))

    # 结束时间，默认取本月最后一天
    end_date = fields.Date(string='结束时间', default=fields.Date.today().replace(day=calendar.monthrange(fields.Date.today().year, fields.Date.today().month)[1]))

    # 年份月份时间
    year_month = fields.Char(string='年份月份', compute='_compute_year_month', store=True)

    # 根据开始时间和结束时间计算年份月份
    @api.depends('start_date', 'end_date')
    def _compute_year_month(self):
        for record in self:
            if record.start_date and record.end_date:
                record.year_month = record.start_date.strftime('%Y%m')

    # 任务分配数值
    task_allocation = fields.Integer(string='额定工时')

    # 任务分大于0禁止修改如果发生修改则记录到主表
    # @api.onchange('task_allocation')
    # def _onchange_task_allocation(self):
    #     for line in self:
    #         if line.task_allocation:
    #             body = _('任务分配数值修改为：' + str(line._origin.task_allocation) + '-' + str(line.task_allocation))
    #             # 记录修改信息到employee右侧备注栏
    #             line.employee_id.message_post(body=body)


    # 实际得分
    actual_score = fields.Integer(string='得分')





