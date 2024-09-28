import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum

def get_project_activity_types_query(project, condition):
    LOBActivityType = DocType("LOB Activity Type")
    LineOfBusiness = DocType("Line of Business")
    Project = DocType("Project")
    
    query = (
        frappe.qb.from_(LOBActivityType)
        .inner_join(LineOfBusiness)
        .on(LOBActivityType.parent == LineOfBusiness.name)
        .inner_join(Project)
        .on(LineOfBusiness.name == Project.lob)
        .select(LOBActivityType.activity_type.as_("name"))
        .where(Project.name == project)
    )
    if condition:
        query = query.where(condition)
    return query.run()


def get_filtered_users_query(condition):
    User = DocType("User")
    HasRole = DocType("Has Role")

    query = (
        frappe.qb.from_(User)
        .inner_join(HasRole)
        .on(HasRole.parent == User.name)
        .select(User.name, User.full_name.as_("description"))
        .where(HasRole.role == 'Projects Manager')
        .where(User.name != 'Administrator')
    )
    if condition:
        query = query.where(condition)
    return query.run()

def fetch_projects_query(condition):
    Project = DocType("Project")
    TimesheetDetail = DocType("Timesheet Detail")
    Timesheet = DocType("Timesheet")
    Employee = DocType("Employee")
    
    query = (
        frappe.qb.from_(Project)
        .inner_join(TimesheetDetail)
        .on(TimesheetDetail.project == Project.name)
        .inner_join(Timesheet)
        .on(Timesheet.name == TimesheetDetail.parent)
        .inner_join(Employee)
        .on(Employee.name == Timesheet.employee)
        .select(Project.name, Project.project_name)
        .where(Project.status == "Open")
        .groupby(Project.name)
    )
    if condition:
        query = query.where(condition)
    return query.run()

def get_employee_query(condition):
    Timesheet = DocType("Timesheet")
    TimesheetDetail = DocType("Timesheet Detail")
    Employee = DocType("Employee")
    Project = DocType("Project")
    
    query = (
        frappe.qb.from_(Timesheet)
        .inner_join(TimesheetDetail)
        .on(TimesheetDetail.parent == Timesheet.name)
        .inner_join(Employee)
        .on(Employee.name == Timesheet.employee)
        .inner_join(Project)
        .on(Project.name == TimesheetDetail.project)
        .select(Timesheet.employee, Employee.employee_name)
        .where(Timesheet.employee.isnotnull())
        .groupby(Timesheet.employee)
    )
    if condition:
        query = query.where(condition)
    return query.run()

def get_data_query(conditions):

	Timesheet = DocType("Timesheet")
	TimesheetDetail = DocType("Timesheet Detail")
	Employee = DocType("Employee")
	Project = DocType("Project")

	frappe.log_error(title="condition",message=conditions)
	if conditions:
		query = (
			frappe.qb.from_(Timesheet)
			.inner_join(TimesheetDetail).on(TimesheetDetail.parent == Timesheet.name)
			.inner_join(Employee).on(Employee.name == Timesheet.employee)
			.inner_join(Project).on(Project.name == TimesheetDetail.project)
			.select(
				Timesheet.employee_name,
				TimesheetDetail.project,
				TimesheetDetail.customer,
				TimesheetDetail.activity_type,
				TimesheetDetail.description,
				TimesheetDetail.hours,
				Timesheet.log_date,
				TimesheetDetail.name,
				TimesheetDetail.approval_status
			)
			.where(
				(Timesheet.employee.isnotnull()) &
				(Timesheet.docstatus == 0) &
				(Timesheet.sent_for_approval == 1) &
				(~TimesheetDetail.approval_status.isin(["Employee Pending", "Approved"]))
			)
			.where(conditions)
			.orderby(
				Timesheet.employee_name,
				TimesheetDetail.project,
				TimesheetDetail.customer,
				TimesheetDetail.activity_type,
				Timesheet.log_date
			)
		)
		frappe.log_error(conditions)
		return query.run()
	else:
		return []

def get_sales_order_billing_methods(so_id):
    SalesOrderItem = frappe.qb.DocType("Sales Order Item")
    SalesOrderBillingMethod = frappe.qb.DocType("Sales Order Billing Method")

    query = (
        frappe.qb.from_(SalesOrderItem)
        .left_join(SalesOrderBillingMethod)
        .on(SalesOrderItem.name == SalesOrderBillingMethod.item_id)
        .select(
            SalesOrderItem.parent.as_("so_id"),
            SalesOrderItem.name.as_("so_item_id"),
            SalesOrderItem.amount.as_("so_amount"),
            Sum(SalesOrderBillingMethod.billing_amt).as_("billing_amount")
        )
        .where(
            (SalesOrderItem.parent == so_id)
            & (SalesOrderItem.revenue_method.isin([
                "Equal revenue over the contract period", 
                "100% revenue on delivery", 
                "irrespective of billing time", 
                "POC"
            ]))
        )
        .groupby(SalesOrderItem.name)
    )
    return query.run(as_dict=True)


def get_employee():
    Employee = DocType("Employee")

    query = (
        frappe.qb.from_(Employee)
        .select(
            Employee.name,
            Employee.prefered_email,
            Employee.prefered_contact_email,
            Employee.personal_email,
            Employee.company_email
        )
        .where(
            (Employee.prefered_contact_email.isnotnull()) &
            ((Employee.user_id.isnull()) | (Employee.user_id == ''))
        )
        .limit(50)
    )
    frappe.log_error(1)
    return query.run(as_dict=True)

