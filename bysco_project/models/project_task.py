# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError


class ByscoJobType(models.Model):
    _name = 'bysco.job.type'
    _description = "佰事可工作类型"

    name = fields.Char(string='名称')
    code = fields.Char(string='代码')


class ByscoJobDetails(models.Model):
    _name = 'bysco.job.details'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "佰事可工作详情"

    # 任务编号
    name = fields.Char(string='任务描述', track_visibility='always')
    code = fields.Char(string='编号')
    # 工作人员
    user_id = fields.Many2one('res.users', string='工作人员', default=lambda self: self.env.user, track_visibility='always')
    # 任务类型
    task_type = fields.Many2one('bysco.job.type', string='任务类型', track_visibility='always')

    cancel_reason = fields.Char(string='取消原因')

    # 取消时间
    cancel_date = fields.Datetime(string='取消时间')
    # 取消人员
    cancel_user_id = fields.Many2one('res.users', string='取消人员')

    @api.depends('start_date', 'end_date')
    def _compute_time_spent(self):
        for record in self:
            if record.start_date and record.end_date:
                record.time_spent = (record.end_date - record.start_date).total_seconds() / 3600
            else:
                record.time_spent = 0.0

    # 开始任务，记录开始人员，开始时间，状态跳转到进行中
    def btn_start(self):
        self.write({
            'state': 'confirm',
            'start_user_id': self.env.user.id,
            'start_date': fields.Datetime.now(),
        })

    # 完成任务，记录完成人员，完成时间，状态跳转到完成
    def btn_end(self):
        # 任务结束人员必须与开始人员一致
        if self.start_user_id.id != self.env.user.id:
            raise UserError('任务结束人员必须与开始人员一致')
        self.write({
            'state': 'done',
            'end_user_id': self.env.user.id,
            'end_date': fields.Datetime.now(),
        })

    # 取消任务，记录取消人员，取消时间，状态跳转到取消
    def btn_cancel(self):
        self.write({
            'state': 'cancel',
            'cancel_user_id': self.env.user.id,
            'cancel_date': fields.Datetime.now(),
        })

    # 用时
    time_spent = fields.Float(string='用时', compute='_compute_time_spent')
    state = fields.Selection([('draft', '草稿'), ('confirm', '进行中'), ('done', '完成'), ('cancel', '取消')], string='状态',
                             default='draft', track_visibility='always')
    project_id = fields.Many2one('project.project', string='项目')

    task_id = fields.Many2one('project.task', string='开发任务')

    end_date = fields.Datetime(string='完成时间')
    start_date = fields.Datetime(string='开始时间')

    start_user_id = fields.Many2one('res.users', string='开始人员')
    end_user_id = fields.Many2one('res.users', string='完成人员')

    # 任务分
    task_score = fields.Float(string='任务分')

    @api.model
    def create(self, vals):
        if not vals.get('code', False) or vals['code'] == _(''):
            project_name = 'Test'
            if vals.get('project_id'):
                project_name = self.env['project.project'].sudo().browse(vals.get('project_id')).name
            vals['code'] = project_name.upper() + self.env['ir.sequence'].next_by_code('job.code') or _('')

        result = super(ByscoJobDetails, self).create(vals)
        return result

    description = fields.Html(string="任务评价")


