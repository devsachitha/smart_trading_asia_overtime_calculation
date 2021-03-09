from flectra import fields, api, models, _
from datetime import date, datetime, timedelta
from ast import literal_eval
import datetime
import time
from flectra.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import pytz
from zk import ZK, const
import socket


class codesoHrOvertime(models.Model):
    _name = "codeso.hr.overtime"
    _description = "codeso Hr Overtime"
    _rec_name = 'employee_id'
    _order = 'id desc'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    manager_id = fields.Many2one('hr.employee', string='Manager')
    start_date = fields.Datetime('Check IN')
    end_date = fields.Datetime('Check OUT')
    normal_overtime_hours = fields.Float('Normal Overtime Hours')
    double_overtime_hours = fields.Float('Double Overtime Hours')
    notes = fields.Text(string='Notes')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'),
                              ('validate', 'Approved'), ('cancel', 'Cancelled')], default='draft', copy=False)
    attendance_id = fields.Many2one('hr.attendance', string='Attendance')

    @api.model
    def set_overtime_reset(self):
        all_attendance_records = self.env['hr.attendance'].search([])
        if all_attendance_records:
            for r in all_attendance_records:
                r.write({'overtime_created': False})

    @api.model
    def run_overtime_scheduler(self):
        attendance_records = self.env['hr.attendance'].search([('overtime_created', '=', False)])
        for attendance_record in attendance_records:
            if attendance_record.check_out:
                source_checkin_date_time = str(attendance_record.sudo().check_in)
                checkin_date_time = datetime.datetime.strptime(source_checkin_date_time, '%Y-%m-%d %H:%M:%S')
                checkin_with_time_zone = checkin_date_time + timedelta(hours=5, minutes=30)

                # standard start time
                standard_date = str(datetime.datetime.strptime(source_checkin_date_time, '%Y-%m-%d %H:%M:%S').date())
                standard_date_time = standard_date + ' ' + '08:00:00'
                standard_date_time = datetime.datetime.strptime(standard_date_time, '%Y-%m-%d %H:%M:%S')

                source_checkout_date_time = str(attendance_record.sudo().check_out)
                checkout_date_time = datetime.datetime.strptime(source_checkout_date_time, '%Y-%m-%d %H:%M:%S')
                checkout_with_time_zone = checkout_date_time + timedelta(hours=5, minutes=30)

                get_day_number = checkout_with_time_zone.weekday()
                checkout_date_time_ot = checkout_with_time_zone + timedelta(minutes=30)
                employee_contract = self.env['hr.contract'].search(
                    [('employee_id', '=', attendance_record.employee_id.id), ('state', '=', 'open')])
                department = attendance_record.employee_id.department_id
                if department.allow_overtime:
                    wkdays_overtime = department.weekdays_overtime
                    covert_to_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(wkdays_overtime * 60, 60))
                    standard_format = covert_to_time + ':' + '00'
                    wkdays_overtime = datetime.datetime.strptime(standard_format, '%H:%M:%S').time()

                    wkends_overtime = department.weekends_overtime
                    covert_to_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(wkends_overtime * 60, 60))
                    standard_format = covert_to_time + ':' + '00'
                    wkends_overtime = datetime.datetime.strptime(standard_format, '%H:%M:%S').time()

                    # actual worked hours
                    actual_worked_time = checkout_with_time_zone - checkin_with_time_zone
                    actual_worked_hours = int(str(actual_worked_time).split(':')[0])

                    standard_worked_time = checkout_with_time_zone - standard_date_time

                    # check the day is a global leave or not
                    public_holidays = self.env['resource.calendar.leaves']
                    check_public_holiday = public_holidays.search(
                        [('from_date', '=', str(checkout_date_time_ot.date()))])

                    # if the day is a holiday or a Sunday
                    if check_public_holiday or get_day_number == 6:
                        split_time_record = str(standard_worked_time).split(':')
                        time_difference_hours = split_time_record[0]
                        time_difference_mins = int(split_time_record[1])
                        if time_difference_mins < 30:
                            time_difference_mins = 00
                        elif time_difference_mins >= 30:
                            time_difference_mins = 30
                        time_difference_float = time_difference_hours + '.' + str(time_difference_mins)
                        vals = {
                            'employee_id': attendance_record.employee_id and attendance_record.employee_id.id or False,
                            'manager_id': attendance_record.employee_id and attendance_record.employee_id.parent_id and attendance_record.employee_id.parent_id.id or False,
                            'start_date': attendance_record.check_in,
                            'end_date': attendance_record.check_out,
                            'normal_overtime_hours': 0,
                            'double_overtime_hours': round(float(time_difference_float), 2),
                            'attendance_id': attendance_record.id,
                        }
                        self.env['codeso.hr.overtime'].create(vals)
                        attendance_record.overtime_created = True

                    # if the worked day is a week day
                    elif get_day_number in (0, 1, 2, 3, 4):
                        # if actual working hours below 4 hours the working time will be considered as overtime
                        if actual_worked_hours < 4:
                            split_time_record = str(actual_worked_time).split(':')
                            time_difference_hours = split_time_record[0]
                            time_difference_mins = int(split_time_record[1])
                            if time_difference_mins < 30:
                                time_difference_mins = 00
                            elif time_difference_mins >= 30:
                                time_difference_mins = 30
                            time_difference_float = time_difference_hours + '.' + str(time_difference_mins)
                            vals = {
                                'employee_id': attendance_record.employee_id and attendance_record.employee_id.id or False,
                                'manager_id': attendance_record.employee_id and attendance_record.employee_id.parent_id and attendance_record.employee_id.parent_id.id or False,
                                'start_date': attendance_record.check_in,
                                'end_date': attendance_record.check_out,
                                'normal_overtime_hours': round(float(time_difference_float), 2),
                                'double_overtime_hours': 0,
                                'attendance_id': attendance_record.id,
                            }
                            self.env['codeso.hr.overtime'].create(vals)
                            attendance_record.overtime_created = True

                        # if worked hours more than four hours and worked hours is lager than the standard working hours
                        elif actual_worked_hours >= 4:
                            checkout_time = checkout_with_time_zone.time()
                            FMT = '%H:%M:%S'
                            if datetime.datetime.strptime(str(wkdays_overtime), FMT) < \
                                    datetime.datetime.strptime(str(checkout_time), FMT):

                                ot_time = datetime.datetime.strptime(str(checkout_time), FMT) - datetime.datetime.strptime(
                                    str(wkdays_overtime), FMT)
                                split_time_record = str(ot_time).split(':')
                                time_difference_hours = split_time_record[0]
                                time_difference_mins = int(split_time_record[1])
                                if time_difference_mins < 30:
                                    time_difference_mins = 00
                                elif time_difference_mins >= 30:
                                    time_difference_mins = 30
                                time_difference_float = time_difference_hours + '.' + str(time_difference_mins)
                                vals = {
                                    'employee_id': attendance_record.employee_id and attendance_record.employee_id.id or False,
                                    'manager_id': attendance_record.employee_id and attendance_record.employee_id.parent_id and attendance_record.employee_id.parent_id.id or False,
                                    'start_date': attendance_record.check_in,
                                    'end_date': attendance_record.check_out,
                                    'normal_overtime_hours': round(float(time_difference_float), 2),
                                    'double_overtime_hours': 0,
                                    'attendance_id': attendance_record.id,
                                }
                                self.env['codeso.hr.overtime'].create(vals)
                                attendance_record.overtime_created = True
                            else:
                                pass

                    # if worked day is a Saturday
                    elif get_day_number == 5:
                        checkout_time = checkout_with_time_zone.time()
                        FMT = '%H:%M:%S'
                        # saturday checkout time if later than the over time calculation time
                        if department.weekends_overtime:
                            if datetime.datetime.strptime(str(wkends_overtime), FMT) < \
                                    datetime.datetime.strptime(str(checkout_time), FMT):
                                ot_time = datetime.datetime.strptime(str(checkout_time),
                                                                     FMT) - datetime.datetime.strptime(
                                    str(wkends_overtime), FMT)
                                split_time_record = str(ot_time).split(':')
                                time_difference_hours = split_time_record[0]
                                time_difference_mins = int(split_time_record[1])
                                if time_difference_mins < 30:
                                    time_difference_mins = 00
                                elif time_difference_mins >= 30:
                                    time_difference_mins = 30
                                time_difference_float = time_difference_hours + '.' + str(time_difference_mins)
                                vals = {
                                    'employee_id': attendance_record.employee_id and attendance_record.employee_id.id or False,
                                    'manager_id': attendance_record.employee_id and attendance_record.employee_id.parent_id and attendance_record.employee_id.parent_id.id or False,
                                    'start_date': attendance_record.check_in,
                                    'end_date': attendance_record.check_out,
                                    'normal_overtime_hours': round(float(time_difference_float), 2),
                                    'double_overtime_hours': 0,
                                    'attendance_id': attendance_record.id,
                                }
                                self.env['codeso.hr.overtime'].create(vals)
                                attendance_record.overtime_created = True
                        elif not department.weekends_overtime:
                            split_time_record = str(standard_worked_time).split(':')
                            time_difference_hours = split_time_record[0]
                            time_difference_mins = int(split_time_record[1])
                            if time_difference_mins < 30:
                                time_difference_mins = 00
                            elif time_difference_mins >= 30:
                                time_difference_mins = 30
                            time_difference_float = time_difference_hours + '.' + str(time_difference_mins)
                            vals = {
                                'employee_id': attendance_record.employee_id and attendance_record.employee_id.id or False,
                                'manager_id': attendance_record.employee_id and attendance_record.employee_id.parent_id and attendance_record.employee_id.parent_id.id or False,
                                'start_date': attendance_record.check_in,
                                'end_date': attendance_record.check_out,
                                'normal_overtime_hours': round(float(time_difference_float), 2),
                                'double_overtime_hours': 0,
                                'attendance_id': attendance_record.id,
                            }
                            self.env['codeso.hr.overtime'].create(vals)
                            attendance_record.overtime_created = True
                        else:
                            pass
                    else:
                        pass

    @api.multi
    def action_submit(self):
        return self.write({'state': 'confirm'})

    @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def action_approve(self):
        return self.write({'state': 'validate'})

    @api.multi
    def action_refuse(self):
        return self.write({'state': 'refuse'})

    @api.multi
    def action_view_attendance(self):
        attendances = self.mapped('attendance_id')
        action = self.env.ref('hr_attendance.hr_attendance_action').read()[0]
        if len(attendances) > 1:
            action['domain'] = [('id', 'in', attendances.ids)]
        elif len(attendances) == 1:
            action['views'] = [(self.env.ref('hr_attendance.hr_attendance_view_form').id, 'form')]
            action['res_id'] = self.attendance_id.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    overtime_created = fields.Boolean(string='Overtime Created', default=False, copy=False)