def get_recognised_revenue(doc_name, row_name):
    item_query = f"""
            SELECT COALESCE(SUM(CASE
                WHEN jea.so_currency='INR' AND jea.credit>0 THEN jea.credit
                WHEN jea.so_currency='INR' AND jea.debit>0 THEN -jea.debit
                WHEN jea.so_currency<>'INR' AND jea.debit>0 THEN -(jea.debit/jea.so_exchange_rate)
                WHEN jea.so_currency<>'INR' AND jea.credit>0 THEN (jea.credit/jea.so_exchange_rate)
                ELSE 0 END), 0) AS bc_recognised_revenue
            FROM `tabJournal Entry Account` jea
            INNER JOIN `tabJournal Entry` je ON je.name = jea.parent
            WHERE sales_order = '{doc_name}' AND sales_order_item = '{row_name}'
            AND je.docstatus = 1 AND (jea.credit>0 OR jea.debit>0)
            AND jea.account IN(SELECT name FROM `tabAccount` WHERE parent_account='Revenue From Operations - IBSL')
        """
    total_jv = frappe.db.sql(item_query, as_dict=True)
    return total_jv

def order_items_query():
    SalesOrderItem = frappe.qb.DocType('Sales Order Item')
    SalesInvoiceItem = frappe.qb.DocType('Sales Invoice Item')

    return (
        frappe.qb.from_(SalesOrderItem)
        .inner_join(SalesInvoiceItem)
        .on(
            (SalesInvoiceItem.sales_order == SalesOrderItem.parent) &
            (SalesInvoiceItem.so_detail == SalesOrderItem.name)
        )
        .select(
            SalesInvoiceItem.sales_order.as_("sales_invoice_ref"),
            SalesInvoiceItem.parent.as_("sales_invoice"),
            SalesOrderItem.mandate.as_("so_mandate"),
            SalesInvoiceItem.mandate.as_("si_mandate"),
            SalesInvoiceItem.project.as_("si_project"),
            SalesOrderItem.project.as_("so_project"),
            SalesInvoiceItem.name.as_("si_id"),
            SalesOrderItem.cost_center
        )
        .orderby(SalesInvoiceItem.sales_order)
        .run(as_dict=True)
    )

def order_item():
    SalesOrderItem = frappe.qb.DocType('Sales Order Item')
    SalesOrder = frappe.qb.DocType('Sales Order')
    CommonProjectMapper = frappe.qb.DocType('Common Project Mapper')

    return (
        frappe.qb.from_(SalesOrderItem)
        .inner_join(SalesOrder)
        .on(SalesOrder.name == SalesOrderItem.parent)
        .inner_join(CommonProjectMapper)
        .on(
            (CommonProjectMapper.sales_order == SalesOrderItem.parent) &
            (CommonProjectMapper.sales_order_item == SalesOrderItem.name)
        )
        .select(
            CommonProjectMapper.sales_order.as_("cpm_ref"),
            CommonProjectMapper.name.as_("cpm_id"),
            CommonProjectMapper.sales_order_status.as_("cpm_so_status"),
            SalesOrder.status.as_("so_status")
        )
        .orderby(CommonProjectMapper.sales_order)
        .run(as_dict=True)
    )

def get_count(name,doctype):
    linked_doctype = 'Sales Order' if doctype == 'Purchase Order' else 'Purchase Order'
    linked_field = 'sales' if doctype != 'Purchase Order' else 'purchase'
    
    o = DocType(linked_doctype)
    oi = DocType(f"{linked_doctype} Item")
    
    count = (
        frappe.qb
        .from_(o)
        .left_join(oi)
        .on(o.name == oi.parent)
        .where(o.docstatus < 2)
        .where(oi[f"linked_{linked_field}_order"].like(f"%{name}%"))
        .groupby(o.name)
        .select(o.name)
    ).run()
    
    return count

def get_invoice_sum_of_so(so_name):
    SalesInvoice = DocType('Sales Invoice')
    SalesInvoiceItem = DocType('Sales Invoice Item')
    
    query = (
        frappe.qb.from_(SalesInvoice)
        .join(SalesInvoiceItem).on(SalesInvoice.name == SalesInvoiceItem.parent)
        .where(SalesInvoiceItem.sales_order == so_name)
        .select(Sum(SalesInvoice.grand_total).as_('total'))
    ).run(as_dict=True)
    
    return query[0]['total'] if query and query[0]['total'] else 0

def get_revenue_recognized_sum(doc_name):
    JournalEntry = DocType('Journal Entry')
    
    query = (
        frappe.qb.from_(JournalEntry)
        .where(JournalEntry.sales_order == doc_name)
        .select(Sum(JournalEntry.total_credit).as_('total'))
    ).run(as_dict=True)
    
    return query[0]['total'] if query and query[0]['total'] else 0

def get_billing_hours(project, f_date, t_date):
    TimesheetDetail = DocType("Timesheet Detail")
    
    query = (
        frappe.qb.from_(TimesheetDetail)
        .select(Sum(TimesheetDetail.hours).as_("hours"))
        .where(
            (TimesheetDetail.project == project) &
            (TimesheetDetail.approval_status == 'Approved') &
            (TimesheetDetail.docstatus == 1) &
            (TimesheetDetail.to_time.between(f_date, t_date))
        )
        .groupby(TimesheetDetail.project)
    )
    result = query.run(as_dict=True)
    return result


