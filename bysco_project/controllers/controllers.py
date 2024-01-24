# -*- coding: utf-8 -*-
# from odoo import http


# class ByscoRepair(http.Controller):
#     @http.route('/bysco_repair/bysco_repair/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bysco_repair/bysco_repair/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('bysco_repair.listing', {
#             'root': '/bysco_repair/bysco_repair',
#             'objects': http.request.env['bysco_repair.bysco_repair'].search([]),
#         })

#     @http.route('/bysco_repair/bysco_repair/objects/<model("bysco_repair.bysco_repair"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bysco_repair.object', {
#             'object': obj
#         })