class Task(models.Model):
    _inherit = "project.task"

    code = fields.Char(string='任务编号', index=True, copy=False)
    soft_name = fields.Char(string='软件包', tracking=True)
    plan_date = fields.Datetime(string='计划完成日期', index=True, tracking=True)
    req_source = fields.Char(string='需求来源', tracking=True)
    task_question = fields.Many2many('project.task', 'task_question_rel', 'task_id', 'ques_id',
                                     string='问题关联', tracking=True, domain="[('id','!=',id)]")
    question_list = fields.Many2many('project.task', 'task_question_rel', 'ques_id', 'task_id',
                                     string='问题清单', tracking=True, readonly=True)
    task_optimization = fields.Many2many('project.task', 'task_optimization_rel', 'task_id', 'optim_id',
                                         string='优化关联', domain="[('id','!=',id)]", tracking=True)
    optimization_list = fields.Many2many('project.task', 'task_optimization_rel', 'optim_id', 'task_id',
                                         string='优化清单', tracking=True, readonly=True)
    is_private = fields.Boolean(string="是否个性化", default=False, tracking=True)
    participants = fields.Many2many('res.users', string='参与人', tracking=True)
    # # 开发人员
    # dev_user_id = fields.Many2one('hr.employee', string='开发人员', tracking=True)
    # # 测试人员
    # test_user_id = fields.Many2one('hr.employee', string='测试人员', tracking=True)
    state = fields.Selection([
        ('collect', "需求收集"),
        ('confirm', "需求审核"),
        ('develop', "任务派发"),
        ('code', "接受任务"),
        ('test', "代码推送"),
        ('train', "需求测试"),
        ('criteria', "需求验收"),
        ('fin', "完成"),
        ('cancel', "取消"),
    ], default='collect', string='状态', required=True, tracking=True)

    # 重新评估需求
    def btn_reconfirm(self):
        self.write({
            'state': 'confirm',
        })

    # 提交需求评估，记录提交人，提交时间
    def btn_submit(self):
        create_date = fields.Datetime.now()
        uid = self.env.uid
        self.write({
            'state': 'confirm',
            'confirm_user_id': uid,
            'confirm_date': create_date,
            'test_user_id': uid,
        })
        if not self.xqpg_job_details_id:
            # 获取需求评估task_type
            task_type = self.env['bysco.job.type'].search([('code', '=', 'XQPG')], limit=1)
            # 获取开发主管
            user_id = self.env['hr.employee'].search([('job_title', '=', '开发主管')], limit=1).user_id.id
            #     创建需求评估开始任务
            job_details_id = self.env['bysco.job.details'].create({
                'name': '需求评估-' + self.code,
                'user_id': user_id,
                'project_id': self.project_id.id,
                'start_date': create_date,
                'start_user_id': user_id,
                'task_type': task_type.id,
                'state': 'confirm',
                'task_id': self.id,
            })
            self.xqpg_job_details_id = job_details_id.id
        # 创建需求分析任务
        # xqfx_task_type = self.env['bysco.job.type'].search([('code', '=', 'XQFX')], limit=1)
        # xqfx_job_details_id = self.env['bysco.job.details'].create({
        #     'name': '需求分析-' + self.code,
        #     'user_id': self.env.uid,
        #     'project_id': self.project_id.id,
        #     'start_date': self.create_date,
        #     'start_user_id': self.env.uid,
        #     'end_date': create_date,
        #     'end_user_id': self.env.uid,
        #     'task_type': xqfx_task_type.id,
        #     'task_id': self.id,
        #     'state': 'done'
        # })

    # 需求评估完成，记录评估人，评估时间
    def btn_confirm(self):
        self.write({
            'state': 'develop',
            'develop_user_id': self.env.user.id,
            'develop_date': fields.Datetime.now(),
        })
        # 更新需求评估任务状态、完成时间、完成人
        self.xqpg_job_details_id.write({
            'state': 'done',
            'end_date': fields.Datetime.now(),
            'end_user_id': self.env.user.id,
        })

    xqkf_job_details_id = fields.Many2one('bysco.job.details', string='需求开发工作详情')
    xqpg_job_details_id = fields.Many2one('bysco.job.details', string='需求评估工作详情')

    # 计划完成时间禁止选取今天之前的日期
    @api.onchange('plan_done_date')
    def _onchange_plan_done_date(self):
        if self.plan_done_date and self.plan_done_date < fields.Date.today():
            raise UserError("计划完成时间不能小于今天！")

    # 开发人员接收任务，记录接收人，接收时间
    def btn_develop(self):
        # 每个开发人员每次只能处理一个任务并且接受的任务等级如果不是紧急需要判断当前任务列表是否有紧急，如果有则需要把紧急任务处理完才能接受非紧急任务，有其他任务没处理完禁止接受新任务
        # 获取当前用户的任务列表
        # task_list = self.env['project.task'].search([('code_user_id', '=', self.env.user.id), ('state', '=', 'code')])
        # if task_list:
        #     #     获取任务编号
        #     task_code = task_list.code
        #     raise UserError("您有任务未完成或开发任务测试异常，禁止开发新任务！\n需要处理的任务编号为：%s" % task_code)
        # 查看当前要接受的任务是否为紧急任务
        # if self.priority != '2':
        #     # 当前是否有紧急任务未开发
        #     urgent_task = self.env['project.task'].search_count([('priority', '=', '2'), ('state', '=', 'develop')])
        #     if urgent_task:
        #         raise UserError("紧急任务未全部处理，禁止开发非紧急类型新任务！")
        # 检查计划完成时间plan_done_date是否填写
        if not self.plan_done_date:
            raise UserError("请填写计划完成时间！")
        create_date = fields.Datetime.now()
        self.write({
            'state': 'code',
            'code_user_id': self.env.user.id,
            'code_date': create_date,
        })

        if not self.xqkf_job_details_id:
            task_type = self.env['bysco.job.type'].search([('code', '=', 'XQKF')], limit=1)
            # 创建bysco.job.details任务记录
            job_details_id = self.env['bysco.job.details'].create({
                'name': '开发任务' + self.name,
                'user_id': self.env.uid,
                'project_id': self.project_id.id,
                'task_id': self.id,
                'start_date': create_date,
                'start_user_id': self.env.uid,
                'task_type': task_type.id,
                'state': 'confirm'
            })
            self.xqkf_job_details_id = job_details_id.id

    # 开发人员提交代码，记录提交人，提交时间,提交代码的人与接收任务的人必须是同一个人
    def btn_code(self):
        if self.env.user.id != self.code_user_id.id:
            raise UserError("提交代码的人与接收任务的人必须是同一个人")
        self.write({
            'state': 'test',
            'test_user_id': self.confirm_user_id.id,
            'test_date': fields.Datetime.now(),
        })
        self.xqkf_job_details_id.write({
            'end_date': fields.Datetime.now(),
            'end_user_id': self.env.user.id,
            'state': 'done',
        })

    xqcs_job_details_id = fields.Many2one('bysco.job.details', string='需求测试工作详情')

    # 测试人员开始测试，记录测试人员、测试时间
    def btn_test(self):
        # 测试人员与提交代码人员不能是同一个人
        if self.env.user.id == self.code_user_id.id:
            raise UserError("测试人员与提交代码人员不能是同一个人")
        create_date = fields.Datetime.now()
        self.write({
            'state': 'train',
            'train_user_id': self.env.user.id,
            'train_date': fields.Datetime.now(),
        })
        # 创建需求测试任务
        task_type = self.env['bysco.job.type'].search([('code', '=', 'XQCS')], limit=1)
        # 创建bysco.job.details任务记录
        job_details_id = self.env['bysco.job.details'].create({
            'name': '需求测试 -' + self.code,
            'user_id': self.user_id.id,
            'project_id': self.project_id.id,
            'start_date': create_date,
            'start_user_id': self.user_id.id,
            'task_type': task_type.id,
            'task_id': self.id,
            'state': 'confirm'
        })
        self.xqcs_job_details_id = job_details_id.id

    # 测试失败次数
    test_fail_count = fields.Integer(string='异常', default=0)

    # 测试不通过，需求人员填写测试缺陷，驳回任务到开发人员，记录驳回人、驳回时间
    def btn_train(self):
        # 测试驳回人员与测试人员必须是同一人
        if self.env.user.id != self.train_user_id.id:
            raise UserError("测试驳回人员与测试人员必须是同一人")
        # 弹窗填写测试缺陷
        post_task_id = self.env['bicycle.project.reject'].create({'task_id': self.id})
        pop_up_windows_view = {
            'type': 'ir.actions.act_window',
            'name': '测试缺陷',
            'res_model': 'bicycle.project.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': post_task_id.id,
            'target': 'new',
        }
        self._compute_actual_hour()
        return pop_up_windows_view

    # 测试通过，需求人员验收，记录验收人、验收时间
    def btn_criteria(self):
        # 测试完成人员与测试人员必须是同一人
        if self.env.user.id != self.train_user_id.id:
            raise UserError("测试人员与测试人员必须是同一人")
        self.write({
            'state': 'fin',
            'fin_user_id': self.env.user.id,
            'fin_date': fields.Datetime.now(),
        })
        #     更新测试任务状态、结束时间、结束人
        self.xqcs_job_details_id.write({
            'end_date': fields.Datetime.now(),
            'end_user_id': self.env.user.id,
            'state': 'done',
        })
        self._compute_actual_hour()

    collect_date = fields.Datetime(string='收集日期')
    confirm_date = fields.Datetime(string='审核日期')
    confirm_user_id = fields.Many2one('res.users', string='审核人')
    develop_date = fields.Datetime(string='派发日期')
    develop_user_id = fields.Many2one('res.users', string='派发人')
    code_date = fields.Datetime(string='接受日期')
    code_user_id = fields.Many2one('res.users', string='开发')
    test_date = fields.Datetime(string='推送日期')
    test_user_id = fields.Many2one('res.users', string='测试')
    train_date = fields.Datetime(string='测试日期')
    train_user_id = fields.Many2one('res.users', string='测试人')
    fin_date = fields.Datetime(string='完成日期')

    fin_user_id = fields.Many2one('res.users', string='完成人')
    cancel_date = fields.Datetime(string='取消日期')
    postscript_data = fields.Char(string='驳回原因', track_visibility='onchange')
    task_type = fields.Selection([
        ('req', "需求"),
        ('que', "问题"),
        ('opt', "优化"),
    ], default='req', string='任务类型', required=True, tracking=True)
    test_ids = fields.One2many('bicycle.task.test.record', 'task_id', string='测试记录', tracking=True)

    app_user_id = fields.Many2one('res.users', string='应用负责人', tracking=True)
    app_job_grade = fields.Selection(related="app_user_id.job_grade", string="应用岗位等级", store=True, readonly=True)
    tech_job_grade = fields.Selection(related="user_id.job_grade", string="技术岗位等级", store=True, readonly=True)
    priority = fields.Selection([
        ('0', '一般'),
        ('1', '重要'),
        ('2', '紧急'),
    ], default='0', index=True, required=True, string="优先级", tracking=True)
    diff_coeff = fields.Selection([
        ('1.0', "一级"), ('2.0', "二级"), ('3.0', "三级"), ('4.0', "四级"), ('5.0', "五级")
    ], default='1.0', required=True, string="难度系数", tracking=True)
    tech_score_bug = fields.Selection([
        ('50', "合格"), ('40', "一般"), ('20', "严重")
    ], default='', string="缺陷评分", tracking=True)
    tech_score_bug_char = fields.Float(compute='_compute_tech_task')
    tech_score_time = fields.Selection([
        ('50', "准时"), ('30', "延迟"), ('60', "提前")
    ], default='', string="时效评分", tracking=True)
    tech_score_time_char = fields.Float(compute='_compute_tech_task')
    tech_task_score = fields.Float(string='评分')

    app_score_bug = fields.Selection([
        ('50', "合格"), ('40', "一般"), ('20', "严重")
    ], default='', string="质量评分", tracking=True)
    app_score_time = fields.Selection([
        ('50', "准时"), ('30', "延迟"), ('60', "提前")
    ], default='', string="时效评分", tracking=True)

    # 客户要求完成时间
    client_done_date = fields.Date(string='客户要求时间', tracking=True)

    plan_man_hour = fields.Float(string='任务额定工时', tracking=True, default=1)
    task_allocation = fields.Float(string='任务分配工时', tracking=True, default=1)
    plan_done_date = fields.Date(string='计划完成时间')

    # 实得工时
    actual_hour = fields.Float(string='任务实得工时', compute='_compute_actual_hour', store=True)

    # 计算实得工时
    @api.depends('test_ids')
    def _compute_actual_hour(self):
        # 难度系数与容错计数,容错基数=难度系数*2，容错次数=难度系数
        difficulty = {'1.0': {'rcjs': 2, 'rccs': 1},
                      '2.0': {'rcjs': 4, 'rccs': 2},
                      '3.0': {'rcjs': 6, 'rccs': 3},
                      '4.0': {'rcjs': 8, 'rccs': 4},
                      '5.0': {'rcjs': 10, 'rccs': 5}}
        for rec in self:
            diff_coeff = difficulty[rec.diff_coeff]
            if rec.test_fail_count > diff_coeff['rccs']:
                # 实得工时 = 计划工时×(1-(报错次数-容错次数)/容错基数)
                actual_hour = rec.plan_man_hour * (1 - (rec.test_fail_count - diff_coeff['rccs']) / diff_coeff['rcjs'])
            else:
                actual_hour = rec.plan_man_hour
            rec.actual_hour = actual_hour

    @api.depends('diff_coeff', 'tech_score_time', 'tech_score_bug', 'state')
    def _compute_tech_task(self):
        for rec in self:
            rec.tech_score_time_char = 100
            rec.tech_score_bug_char = 100

    def return_confirm(self):
        state_infos = ''
        self.ensure_one()
        if self.state == 'confirm':
            state_infos = 'collect'
        if self.state == 'develop':
            state_infos = 'confirm'
        if self.state == 'code':
            state_infos = 'develop'
        if self.state == 'test':
            state_infos = 'code'
        if self.state == 'train':
            state_infos = 'test'
        if self.state == 'criteria':
            state_infos = 'train'
        return self.action_pop_up_windows(state_infos)

    def action_pop_up_windows(self, state_infos):
        post_task_id = self.env['bicycle.project.reject'].create(
            {'task_id': self.id, 'state_info': state_infos})
        pop_up_windows_view = {
            'type': 'ir.actions.act_window',
            'name': '驳回原因',
            'res_model': 'bicycle.project.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': post_task_id.id,
            'target': 'new',
        }
        return pop_up_windows_view

    @api.model
    def create(self, vals):
        if not vals.get('code', False) or vals['code'] == _(''):
            project_name = 'BSC'
            if vals.get('project_id'):
                project_name = self.env['project.project'].sudo().browse(vals.get('project_id')).name
            vals['code'] = project_name.upper() + self.env['ir.sequence'].next_by_code(self._name) or _('')

        result = super(Task, self).create(vals)
        return result