def subscription_revenue_engine_query(period_list):
    query = """	
            SELECT
                so.name AS doc,
                so.transaction_date AS posting_date,
                soi.name AS item,
                soi.item_name,
                COALESCE(soi.actual_start_date, soi.start_date) AS service_start_date,
                soi.end_date AS service_end_date,
                soi.base_net_amount,
                aoa.credit_account AS deferred_revenue_account,
                je.posting_date AS gle_posting_date,
                COALESCE(
                    SUM(jea.debit), 0) AS debit,
                0 AS credit,
                'posted'
            FROM
                `tabSales Order` so
            JOIN
                `tabSales Order Item` soi ON so.name = soi.parent
            JOIN
                `tabAssociated Offering Account` aoa ON soi.offering = aoa.parent
            JOIN
                `tabJournal Entry` je ON soi.name = je.sales_order_item AND je.sales_order = so.name
            JOIN
                `tabJournal Entry Account` jea ON jea.parent = je.name
            WHERE
                so.docstatus = 1
                AND (
                    CASE
                        WHEN soi.revenue_method = 'Equal revenue over the contract period' THEN 1
                        ELSE 0
                    END
                )
                AND (
                    ('{0}' >= COALESCE(soi.actual_start_date, soi.start_date) AND COALESCE(soi.actual_start_date, soi.start_date) >= '{1}')
                    OR (COALESCE(soi.actual_start_date, soi.start_date) >= '{0}' AND COALESCE(soi.actual_start_date, soi.start_date) <= '{2}')
                )
            GROUP BY
                so.name,
                soi.name,
                je.posting_date
            ORDER BY
                je.posting_date""".format(period_list[0].from_date,period_list[0].from_date, period_list[-1].to_date )

    return query

# query.py

def get_account_data(company):
    accounts = frappe.db.sql(
        """
        select
            name, account_number, parent_account, lft, rgt, root_type,
            report_type, account_name, include_in_gross, account_type, is_group
        from
            `tabAccount`
        where
            company=%s
            AND root_type IN ('Expense','Income')
            order by lft""",
        (company),
        as_dict=True,
    )
    return accounts

def get_min_max_lft_rgt(company):
    return frappe.db.sql(
        """select min(lft), max(rgt) from `tabAccount`
        where company=%s AND root_type IN ('Expense','Income')""",
        (company),
    )[0]

def get_account_names(min_lft, max_rgt, company):
    return frappe.db.sql_list(
        """select name from `tabAccount`
        where lft >= %s and rgt <= %s and company = %s AND root_type IN ('Expense','Income')""",
        (min_lft, max_rgt, company),
    )

def get_gl_entries_by_account(dimension, condition, gl_filters,finance_book):
    return frappe.db.sql(
            """
            select
                posting_date, account, {dimension}, debit, credit, is_opening, fiscal_year,
                debit_in_account_currency, credit_in_account_currency, account_currency
            from
                `tabGL Entry`
            where
                company=%(company)s
            {condition}
            and posting_date >= %(from_date)s
            and posting_date <= %(to_date)s
            and is_cancelled = 0
            {finance_book}
            order by account, posting_date""".format(
                dimension=dimension, condition=condition,
                finance_book = finance_book
            ),
            gl_filters,
            as_dict=True,
        ) 

def get_cost_centers(company):
    # cost_center = DocType("Cost Center")
    # cost_centers = (
    #     frappe.qb.from_(cost_center)
    #     .select(cost_center.name)
    #     .where(cost_center.company == company)
    #     .orderby(cost_center.name)
    # ).run(as_dict=True)
    # frappe.log_error("cost_centers",cost_centers)
    # return cost_centers
    return frappe.db.sql(
        """select name, parent_cost_center as parent_account, cost_center_name as account_name, lft, rgt
        from `tabCost Center` where company=%s order by name""",
        company,
        as_dict=True,
    )
def get_mandates(company):
    return frappe.db.sql(
        """select name from `tabMandate` where company=%s order by name""",
        company,
        as_dict=True,
    )


def fetch_gl_entries(company, from_date, to_date, based_on, additional_conditions):
    query = """
        select posting_date, {based_on} as based_on, debit, credit,
        is_opening, (select root_type from `tabAccount` where name = account) as type
        from `tabGL Entry` where company=%(company)s
        {additional_conditions}
        and posting_date <= %(to_date)s
        and {based_on} is not null
        and is_cancelled = 0
        order by {based_on}, posting_date
    """.format(
        additional_conditions="\n".join(additional_conditions), based_on=based_on
    )

    return frappe.db.sql(query, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)


