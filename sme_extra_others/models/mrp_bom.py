from odoo import models, fields, api, _

class MrpByProduct(models.Model):
    _inherit = 'mrp.bom.byproduct'

    cost_share = fields.Float(
        "Cost Share (%)", digits='Cost Share',  # decimal = 2 is important for rounding calculations!!
        help="The percentage of the final production cost for this by-product line (divided between the quantity produced)."
             "The total of all by-products' cost share must be less than or equal to 100.")