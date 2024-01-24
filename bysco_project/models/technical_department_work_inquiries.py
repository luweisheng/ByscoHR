# -*- coding: utf-8 -*-
import calendar
import datetime
from datetime import timedelta

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError


class ByscoTechnicalDepartmentWorkInquiries(models.TransientModel):
    _name = 'bysco.technical.department.work.inquiries'
    _description = "开发任务工作情况查询"

    user_ids = fields.Many2many('res.users', 'user_ids', string='工作人员')
    start_date = fields.Date(string='开始时间')
    end_date = fields.Date(string='结束时间')
    time_horizon = fields.Selection([('today', '今日'), ('week', '本周'), ('month', '本月'), ('year', '本年')],
                                    string='时间范围', default='month')

    position_ids = fields.Many2many('hr.job', 'position_ids', string='职位')

    # 获取技术部门的id
    def _get_default_department_ids(self):
        department_ids = self.env['hr.department'].search([('name', '=', '技术')]).ids
        return department_ids

    department_ids = fields.Many2many('hr.department', 'department_ids', string='部门',
                                      default=lambda self: self._get_default_department_ids())

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
    work_report_inquiry_line_ids = fields.One2many('bysco.technical.department.work.inquiries.detail', 'work_report_id',
                                                   string='工作查询子表')


    # 团队完成率
    team_completion_rate = fields.Float(string='团队完成率')

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
        user_ids = self.user_ids.ids

        if user_ids and self.start_date and self.end_date:
            work_line = {}
            task_allocation_total_hours = 0
            task_effective_total_hours = 0
            for u_line in user_ids:
                work_line[u_line] = {
                    'user_id': u_line,
                    'task_done_hours': 0,
                    'test_fail_count': 0,
                    'task_effective_hours': 0,
                }
            # 查询开发任务，根据用户分组，统计完成的任务数量和总工时，刷新工作子表
            work_ids = self.env['project.task'].search([('code_user_id', 'in', user_ids),
                                                        ('state', '=', 'fin'),
                                                        ('fin_date', '>=', self.start_date),
                                                        ('fin_date', '<=', self.end_date)])
            total_task_score = 0
            total_test_fail_count = 0
            for line in work_ids:
                code_user_id = line.code_user_id.id
                if code_user_id in work_line:
                    work_line[code_user_id]['task_done_hours'] += line.plan_man_hour
                    work_line[code_user_id]['test_fail_count'] += line.test_fail_count
                    work_line[code_user_id]['task_effective_hours'] += line.actual_hour
                else:
                    work_line[code_user_id] = {
                        'user_id': code_user_id,
                        'task_done_hours': line.plan_man_hour,
                        'test_fail_count': line.test_fail_count,
                        'task_effective_hours': line.actual_hour,
                    }
                total_task_score += line.actual_hour
                total_test_fail_count += line.test_fail_count
            # 刷新工作子表
            self.work_report_inquiry_line_ids = None
            work_report_inquiry_line_ids = []
            for key, value in work_line.items():
                task_effective_hours = value['task_effective_hours']
                if total_task_score > 0:
                    value['task_hours_proportion'] = task_effective_hours / total_task_score
                if total_test_fail_count > 0:
                    value['test_fail_proportion'] = value['test_fail_count'] / total_test_fail_count
                if value['task_done_hours'] > 0:
                    value['test_fail_rate'] = value['test_fail_count'] / value['task_done_hours']
                # 获取本月年月
                year = datetime.datetime.now().year
                month = datetime.datetime.now().month
                if month < 10:
                    year_month = str(year) + '0' + str(month)
                else:
                    year_month = str(year) + str(month)
                # 获取员工本月分配任务工时task_allocation
                task_allocation = self.env['bysco.task.allocation.detail'].search(
                    [('employee_id.user_id', '=', value['user_id']),
                     ('year_month', '=', year_month)]).task_allocation
                value['task_allocation'] = task_allocation
                task_allocation_total_hours += task_allocation
                # 计算本月完成率
                if task_allocation > 0:
                    value['task_done_rate'] = task_effective_hours / task_allocation
                else:
                    value['task_done_rate'] = 0
                task_effective_total_hours += task_effective_hours
                work_report_inquiry_line_ids.append((0, 0, value))
            # 计算团队完成率
            if task_allocation_total_hours > 0:
                self.team_completion_rate = task_effective_total_hours / task_allocation_total_hours
            else:
                self.team_completion_rate = 0
            self.work_report_inquiry_line_ids = work_report_inquiry_line_ids


# 工作报告明细表
class ByscoTechnicalDepartmentWorkInquiriesDetail(models.TransientModel):
    _name = 'bysco.technical.department.work.inquiries.detail'
    _description = "工作报告明细表"

    work_report_id = fields.Many2one('bysco.technical.department.work.inquiries', string='工作报告')
    # 职工
    user_id = fields.Many2one('res.users', string='姓名')
    # 部门
    department = fields.Char(string='部门')
    # 职位
    position = fields.Char(string='职位')
    # 已完成工作的数量
    work_done_count = fields.Integer(string='完成')
    # 完成工时
    work_done_hours = fields.Integer(string='完成工时')
    # 错误
    test_fail_count = fields.Integer(string='错误')
    # 工作评分
    work_score = fields.Integer(string='工作评分')
    # 任务数
    task_count = fields.Integer(string='完成')
    task_done_hours = fields.Float(string='领取计划工时')
    task_allocation = fields.Float(string='本月额定工时')
    task_fail_count = fields.Integer(string='错误')
    task_effective_hours = fields.Float(string='有效工时')
    task_effective_rate = fields.Float(string='有效率')
    # 工时总占比
    task_hours_proportion = fields.Float(string='工时总占比')
    # 错误占比
    test_fail_proportion = fields.Float(string='错误占比')
    # 错误率
    test_fail_rate = fields.Float(string='错误率')
    # 本月完成率
    task_done_rate = fields.Float(string='本月完成率')
    # 打开当前工作人员完成工作bysco.job.details，tree视图
    def tasks_work_tree(self):
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