def recognised_revenue_report(condition,date):
    datas =  frappe.db.sql("""
			SELECT
			soi.parent,
			soi.transaction_date,
			soi.mandate,
			so.status,
			soi.name as so_item,
			soi.item_code,
			soi.offering,
			soi.revenue_method,
			soi.start_date,
			soi.end_date,
			soi.cost_center,
			soi.project,
			(SELECT project_manager FROM `tabProject` WHERE name = soi.project) AS project_manager,
			so.currency,
			soi.net_amount,
			so.customer,
			soi.end_customer,
			so.conversion_rate,
			CAST(nvl(soi.custom_billed_amount,0) AS DECIMAL(10,2)) AS billed_till_march,
						
			CAST(
			COALESCE(
				(
					SELECT SUM(sii.amount)
					FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 0
				), 0
			)  AS DECIMAL(10,2))
			AS billed_from_april,
						
			( ((SELECT 
					SUM(billing) 
				FROM `tabSales Order Billing Method` 
				WHERE item_id = soi.name AND parent = so.name AND docstatus = 1 AND is_billed = 1 )/100) * soi.net_amount)
			AS base_currency_billed,
						
		    -
			COALESCE(
				(
					SELECT ABS(SUM(sii.amount) )
					FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					WHERE  si.posting_date <= '{date}' AND sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
				), 0
			)
			 AS base_currency_curent_credit_value,
						
			-
			COALESCE(
							(
								SELECT ABS(SUM(sii.base_amount) )
								FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
								WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
							), 0
						) AS base_currency_curent_credit_value_inr,
			COALESCE(
					(
					SELECT
						SUM(CASE WHEN je.custom_currency='INR' AND jea.credit>0 THEN
								jea.credit
							WHEN je.custom_currency='INR' AND jea.debit>0 THEN
								-jea.debit
							WHEN je.custom_currency<>'INR' AND jea.debit>0 THEN
								-je.custom_debit_rate
							WHEN je.custom_currency<>'INR' AND jea.credit>0 THEN
								je.custom_debit_rate
							ELSE 0 
						END ) AS journal_entry_value
					FROM
						`tabJournal Entry` je
					LEFT JOIN
						`tabJournal Entry Account` jea
					ON
						je.name = jea.parent
					WHERE
						sales_order = so.name
						AND sales_order_item = soi.name
						AND je.docstatus = 1
						AND je.is_from_report = 0
						AND je.posting_date <= '{date}' 
						AND (jea.credit>0 OR jea.debit>0)
						AND jea.account IN(SELECT name FROM `tabAccount` WHERE parent_account='Revenue From Operations - IBSL')
					),
					0
				) AS journal_entry_value,
						
			COALESCE(
					(
					SELECT
						SUM(CASE WHEN je.custom_currency='INR' AND jea.credit>0 THEN
								jea.credit
							WHEN je.custom_currency='INR' AND jea.debit>0 THEN
								-jea.debit
							WHEN je.custom_currency<>'INR' AND jea.credit>0 THEN
								jea.credit
							WHEN je.custom_currency<>'INR' AND jea.debit>0 THEN
								-jea.debit
							ELSE 0 
						END) AS journal_entry_value
					FROM
						`tabJournal Entry` je
					LEFT JOIN
						`tabJournal Entry Account` jea
					ON
						je.name = jea.parent
					WHERE
						sales_order = so.name
						AND sales_order_item = soi.name
						AND je.docstatus = 1
						AND je.is_from_report = 0
						AND je.posting_date <= '{date}' 
						AND (jea.credit>0 OR jea.debit>0)
						AND jea.account IN(SELECT name FROM `tabAccount` WHERE parent_account='Revenue From Operations - IBSL')
					),
					0
				) AS journal_entry_value_inr,
						
			CASE WHEN soi.revenue_method = 'Units rate' THEN CAST(nvl(soi.custom_billed_amount,0) AS DECIMAL(10,2))
    		 WHEN soi.revenue_method = 'Hours rate' THEN CAST(nvl(soi.custom_billed_amount,0) AS DECIMAL(10,2))
			ELSE soi.revenue_recognised_amount
			END AS recognised_revenue_till_march,
						
			CASE WHEN soi.revenue_method = 'Units rate' THEN 
            		CAST(COALESCE( ( SELECT SUM(sii.amount) FROM `tabSales Invoice`si 
                             LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					         WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name 
					         AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 0	), 0)  AS DECIMAL(10,2))
			                 -
					ABS(CAST(COALESCE( ( SELECT SUM(sii.amount) FROM `tabSales Invoice`si 
                             LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					         WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name 
					         AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1	), 0)  AS DECIMAL(10,2)))
        	WHEN soi.revenue_method = 'Hours rate' THEN 
            		CAST(COALESCE(	( SELECT SUM(sii.amount) FROM `tabSales Invoice`si 
                              LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					          WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name 
					          AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 0), 0)  AS DECIMAL(10,2))
					          -
					ABS(CAST(COALESCE(	( SELECT SUM(sii.amount) FROM `tabSales Invoice`si 
                              LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					          WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name 
					          AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1), 0)  AS DECIMAL(10,2)))
			ELSE COALESCE((SELECT SUM(debit_in_account_currency / so_exchange_rate)	FROM `tabJournal Entry Account` jea LEFT JOIN `tabJournal Entry` je 
			ON je.name = jea.parent	WHERE je.docstatus = 1 AND sales_order = so.name AND je.is_from_report = 1 
			AND sales_order_item = soi.name and je.posting_date <= '{date}'), 0) END AS recognised_revenue_from_april,
			
			soi.base_net_amount AS net_amount_c,
						
			0 as inr_forex,
						
			(nvl(soi.custom_billed_amount,0) * nvl(so.conversion_rate,0) ) 
			AS billed_till_march_inr,
						
			COALESCE(
				(
					SELECT SUM(sii.base_amount)
					FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 0
				), 0
			)
			AS billed_from_april_inr,
						
			( ((SELECT 
					SUM(billing) 
				FROM `tabSales Order Billing Method` sobm
				inner join `tabSales Invoice Item` sii on sobm.item_id = sii.so_detail
				WHERE sobm.item_id = soi.name AND sobm.parent = so.name AND sii.docstatus = 1 AND sobm.is_billed = 1 )/100) * soi.base_net_amount)
			AS billed_inr,
						
			CASE WHEN soi.revenue_method = 'Units rate' THEN (nvl(soi.custom_billed_amount,0) * nvl(so.conversion_rate,0) ) 
			WHEN soi.revenue_method = 'Hours rate' THEN (nvl(soi.custom_billed_amount,0) * nvl(so.conversion_rate,0) ) 
			ELSE (soi.revenue_recognised_amount * so.conversion_rate )
			END AS recognised_revenue_till_march_inr,
			
			
			CASE WHEN soi.revenue_method = 'Units rate' THEN 
            		CAST(COALESCE( ( SELECT SUM(sii.base_amount) FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					    WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 0	), 0)  AS DECIMAL(10,2))
			            -
					ABS(CAST(COALESCE( ( SELECT SUM(sii.base_amount) FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
						WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name 
						AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1	), 0)  AS DECIMAL(10,2)))
        	WHEN soi.revenue_method = 'Hours rate' THEN 
            		CAST(COALESCE(	( SELECT SUM(sii.base_amount) FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					    WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 0), 0)  AS DECIMAL(10,2))
					    -
					ABS(CAST(COALESCE(	( SELECT SUM(sii.base_amount) FROM `tabSales Invoice`si 
						LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
						WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name 
						AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1), 0)  AS DECIMAL(10,2)))
			ELSE COALESCE((SELECT SUM(debit_in_account_currency)
	FROM `tabJournal Entry Account` jea LEFT JOIN `tabJournal Entry` je ON je.name = jea.parent
	WHERE je.docstatus = 1 AND sales_order = so.name AND je.is_from_report = 1 
	AND sales_order_item = soi.name and je.posting_date <= '{date}'), 0)
	END AS recognised_revenue_from_april_inr
						
		FROM
			`tabSales Order` so,
			`tabSales Order Item` soi
		WHERE
			so.docstatus = 1 
			AND soi.parent = so.name 
			AND so.creation >= '2024-04-01' {condition}
		""".format(condition=condition,date=date), as_dict=True)
    return datas



