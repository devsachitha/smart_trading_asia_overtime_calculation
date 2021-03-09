from flectra import api, fields, models, _
from datetime import date,datetime,timedelta


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')

    @api.model
    def create(self,vals):
        vals['from_date'] = datetime.strptime(vals['date_from'], '%Y-%m-%d %H:%M:%S').date()
        vals['to_date'] = datetime.strptime(vals['date_to'], '%Y-%m-%d %H:%M:%S').date()
        return super(ResourceCalendarLeaves, self).create(vals)
