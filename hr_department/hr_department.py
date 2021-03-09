from flectra import api, fields, models, _


class Department(models.Model):
    _inherit = 'hr.department'

    allow_overtime = fields.Boolean(string='Overtime Calculation', default=False)
    allow_weekday_overtime = fields.Boolean(string='WeekDay Overtime Calculation', default=False)
    allow_weekend_overtime = fields.Boolean(string='WeekEnd Overtime Calculation', default=False)
    weekdays_overtime = fields.Float(string='Week day Overtime Starts with', default=00.00)
    weekends_overtime = fields.Float(string='Week end Overtime Starts with', default=00.00)