# def revenue_recognition_engine_query(condition=None,date=None):
#     datas =  frappe.db.sql("""
# 			SELECT
# 				so.name AS sales_order,
# 			 	so.company,
# 				so.transaction_date,
# 				soi.item_code,
# 				soi.name as so_item,
# 				soi.mandate,
# 				soi.offering,
# 				soi.revenue_method,
# 				soi.start_date,
# 				soi.end_date,
# 				soi.cost_center,
# 				soi.project,
# 			 	so.customer,
# 				soi.end_customer,
# 				so.currency as so_currency,
# 				soi.net_amount,
# 				(SELECT project_manager FROM `tabProject` WHERE name = soi.project) AS project_manager,
# 				soi.base_net_amount,
# 			 	soi.revenue_recognised_amount,
# 			 	so.conversion_rate,
# 				COALESCE(
# 					(
# 					SELECT
# 						SUM(jea.debit_in_account_currency/ jea.so_exchange_rate)
# 					FROM
# 						`tabJournal Entry` je
# 					LEFT JOIN
# 						`tabJournal Entry Account` jea
# 					ON
# 						je.name = jea.parent
# 					WHERE
# 						sales_order = so.name
# 						AND sales_order_item = soi.name
# 						AND je.docstatus = 1
# 					),
# 					0
# 				) AS journal_entry_value,
# 				CASE
# 					WHEN
# 						(
# 							COALESCE(
# 								(
# 									SELECT ABS(SUM(sii.amount) )
# 									FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
# 									WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
# 								), 0
# 							)
# 							-
# 							COALESCE(
# 								(
# 									SELECT ABS(SUM(sii.amount))
# 									FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
# 									WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1
# 								), 0
# 							)
# 			 			) < 0
# 			 		THEN
# 			 			0
# 			 		ELSE
# 			 			(
# 							COALESCE(
# 								(
# 									SELECT ABS(SUM(sii.amount))
# 									FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
# 									WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
# 								), 0
# 							)
# 							-
# 							COALESCE(
# 								(
# 									SELECT ABS(SUM(sii.amount))
# 									FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
# 									WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1
# 								), 0
# 							)
# 			 			)
# 			 	END AS credit_note_value,
# 				-- COALESCE(
# 				-- 	(
# 				-- 	SELECT
# 				-- 		SUM(jea.debit_in_account_currency/ jea.so_exchange_rate)
# 				-- 	FROM
# 				-- 		`tabJournal Entry` je
# 				-- 	LEFT JOIN
# 				-- 		`tabJournal Entry Account` jea
# 				-- 	ON
# 				-- 		je.name = jea.parent
# 				-- 	WHERE
# 				-- 		sales_order = so.name
# 				-- 		AND sales_order_item = soi.name
# 				-- 		AND je.docstatus = 1
# 				-- 	),
# 				-- 	0
# 				-- ) + (soi.revenue_recognised_amount) AS bc_recognised_revenue,
# 				COALESCE(
# 					(
# 					SELECT
# 						SUM(CASE WHEN jea.so_currency='INR' AND jea.credit>0 THEN
# 								jea.credit
# 							WHEN jea.so_currency='INR' AND jea.debit>0 THEN
# 								-jea.debit
# 							WHEN jea.so_currency<>'INR' AND jea.debit>0 THEN
# 								-(jea.debit/jea.so_exchange_rate)
# 							WHEN jea.so_currency<>'INR' AND jea.credit>0 THEN
# 								(jea.credit/jea.so_exchange_rate)
# 							ELSE 0 
# 						END ) AS journal_entry_value
# 					FROM
# 						`tabJournal Entry Account` jea

