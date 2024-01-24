# -*- coding: utf-8 -*-
import calendar
import datetime
from datetime import timedelta

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError


class ByscoWorkReportInquiry(models.TransientModel):
    _name = 'bysco.work.report.inquiry'
    _description = "工作查询"

    user_ids = fields.Many2many('res.users', 'user_ids', string='工作人员')
    start_date = fields.Date(string='开始时间')
    end_date = fields.Date(string='结束时间')
    time_horizon = fields.Selection([('today', '今日'), ('week', '本周'), ('month', '本月'), ('year', '本年')],
                                    string='时间范围', default='today')

    position_ids = fields.Many2many('hr.job', 'position_ids', string='职位')

    #
    department_ids = fields.Many2many('hr.department', 'department_ids', string='部门')

    # 根据部门变化，更新用户信息
    @api.onchange('department_ids')
    def _onchange_department_ids(self):
        if self.department_ids:
            self.user_ids = None
            user_ids = self.env['hr.employee'].search([('department_id', 'in', self.department_ids.ids)]).user_id.ids
            self.user_ids = user_ids

    # 工作状态
    work_state = fields.Selection([('confirm', '进行中'), ('done', '完成')], string='工作进度', default='done', required=True)

    # 工作查询子表
    work_report_inquiry_line_ids = fields.One2many('bysco.work.report.detail', 'work_report_id', string='工作查询子表')

    @api.onchange('time_horizon')
    def _set_default_date(self):
        time_horizon = self.time_horizon
        # 根据用户选择的时间范围，设置默认的开始时间和结束时间
        if time_horizon == 'today':
            self.start_date = fields.Date.today()
            self.end_date = fields.Date.today()
        elif time_horizon == 'week':
            self.start_date = fields.Date.today() - timedelta(days=datetime.datetime.now().weekday())
            self.end_date = fields.Date.today() + timedelta(days=6 - datetime.datetime.now().weekday())
        elif time_horizon == 'month':
            self.start_date = fields.Date.today().replace(day=1)
            self.end_date = fields.Date.today().replace(
                day=calendar.monthrange(fields.Date.today().year, fields.Date.today().month)[1])
        elif time_horizon == 'year':
            self.start_date = fields.Date.today().replace(month=1, day=1)
            self.end_date = fields.Date.today().replace(month=12, day=31)

    # 根据工作人员、开始时间、结束时间查询工作报告
    @api.onchange('user_ids', 'start_date', 'end_date')
    def inquiry_work_report(self):
        if self.user_ids and self.start_date and self.end_date:
            work_line = {}
            # 查询开发任务，根据用户分组，统计完成的任务数量和总工时，刷新工作子表
            work_ids = self.env['bysco.job.details'].search([('user_id', 'in', self.user_ids.ids),
                                                             ('state', '=', 'done'),
                                                             ('end_date', '>=', self.start_date),
                                                             ('end_date', '<=', self.end_date)])
            for line in work_ids:
                if line.user_id.id in work_line:
                    work_line[line.user_id.id]['task_count'] += 1
                else:
                    work_line[line.user_id.id] = {
                        'user_id': line.user_id.id,
                        'department': line.user_id.department_id.name,
                        'task_count': 1,
                    }
            # 刷新工作子表
            self.work_report_inquiry_line_ids = None
            work_report_inquiry_line_ids = []

            for key, value in work_line.items():

                work_report_inquiry_line_ids.append((0, 0, value))
            self.work_report_inquiry_line_ids = work_report_inquiry_line_ids


# 工作报告明细表
class ByscoWorkReportDetail(models.TransientModel):
    _name = 'bysco.work.report.detail'
    _description = "工作报告明细表"

    work_report_id = fields.Many2one('bysco.work.report.inquiry', string='工作报告')
    # 职工
    user_id = fields.Many2one('res.users', string='姓名')
    # 部门
    department = fields.Char(string='部门')
    # 职位
    position = fields.Char(string='职位')
    # 已完成工作的数量
    work_done_count = fields.Integer(string='完成')
    # 完成工时
    work_done_hours = fields.Integer(string=' 完成工时')
    # 错误
    test_fail_count = fields.Integer(string='错误')
    # 工作评分
    work_score = fields.Integer(string='工作评分')

    # 任务数
    task_count = fields.Integer(string='完成')

    def tasks_work_tree(self):
        # print('打开当前工作人员的任务')
        # 打开当前工作人员完成工作bysco.job.details，tree视图
        return {
            'name': _('工作报告'),
            'view_mode': 'tree',
            'res_model': 'bysco.job.details',
            'type': 'ir.actions.act_window',
            'domain': [('user_id', '=', self.user_id.id),
                       ('state', '=', 'done'),
                       ('end_date', '>=', self.work_report_id.start_date),
                       ('end_date', '<=', self.work_report_id.end_date)],
            'context': {'create': False},
            'target': 'current',
        }