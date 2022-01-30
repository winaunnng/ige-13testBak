from odoo import models
import string


class HrJobReport(models.AbstractModel):
    _name = 'report.sme_hr.xlsx_hr_job_report'
    _description = 'HR Job Position Report Xlsx'
    _inherit = 'report.report_xlsx.abstract'


    def generate_xlsx_report(self, workbook, data, job_ids):
        format1 = workbook.add_format(
            {'font_size': 12, 'align': 'vcenter', 'bold': True, 'bg_color': '#d3dde3', 'color': 'black',
             'bottom': True, })
        format2 = workbook.add_format(
            {'font_size': 12, 'align': 'vcenter', 'bold': True, 'bg_color': '#edf4f7', 'color': 'black',
             'num_format': '#,##0'})
        format3 = workbook.add_format({'font_size': 11, 'align': 'vcenter', 'bold': False, 'num_format': '#,##0.00'})
        format3_colored = workbook.add_format(
            {'font_size': 11, 'align': 'vcenter', 'bg_color': '#f7fcff', 'bold': False, 'num_format': '#,##0.00'})
        format4 = workbook.add_format({'font_size': 12, 'align': 'vcenter', 'bold': True})
        format5 = workbook.add_format({'font_size': 12, 'align': 'vcenter', 'bold': False})
        sheet = workbook.add_worksheet('Job')

        sheet.write(2, 0, 'No', format1)
        sheet.write(2, 1, 'Job Acquisition Approved Date', format1)
        sheet.write(2, 2, 'Month:Year', format1)
        sheet.write(2, 3, 'SBUs', format1)
        sheet.write(2, 4, 'Job Position', format1)
        sheet.write(2, 5, 'Department', format1)
        sheet.write(2, 6, 'Branch/Project', format1)
        sheet.write(2, 7, 'Location', format1)
        sheet.write(2, 8, 'Job Level', format1)
        sheet.write(2, 9, 'Type Of Recruitment', format1)
        sheet.write(2, 10, 'Number of Applicants', format1)
        stage_env = self.env['hr.recruitment.stage']
        stages= stage_env.search([])
        col = 11
        for stage in stages:
            sheet.write(2,col, stage.name , format1)
            col+=1

        col_names = ['Offer Acceptance Date','No of Offer Rejected Person (If have)','Source of Hired','Recruitment External Cost',
                     'Recruitment Internal Cost','Total Recruitment Cost','Hired Employee Name','Gender','Join Date','Attrition Date within 3 months or 1 years',
                     'Remark','Time to Hire (Days)','Time to Fill (Days)','Time to fill alert','Type of Attrition','Female Count','Male Count',
                     'Close Position','New Requirement Count','Replacement Count','Within 45 days count','Over 45 days count','No of Offer accepted Person',
                     'Total No of Offered Person','Level of Management','Time to Hire for Above Senior Management','Time to fill for Above Senior Management',
                     'Time to Hire for Below Senior Management','Time to fill for Below Senior Management','Attrition Month Calculation',
                     '']

        for name in col_names:
            sheet.write(2, col, name, format1)
            col+=1
        data_row = 3
        srno = 1
        for job in job_ids:
            sheet.write(data_row, 0, srno, format5)
            sheet.write(data_row, 1, job.x_studio_job_acquisition_approved_date, format5) #Job Acquisition Approved Date
            sheet.write(data_row, 2, job.x_studio_job_acquisition_approved_date, format5) #Month:Year
            sheet.write(data_row, 3, job.x_studio_sbu or '', format5) #SBUs
            sheet.write(data_row, 4, job.name, format5) #Job Position
            sheet.write(data_row, 5, job.department_id.name or '', format5) #Department
            sheet.write(data_row, 6, job.x_studio_branchproject or '', format5)  #Branch/Project
            sheet.write(data_row, 7, job.x_studio_location or '', format5)  #Location
            sheet.write(data_row, 8, job.x_studio_job_level or '', format5)  # Job Level
            sheet.write(data_row, 9, job.x_studio_type_of_recruitment or '', format5)  # Type Of Recruitment
            sheet.write(data_row, 10, job.application_count, format5)  # Number of Applicants

            data_col = 11
            for stage in stages:
                print(stage.sequence)
                if stage.name in 'Reject':
                    domain = [('sequence', '=', stage.sequence)]
                else:
                    domain = [('sequence','>=',stage.sequence)]

                stage_ids=stage_env.search(domain)
                applicant_count = len(self.env['hr.applicant'].search(
                    [('job_id', '=', job.id), ('stage_id', 'in', stage_ids.ids )]))
                sheet.write(data_row, data_col, applicant_count, format5)
                data_col+=1

            sheet.write(data_row, data_col, job.x_studio_offer_acceptance_date, format5)  # Offer Acceptance Date
            sheet.write(data_row, data_col+1, 1 if job.x_studio_offer_rejected else 0, format5)  # No of Offer Rejected Person (If have)
            sheet.write(data_row, data_col+2, job.x_studio_hired_applicant.source_id.name or '', format5)  # Source of Hired
            sheet.write(data_row, data_col+3, job.x_studio_recruitment_external_cost or '', format5)  # Recruitment External Cost
            sheet.write(data_row, data_col+4, job.x_studio_recruitment_internal_cost or '', format5)  # Recruitment Internal Cost
            sheet.write(data_row, data_col+5, job.x_studio_total_recruitment_cost or '', format5)  # Recruitment Total Cost
            sheet.write(data_row, data_col+6, job.x_studio_hired_applicant.name or '', format5)  # Hired Applicant Name
            sheet.write(data_row, data_col+7, job.x_studio_hired_applicant.x_studio_gender, format5)  # Hired Applicant Name
            sheet.write(data_row, data_col+8, job.x_studio_hired_applicant.x_studio_join_date, format5)  # Join Date
            # sheet.write(data_row, data_col+9, job.x_studio_hired_applicant.attrition_date_within_3_months_or_1_years, format5)  # attrition_date_within_3_months_or_1_years
            sheet.write(data_row, data_col+10, job.x_studio_remark, format5)  # Remark
            sheet.write(data_row, data_col+11, job.x_studio_time_to_hire_days, format5)  # Time to Hire (Days)
            sheet.write(data_row, data_col+12, job.x_studio_time_to_fill_days, format5)  # Time to Fill (Days)
            sheet.write(data_row, data_col+13, job.x_studio_time_to_fill_alert, format5)  # Time to Fill ALert (Days)
            sheet.write(data_row, data_col+14, job.x_studio_type_of_attrition, format5)  # Type of Attrition'
            sheet.write(data_row, data_col+15, 1 if job.x_studio_hired_applicant.x_studio_gender == 'Female' else 0, format5)  # Female Count
            sheet.write(data_row, data_col+16, 1 if job.x_studio_hired_applicant.x_studio_gender=='Male' else 0, format5)  # Female Count
            sheet.write(data_row, data_col+17, job.x_studio_remark, format5)  # Close Position
            sheet.write(data_row, data_col+18, 0 if job.x_studio_type_of_recruitment=='Replacement' else 1, format5)  # New Requirement Count
            sheet.write(data_row, data_col+19, 1 if job.x_studio_type_of_recruitment=='Replacement' else 0, format5)  # Replacement Count
            sheet.write(data_row, data_col+10, '', format5)  # Within 45 days count
            sheet.write(data_row, data_col + 11, '', format5)  # Over 45 days count
            sheet.write(data_row, data_col + 12, '', format5)  # No of Offer accepted Person
            sheet.write(data_row, data_col + 13, '', format5)  # Total No of Offered Person
            sheet.write(data_row, data_col + 14, '', format5)  # Level of Management
            sheet.write(data_row, data_col + 15, '', format5)  # Time to Hire for Above Senior Management
            sheet.write(data_row, data_col + 16, '', format5)  # Time to fill for Above Senior Management
            sheet.write(data_row, data_col + 17, '',
                        format5)  # Time to Hire for Below Senior Management
            sheet.write(data_row, data_col + 18, '',
                        format5)  # Time to fill for Below Senior Management
            sheet.write(data_row, data_col + 19, '',
                        format5)  # Attrition Month Calculation
            data_row +=1
            srno+=1



