# 					INNER JOIN
# 						`tabJournal Entry` je

# 					ON
# 						je.name = jea.parent
# 					WHERE
# 						sales_order = so.name
# 						AND sales_order_item = soi.name
# 						AND je.docstatus = 1
# 						AND (jea.credit>0 OR jea.debit>0)
# 						AND jea.account IN(SELECT name FROM `tabAccount` WHERE parent_account='Revenue From Operations - IBSL')
# 					),
# 					0
# 				) + (soi.revenue_recognised_amount) AS bc_recognised_revenue,
# 				CASE
# 					WHEN
# 						(soi.net_amount -(
# 						COALESCE(
# 							(
# 							SELECT
# 								SUM(jea.debit_in_account_currency / jea.so_exchange_rate)
# 							FROM
# 								`tabJournal Entry` je
# 							LEFT JOIN `tabJournal Entry Account` jea
# 							ON je.name = jea.parent
# 							WHERE
# 								sales_order = so.name
# 								AND sales_order_item = soi.name
# 								AND je.docstatus = 1
# 							),
# 							0
# 						) + (soi.revenue_recognised_amount))) > 0
# 					THEN
# 						soi.net_amount -(
# 						COALESCE(
# 							(
# 							SELECT
# 								SUM(jea.debit_in_account_currency / jea.so_exchange_rate)
# 							FROM
# 								`tabJournal Entry` je
# 							LEFT JOIN `tabJournal Entry Account` jea
# 							ON je.name = jea.parent
# 							WHERE
# 								sales_order = so.name
# 								AND sales_order_item = soi.name
# 								AND je.docstatus = 1
# 							),
# 							0
# 						) + (soi.revenue_recognised_amount))
# 					ELSE 0
# 				END AS bc_unrecognised_revenue,
# 				-- COALESCE(
# 				-- 	(
# 				-- 	SELECT
# 				-- 		SUM(jea.debit_in_account_currency)
# 				-- 	FROM
# 				-- 		`tabJournal Entry` je
# 				-- 	LEFT JOIN
# 				-- 		`tabJournal Entry Account` jea
# 				-- 	ON
# 				-- 		je.name = jea.parent
# 				-- 	WHERE
# 				-- 		sales_order = so.name
# 				-- 		AND sales_order_item = soi.name
# 				-- 		AND je.docstatus = 1
# 				-- 	),
# 				-- 	0
# 				-- ) + (soi.revenue_recognised_amount * so.conversion_rate) AS recognised_revenue,
# 				COALESCE(
# 					(
# 					SELECT
# 						SUM(CASE WHEN jea.so_currency='INR' AND jea.credit>0 THEN
# 								jea.credit
# 							WHEN jea.so_currency='INR' AND jea.debit>0 THEN
# 								-jea.debit
# 							WHEN jea.so_currency<>'INR' AND jea.credit>0 THEN
# 								jea.credit
# 							WHEN jea.so_currency<>'INR' AND jea.debit>0 THEN
# 								-jea.debit
# 							ELSE 0 
# 						END) AS journal_entry_value
# 					FROM
# 						`tabJournal Entry Account` jea
# 					INNER JOIN
# 						`tabJournal Entry` je
						