class TaskTestRecord(models.Model):
    _name = 'bicycle.task.test.record'
    _description = "任务测试记录"

    name = fields.Char(string='内容提要')
    desc = fields.Char(string='内容描述')
    task_id = fields.Many2one('project.task')
    description = fields.Html(string="缺陷报告")

    # 删除无效测试记录
    def btn_delete(self):
        self.ensure_one()
        self.unlink()
        #   task_id的test_fail_count减1
        self.task_id.write({
            'test_fail_count': self.task_id.test_fail_count - 1
        })


class bicycleProjectReject(models.Model):
    _name = 'bicycle.project.reject'
    _description = "驳回原因"

    postscript_data = fields.Char(string='驳回原因')
    description = fields.Html(string="缺陷报告")
    task_id = fields.Many2one('project.task')
    state_info = fields.Char(string="记录状态")

    def write_postscript_data(self):
        self.task_id.write({
            'state': 'code',
            'test_fail_count': self.task_id.test_fail_count + 1
        })
        # 创建测试异常记录
        self.env['bicycle.task.test.record'].create({
            'task_id': self.task_id.id,
            'create_uid': self.env.uid,
            'description': self.description
        })
        # 修改任务状态
        # for line in self:
        #     line.task_id.write({'postscript_data': line.postscript_data})
        #     if self.state_info == 'collect':
        #         line.task_id.write({'state': 'collect'})
        #     if self.state_info == 'confirm':
        #         line.task_id.write({'state': 'confirm'})
        #     if self.state_info == 'develop':
        #         line.task_id.write({'state': 'develop'})
        #     if self.state_info == 'code':
        #         line.task_id.write({'state': 'code'})
        #     if self.state_info == 'test':
        #         line.task_id.write({'state': 'test'})
        #     if self.state_info == 'train':
        #         line.task_id.write({'state': 'train'})
        #     if self.state_info == 'criteria':
        #         line.task_id.write({'state': 'criteria'})


class Users(models.Model):
    _inherit = "res.users"

    job_grade = fields.Selection([
        ('0.5', "见习"), ('1.0', "初级"), ('1.5', "中级"), ('2.0', "高级")
    ], default='0.5', string="岗位等级", tracking=True)
