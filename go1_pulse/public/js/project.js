frappe.ui.form.on("Project", {
    onload: function(frm) {
    frm.set_query("project_manager", function() {
        return {
            "query":"revenue.timesheet.get_filtered_users",
           
        }

    })
}
});