# 					ON
# 						je.name = jea.parent
# 					WHERE
# 						sales_order = so.name
# 						AND sales_order_item = soi.name
# 						AND je.docstatus = 1
# 						AND (jea.credit>0 OR jea.debit>0)
# 						AND jea.account IN(SELECT name FROM `tabAccount` WHERE parent_account='Revenue From Operations - IBSL')
# 					),
# 					0
# 				)  + (soi.revenue_recognised_amount * so.conversion_rate) AS recognised_revenue,
# 				CASE
# 					WHEN
# 						(soi.base_net_amount -(
# 						COALESCE(
# 							(
# 							SELECT
# 								SUM(jea.debit_in_account_currency)
# 							FROM
# 								`tabJournal Entry` je  
# 							LEFT JOIN `tabJournal Entry Account` jea 
# 							ON je.name = jea.parent
# 							WHERE
# 								sales_order = so.name
# 								AND sales_order_item = soi.name
# 								AND je.docstatus = 1
# 							),
# 							0
# 						) + (soi.revenue_recognised_amount * so.conversion_rate))) > 0
# 					THEN 
# 						soi.base_net_amount -(
# 						COALESCE(
# 							(
# 							SELECT
# 								SUM(jea.debit_in_account_currency)
# 							FROM
# 								`tabJournal Entry` je  
# 							LEFT JOIN `tabJournal Entry Account` jea 
# 							ON je.name = jea.parent
# 							WHERE
# 								sales_order = so.name
# 								AND sales_order_item = soi.name
# 								AND je.docstatus = 1
# 							),
# 							0
# 						) + (soi.revenue_recognised_amount * so.conversion_rate))
# 					ELSE 0 
# 				END AS unrecognised_revenue,
# 				(
# 					SELECT
# 						estimated_costing
# 					FROM
# 						`tabProject`
# 					WHERE
# 						name = soi.project
# 				) AS budget_cost,
# 				(
# 					SELECT
# 						total_employee_cost + total_purchase_cost
# 					FROM
# 						`tabProject`
# 					WHERE
# 						name = soi.project
# 				) AS actual_cost,
# 				CASE
# 					WHEN (
# 						SELECT
# 							ROUND(((total_employee_cost + total_purchase_cost) / estimated_costing) * 100)
# 						FROM
# 							`tabProject`
# 						WHERE
# 							name = soi.project
# 						) > 100 THEN 100
# 					ELSE (
# 						SELECT
# 							ROUND(((total_employee_cost + total_purchase_cost) / estimated_costing) * 100)
# 						FROM
# 							`tabProject`
# 						WHERE
# 							name = soi.project
# 						)
# 				END AS per_complete,
# 				(
# 					SELECT je.posting_date
# 					FROM `tabJournal Entry` as je
# 					WHERE sales_order= so.name AND sales_order_item = soi.name AND je.docstatus = 1
# 					ORDER BY posting_date DESC
# 					LIMIT 1
# 				) as recognised_until,
# 				(
# 					SELECT je.posting_date
# 					FROM `tabJournal Entry` as je
# 					WHERE sales_order= so.name AND sales_order_item = soi.name AND je.docstatus = 1
# 					ORDER BY je.posting_date DESC
# 					LIMIT 1
# 			 	) AS last_journal_date
# 			FROM
# 				`tabSales Order` so
# 			LEFT JOIN 
# 				`tabSales Order Item` soi ON so.name = soi.parent
# 			WHERE
# 				so.docstatus = 1
# 			AND soi.parent = so.name
# 			AND
# 				soi.start_date <= '{date}'
# 			AND 
# 				soi.end_date >= '{date}'  {condition}
# 			""".
#    format(condition=condition, date=date), as_dict=True)
#     frappe.log_error(title="conditiason",message=condition)  
#     frappe.log_error(title="query_data",message=datas)  
#     return datas
	
