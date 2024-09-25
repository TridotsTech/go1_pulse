const date = new Date();
let currentDay= String(date.getDate()).padStart(2, '0');
let currentMonth = String(date.getMonth()+1).padStart(2,"0");
let currentYear = date.getFullYear();
let currentDateTime = `${currentYear}-${currentMonth}-${currentDay} 00:00:00`;
frappe.ui.form.on("Timesheet", {
    onload: function(frm) {
        // Hide billing details
        frm.set_df_property('total_billable_hours', 'hidden', 1);
        frm.set_df_property('base_total_billable_amount', 'hidden', 1);
        frm.set_df_property('base_total_billed_amount', 'hidden', 1);
        frm.set_df_property('base_total_costing_amount', 'hidden', 1);
        frm.set_df_property('total_billed_hours', 'hidden', 1);
        frm.set_df_property('total_billable_amount', 'hidden', 1);
        frm.set_df_property('total_billed_amount', 'hidden', 1);
        frm.set_df_property('total_costing_amount', 'hidden', 1);
        frm.set_df_property('per_billed', 'hidden', 1);
        $('[class="row-index sortable-handle col"]').attr("style","pointer-events:none;")
        // Set current date as default if no start date is given.
        if (!frm.doc.log_date && frm.doc.docstatus == 0){
            const date = new Date();
            let day = date.getDate(); if (day < 10) {day = `0${day}`};
            let month = date.getMonth() + 1; if (month < 10) {month = `0${month}`};
            let year = date.getFullYear();
            let currentDate = `${year}-${month}-${day}`
            frm.doc.log_date = currentDate
            frm.refresh_field("log_date")
        }
    
     frm.fields_dict["time_logs"].grid.get_field("activity_type").get_query = function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            if(row.project){
                return {
                    "query":"revenue.timesheet.get_project_activity_types",
                    "filters": {
                        "project":row.project
                    }
                }
            }
        }
    },
    

    // Refreshes child table from and to time on changing start date.
    log_date: function(frm){
        if (!frm.doc.employee){
            frappe.throw(__("Please select an Employee"))
        }
       
        if (frm.doc.log_date < get_date(currentDateTime) && frm.doc.log_date != "") {
            frappe.call({
                method: "revenue.timesheet.check_absent",
                args: {
                    "date": frm.doc.log_date,
                    "employee": frm.doc.employee
                },
                callback: function(r){
                    if (r.message){
                        frm.set_value("log_date", "")
                        frappe.throw(__("You were absent on that day"))
                    }
                }
            });
            for (var row of cur_frm.get_field("time_logs").grid.grid_rows){
                var to_time = frappe.utils.filter_dict(row.docfields, {fieldname:"to_time"})[0]
                var from_time = frappe.utils.filter_dict(row.docfields, {fieldname:"from_time"})[0]
                to_time.read_only = 1
                from_time.read_only = 1
                if (row.doc.idx == 1) {
                    let currentDate = frm.doc.log_date;
                    row.doc.from_time = currentDate+" 08:00:00";
                    row.doc.to_time = get_date(row.doc.from_time, row.doc.hours)
                }else{
                    row.doc.from_time = cur_frm.get_field("time_logs").grid.grid_rows[row.doc.idx-2].doc.to_time
                    row.doc.to_time = get_date(row.doc.from_time, row.doc.hours)
                }
            }
        }
        if (frm.doc.log_date > get_date(currentDateTime) && frm.doc.log_date != ""){
            frm.set_value("log_date", "")
            frappe.throw(__("Start Date cannot be a future date."))
        }
    },
    

    refresh: function(frm) {
        // Used to reset sent_for_approval status and fields on rejection of timesheets.
        for (var row of cur_frm.get_field("time_logs").grid.grid_rows){
            if (row.doc.approval_status == "Employee Pending"){
                cur_frm.doc.sent_for_approval = 0
                frm.set_df_property("sent_for_approval", "hidden", 1)
                frm.set_df_property("log_date", "read_only", 0)
                var columns = row.columns
                columns.activity_type.df.read_only = 0
                columns.project.df.read_only = 0
                columns.hours.df.read_only = 0
                columns.description.df.read_only = 0
                frm.refresh_field("time_logs")
                frm.refresh_field("log_date")
                break
            }else{
                cur_frm.doc.sent_for_approval = 1
                frm.set_df_property("sent_for_approval", "hidden", 0)
                frm.set_df_property("log_date", "read_only", 1)
                var columns = row.columns
                columns.activity_type.df.read_only = 1
                columns.project.df.read_only = 1
                columns.customer.df.read_only = 1
                columns.hours.df.read_only = 1
                columns.description.df.read_only = 1
                frm.refresh_field("time_logs")
                frm.refresh_field("log_date")
            }
        }
       
        for (var row of cur_frm.get_field("time_logs").grid.grid_rows){
            if (!has_common(frappe.user_roles, ['System Manager'])){
                var to_time = frappe.utils.filter_dict(row.docfields, {fieldname:"to_time"})[0]
                var from_time = frappe.utils.filter_dict(row.docfields, {fieldname:"from_time"})[0]
                to_time.read_only = 1
                from_time.read_only = 1
            }
            if (row.doc.customer){
                row.columns.customer.df.read_only = 1
            }else{
                row.columns.customer.df.read_only = 0
            }
            if (row.doc.approval_status == "Employee Pending"){
                row.columns.hours.df.read_only = 0
            }else{
                row.columns.hours.df.read_only = 1
            }
            frm.refresh_field("time_logs")
        };
        if (!has_common(frappe.user_roles, ['System Manager'])) {
            cur_frm.fields_dict.employee.df.read_only = 1
            refresh_field("employee")
        }else{
            cur_frm.fields_dict.employee.df.read_only = 0
            refresh_field("employee")
        }
    // Send for Approval Button
    if (frm.doc.sent_for_approval == 1){
        $('head').append('<style>[id="page-Timesheet"] button[class="btn btn-xs btn-secondary grid-add-row"]{display:none !important;}</style>')
        $('head').append('<style>[id="page-Timesheet"] button[class="btn btn-xs btn-danger grid-remove-rows"]{display:none !important;}</style>')
        $('head').append('<style>[id="page-Timesheet"] div[class="row-index sortable-handle col"]{display:none !important;}</style>')
    }
    if (frm.doc.sent_for_approval != 1){
        $('head').append('<style>[id="page-Timesheet"] button[class="btn btn-xs btn-secondary grid-add-row"]{display:inline-block !important;}</style>')
        $('head').append('<style>[id="page-Timesheet"] button[class="btn btn-xs btn-danger grid-remove-rows"]{display:inline-block !important;}</style>')
        $('head').append('<style>[id="page-Timesheet"] div[class="row-index sortable-handle col"]{display:inline-block !important;}</style>')
        if (!frm.doc.__islocal)
        {
            frm.add_custom_button(__('Send for Approval'), function(){
                if (frappe.session.user != frm.doc.owner){
                    frappe.throw(__("You are not the owner of this timesheet."))
                }
                frappe.confirm(
                    __("Are you sure you want to send for approval?"),
                    function() {
                        for (var row of cur_frm.get_field("time_logs").grid.grid_rows){
                            if (row.doc.approval_status == "Employee Pending") {
                                row.doc.approval_status = "RM Pending"
                            }
                        }
                        cur_frm.doc.sent_for_approval = 1
                        frm.set_df_property("sent_for_approval", "hidden", 0)
                        frm.set_df_property("log_date", "read_only", 1)
                        for(var row of cur_frm.get_field("time_logs").grid.grid_rows) {
                            var columns = row.columns
                            columns.activity_type.df.read_only = 1
                            columns.project.df.read_only = 1
                            columns.customer.df.read_only = 1
                            columns.hours.df.read_only = 1
                            columns.description.df.read_only = 1
                        }
                        frappe.call({
                            method: "revenue.timesheet.send_mail",
                            args: {
                                "employee": frm.doc.employee,
                                "name": frm.doc.name
                            },
                        });
                        frm.dirty();
                        frm.save();
                    },
                    function() {$(this).hide()}
                )
            });
        }
    }
 
      
    if (frappe.session.user != frm.doc.owner && !has_common(frappe.user_roles, ['System Manager'])){
        $('head').append('<style>[id="page-Timesheet"] [data-label="Send%20for%20Approval"]{display:none !important;}</style>')
    }
    $('[data-label="Send%20for%20Approval"]').removeClass("btn-default")
    $('[data-label="Send%20for%20Approval"]').addClass("btn-primary")
    $('head').append('<style>[id="page-Timesheet"] div[class="form-message blue"]{display:none !important;}</style>')
    // Hides child table edit column, start/end dates, start/resume timers and submit button.
    if(frappe.session.user!="Administrator" && !has_common(frappe.user_roles, ['System Manager'])){
        $('head').append('<style>[id="page-Timesheet"] div[data-fieldname="time_logs"] .grid-row .col:last-child,[data-fieldname="start_date"]{display:none !important;}</style>')
        $('head').append('<style>[id="page-Timesheet"] div[data-fieldname="time_logs"] .grid-row .col:last-child,[data-fieldname="end_date"]{display:none !important;}</style>')
    }
    $('head').append('<style>[id="page-Timesheet"] button[data-label="Resume%20Timer"]{display:none !important;}</style>')
    $('head').append('<style>[id="page-Timesheet"] button[data-label="Start%20Timer"]{display:none !important;}</style>')
    $('head').append('<style>[id="page-Timesheet"] button[data-label="Submit"]{display:none !important;}</style>')
    if(!has_common(frappe.user_roles, ['System Manager'])) {
        frm.set_df_property('start_date', 'hidden', 1);
        frm.set_df_property('end_date', 'hidden', 1);
    }
      
    },
    before_save: function(frm){
        
        for (var row of cur_frm.doc.time_logs){
            if (row.hours == 0) {
                frappe.throw(__("Timesheet hours cannot be 0."))
            }
        }
        if (frm.doc.total_hours > 16){
            frappe.throw(__("Timesheet total hours cannot be greater than 16."))
        }
        if (frm.doc.log_date > get_date(currentDateTime) && frm.doc.log_date != ""){
            frm.set_value("log_date", "")
            frappe.throw(__("Start Date cannot be a future date."))
        }
        for (var row of cur_frm.get_field("time_logs").grid.grid_rows){
            var to_time = frappe.utils.filter_dict(row.docfields, {fieldname:"to_time"})[0]
            var from_time = frappe.utils.filter_dict(row.docfields, {fieldname:"from_time"})[0]
            to_time.read_only = 1
            from_time.read_only = 1
            if (row.doc.idx == 1) {
                let currentDate = frm.doc.log_date;
                row.doc.from_time = currentDate+" 08:00:00";
                row.doc.to_time = get_date(row.doc.from_time, row.doc.hours)
            }else{
                row.doc.from_time = cur_frm.get_field("time_logs").grid.grid_rows[row.doc.idx-2].doc.to_time
                row.doc.to_time = get_date(row.doc.from_time, row.doc.hours)
            }
        }
       
    }
});
var get_date = function get_date(old_date,old_hours=0){
    return frappe.call({
        method:"revenue.timesheet.get_date",
        async:false,
        args:{
            "date":old_date,
            "hours":old_hours
        },
        callback: function(r){
            return r.message
        }
    }).responseJSON.message
}

// Automatically sets from and to time on changing hrs in child table.
frappe.ui.form.on("Timesheet Detail", {
    hours:function(frm, cdt, cdn){
        var d = locals[cdt][cdn];
        if(d.idx==1){
            let currentDate = frm.doc.log_date;
            d.from_time = currentDate+" 08:00:00";
            d.to_time = get_date(d.from_time, d.hours)
        }
        else{
            d.from_time = cur_frm.get_field("time_logs").grid.data[d.idx-2].to_time;
            d.to_time = get_date(d.from_time, d.hours)
        }
    },
   
    customer:function(frm, cdt, cdn){
        var d = locals[cdt][cdn];
        setTimeout(function(){
            if(d.customer){
                $('[data-fieldname="time_logs"] .grid-row[data-idx="'+d.idx+'"]').find('input[data-fieldname="customer"]').attr("disabled","disabled")
            }
        },250)
            cur_frm.refresh_field('time_logs');
    },
});