def revenue_recognition_engine_query(condition=None,date=None):
    datas =  frappe.db.sql("""
			SELECT
				so.name AS sales_order,
			 	so.company AS company,
				so.transaction_date,
				soi.item_code,
				soi.name as so_item,
				soi.mandate,
				soi.offering,
				soi.revenue_method,
				soi.start_date,
				soi.end_date,
				soi.cost_center,
				soi.project,
			 	so.customer,
				soi.end_customer,
				so.currency as so_currency,
				soi.net_amount,
				(SELECT project_manager FROM `tabProject` WHERE name = soi.project) AS project_manager,
				soi.base_net_amount,
			 	soi.revenue_recognised_amount,
			 	so.conversion_rate,
				COALESCE(
					(
					SELECT
						SUM(jea.debit_in_account_currency/ jea.so_exchange_rate)
					FROM
						`tabJournal Entry` je
					LEFT JOIN
						`tabJournal Entry Account` jea
					ON
						je.name = jea.parent
					WHERE
						sales_order = so.name
						AND sales_order_item = soi.name
						AND je.docstatus = 1
					),
					0
				) AS journal_entry_value,
				CASE
					WHEN
						(
							COALESCE(
								(
									SELECT ABS(SUM(sii.amount) )
									FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
									WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
								), 0
							)
							-
							COALESCE(
								(
									SELECT ABS(SUM(sii.amount))
									FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
									WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1
								), 0
							)
			 			) < 0
			 		THEN
			 			0
			 		ELSE
			 			(
							COALESCE(
								(
									SELECT ABS(SUM(sii.amount))
									FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
									WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
								), 0
							)
							-
							COALESCE(
								(
									SELECT ABS(SUM(sii.amount))
									FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
									WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1
								), 0
							)
			 			)
			 	END AS credit_note_value,
				-- COALESCE(
				-- 	(
				-- 	SELECT
				-- 		SUM(jea.debit_in_account_currency/ jea.so_exchange_rate)
				-- 	FROM
				-- 		`tabJournal Entry` je
				-- 	LEFT JOIN
				-- 		`tabJournal Entry Account` jea
				-- 	ON
				-- 		je.name = jea.parent
				-- 	WHERE
				-- 		sales_order = so.name
				-- 		AND sales_order_item = soi.name
				-- 		AND je.docstatus = 1
				-- 	),
				-- 	0
				-- ) + (soi.revenue_recognised_amount) AS bc_recognised_revenue,
				COALESCE(
					(
					SELECT
						SUM(CASE WHEN jea.so_currency='INR' AND jea.credit>0 THEN
								jea.credit
							WHEN jea.so_currency='INR' AND jea.debit>0 THEN
								-jea.debit
							WHEN jea.so_currency<>'INR' AND jea.debit>0 THEN
								-(jea.debit/jea.so_exchange_rate)
							WHEN jea.so_currency<>'INR' AND jea.credit>0 THEN
								(jea.credit/jea.so_exchange_rate)
							ELSE 0 
						END ) AS journal_entry_value
					FROM
						`tabJournal Entry Account` jea

					INNER JOIN
						`tabJournal Entry` je

					ON
						je.name = jea.parent
					WHERE
						sales_order = so.name
						AND sales_order_item = soi.name
						AND je.docstatus = 1
						AND (jea.credit>0 OR jea.debit>0)
						AND jea.account IN(SELECT name FROM `tabAccount` WHERE parent_account='Revenue From Operations - IBSL')
					),
					0
				) + (soi.revenue_recognised_amount) AS bc_recognised_revenue,
				CASE
					WHEN
						(soi.net_amount -(
						COALESCE(
							(
							SELECT
								SUM(jea.debit_in_account_currency / jea.so_exchange_rate)
							FROM
								`tabJournal Entry` je
							LEFT JOIN `tabJournal Entry Account` jea
							ON je.name = jea.parent
							WHERE
								sales_order = so.name
								AND sales_order_item = soi.name
								AND je.docstatus = 1
							),
							0
						) + (soi.revenue_recognised_amount))) > 0
					THEN
						soi.net_amount -(
						COALESCE(
							(
							SELECT
								SUM(jea.debit_in_account_currency / jea.so_exchange_rate)
							FROM
								`tabJournal Entry` je
							LEFT JOIN `tabJournal Entry Account` jea
							ON je.name = jea.parent
							WHERE
								sales_order = so.name
								AND sales_order_item = soi.name
								AND je.docstatus = 1
							),
							0
						) + (soi.revenue_recognised_amount))
					ELSE 0
				END AS bc_unrecognised_revenue,
				-- COALESCE(
				-- 	(
				-- 	SELECT
				-- 		SUM(jea.debit_in_account_currency)
				-- 	FROM
				-- 		`tabJournal Entry` je
				-- 	LEFT JOIN
				-- 		`tabJournal Entry Account` jea
				-- 	ON
				-- 		je.name = jea.parent
				-- 	WHERE
				-- 		sales_order = so.name
				-- 		AND sales_order_item = soi.name
				-- 		AND je.docstatus = 1
				-- 	),
				-- 	0
				-- ) + (soi.revenue_recognised_amount * so.conversion_rate) AS recognised_revenue,
				COALESCE(
					(
					SELECT
						SUM(CASE WHEN jea.so_currency='INR' AND jea.credit>0 THEN
								jea.credit
							WHEN jea.so_currency='INR' AND jea.debit>0 THEN
								-jea.debit
							WHEN jea.so_currency<>'INR' AND jea.credit>0 THEN
								jea.credit
							WHEN jea.so_currency<>'INR' AND jea.debit>0 THEN
								-jea.debit
							ELSE 0 
						END) AS journal_entry_value
					FROM
						`tabJournal Entry Account` jea
					INNER JOIN
						`tabJournal Entry` je
						
					ON
						je.name = jea.parent
					WHERE
						sales_order = so.name
						AND sales_order_item = soi.name
						AND je.docstatus = 1
						AND (jea.credit>0 OR jea.debit>0)
						AND jea.account IN(SELECT name FROM `tabAccount` WHERE parent_account='Revenue From Operations - IBSL')
					),
					0
				)  + (soi.revenue_recognised_amount * so.conversion_rate) AS recognised_revenue,
				CASE
					WHEN
						(soi.base_net_amount -(
						COALESCE(
							(
							SELECT
								SUM(jea.debit_in_account_currency)
							FROM
								`tabJournal Entry` je  
							LEFT JOIN `tabJournal Entry Account` jea 
							ON je.name = jea.parent
							WHERE
								sales_order = so.name
								AND sales_order_item = soi.name
								AND je.docstatus = 1
							),
							0
						) + (soi.revenue_recognised_amount * so.conversion_rate))) > 0
					THEN 
						soi.base_net_amount -(
						COALESCE(
							(
							SELECT
								SUM(jea.debit_in_account_currency)
							FROM
								`tabJournal Entry` je  
							LEFT JOIN `tabJournal Entry Account` jea 
							ON je.name = jea.parent
							WHERE
								sales_order = so.name
								AND sales_order_item = soi.name
								AND je.docstatus = 1
							),
							0
						) + (soi.revenue_recognised_amount * so.conversion_rate))
					ELSE 0 
				END AS unrecognised_revenue,
				(
					SELECT
						estimated_costing
					FROM
						`tabProject`
					WHERE
						name = soi.project
				) AS budget_cost,
				(
					SELECT
						total_employee_cost + total_purchase_cost
					FROM
						`tabProject`
					WHERE
						name = soi.project
				) AS actual_cost,
				CASE
					WHEN (
						SELECT
							ROUND(((total_employee_cost + total_purchase_cost) / estimated_costing) * 100)
						FROM
							`tabProject`
						WHERE
							name = soi.project
						) > 100 THEN 100
					ELSE (
						SELECT
							ROUND(((total_employee_cost + total_purchase_cost) / estimated_costing) * 100)
						FROM
							`tabProject`
						WHERE
							name = soi.project
						)
				END AS per_complete,
				(
					SELECT je.posting_date
					FROM `tabJournal Entry` as je
					WHERE sales_order= so.name AND sales_order_item = soi.name AND je.docstatus = 1
					ORDER BY posting_date DESC
					LIMIT 1
				) as recognised_until,
				(
					SELECT je.posting_date
					FROM `tabJournal Entry` as je
					WHERE sales_order= so.name AND sales_order_item = soi.name AND je.docstatus = 1
					ORDER BY je.posting_date DESC
					LIMIT 1
			 	) AS last_journal_date
			FROM
				`tabSales Order` so
			LEFT JOIN 
				`tabSales Order Item` soi ON so.name = soi.parent
			WHERE
				so.docstatus = 1
				AND soi.parent = so.name   {condition}
			""".format(condition=condition,date=date, as_dict=True))
    frappe.log_error(title="data",message=datas)
    return datas
		