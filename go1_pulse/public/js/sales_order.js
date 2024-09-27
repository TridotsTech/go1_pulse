
frappe.ui.form.on('Sales Order', {
    refresh:function(frm){
        
        cur_frm.fields_dict.items.grid.get_field('billing_method_details').get_query = function(frm, cdt, cdn){
            let row = locals[cdt][cdn];
            let bm_list=[];
            console.log(1)
            if(row.billing_method){
                frappe.call({
                    method: "go1_pulse.api.get_billing_details",
                    args:{parent : row.billing_method},
                    async: false,
                    callback: function(res){
                        bm_list = res.message;
                    },
                });
            }
            return { filters:{"name":["in",bm_list ]} };
        };


        cur_frm.fields_dict.items.grid.get_field('project').get_query = function(frm, cdt, cdn){
            let row= locals[cdt][cdn];
            let p_list=0;
            if(row.is_common_project){
                frappe.call({
                    method:"go1_pulse.api.get_project_list",
                    args: {offering : row.offering || "", mandate: row.mandate || "", lob: row.line_of_business || "",  cost_center: row.cost_center || ""},
                    async: false,
                    callback: function(res){
                        p_list = res.message;
                    }
                });
                if(p_list){
                    if(row.mandate || row.line_of_business){
                        return {filters:{"name":["in",p_list ]
                        }};
                    }
                    else{
                        return {filters:{"cost_center":row.cost_center}};
                    }
                }
            }
            if(! row.is_common_project){
                console.log(1)
                if(cur_frm.doc.customer){
                    return {
                        filters:{"customer": cur_frm.doc.customer}
                    }
                }
                else{ 
                    return {
                        filters:{"cost_center":row.cost_center}
                    };
                 }
            }
        };



        cur_frm.fields_dict.items.grid.get_field('link_purchase_order').get_query = function(frm, cdt, cdn){
            let row = locals[cdt][cdn]
            if(row.linked_purchase_order){
                return {
                        filters:{"name": ["not in" , row.linked_purchase_order.split("\n") ]}
                    }
            }
        };
        


        cur_frm.refresh_field("items");
        cur_frm.refresh_field("billing_methods");
        // frm.remove_custom_button('Update Items')


    },
    
    //Generating Billing Methods
    get_billing_methods: function(frm){
        if(cur_frm.doc.docstatus === 0){
          frappe.run_serially([
              () => cur_frm.dirty(),
              () => cur_frm.save(),
              () => cur_frm.trigger("gen_billing_methods")
            ]);
        }
        else if(cur_frm.doc.docstatus == 1){
            frm.set_value('billing_methods', []);
            cur_frm.trigger("gen_billing_methods");
        }
    },

    gen_billing_methods: function(frm, cdt, cdn){
        frm.set_value('billing_methods', []);
        cur_frm.refresh();
        frm.refresh();
        $.each(frm.doc.items,  function(i,  d) {

            var billing_amt = d.amount;
            var billing = 100;
    

            // single
            if(d.offering && d.billing_method_details && (d.billing_method_details == "Single")){
                let r = cur_frm.add_child("billing_methods");
                r.item_id = d.name;
                r.item_code = d.item_code;
                r.offering = d.offering;
                r.billing_amt = billing_amt;
                r.billing = billing;
                r.billing_based_on = d.billing_based_on;
                r.customer = d.end_customer
            }
            
            //mutliple
            if(d.offering && d.billing_method_details && (d.billing_method_details == "Multiple")){
                for(let i = 0; i < d.no_of_process;i++){
                    let r = cur_frm.add_child("billing_methods");
                    r.item_id = d.name;
                    r.item_code = d.item_code;
                    r.offering = d.offering;
                    r.billing_amt = billing_amt/d.no_of_process;
                    r.billing = billing/d.no_of_process;
                    r.billing_based_on = d.billing_based_on;
                    r.customer = d.end_customer
                }
            }
            

            if(d.offering && d.billing_method == "Frequency"){
                console.log(d.offering)
                if(!d.start_date){
                    frappe.throw(`Select Valid Date in table <b>Items</b> at row <b>${d.idx}</b>`)
                }
                let date = d.actual_start_date ? d.actual_start_date :d.start_date;
                let nom = 0;

                if( d.go1_pulse_method == "Equal revenue over the contract period" && (!d.end_date || !d.start_date)){
                    return
                }
                
                frappe.call({
                    method: "go1_pulse.api.month_diff",
                    args: {ed_date: d.end_date, st_date: d.actual_start_date ?d.actual_start_date :d.start_date},
                    async:false,
                    callback: function(res){
                        nom = res.message;
                    }
                });
                

                if( !(d.billing_method_details == "Monthly")){
                    if(moment(d.actual_start_date ?d.actual_start_date :d.start_date).isSameOrBefore(moment(d.actual_start_date ?d.actual_start_date :d.start_date).endOf('month').format('YYYY-MM-DD'))){
                        nom -= 1;
                    }
                }


                if( (d.billing_method_details == "Monthly")){
                    nom = 12;
                }


                let nor = d.billing_method_details == "Annual"? Math.ceil(nom/12) : d.billing_method_details == "Half Yearly"? Math.ceil(nom/6) : d.billing_method_details == "Quarterly"? Math.ceil(nom/3) :["Monthly", "Number of Units x Rate", "Monthly for hours worked"].includes(d.billing_method_details) ? Math.ceil(nom/1):0;
                let noi = d.billing_method_details == "Annual"? 12 : d.billing_method_details == "Half Yearly"? 6 : d.billing_method_details == "Quarterly"? 3 : ["Monthly", "Number of Units x Rate", "Monthly for hours worked"].includes(d.billing_method_details) ? 1:0;
                

                for(let i = 0; i < nor;i++){
                    let r = cur_frm.add_child("billing_methods");
                    r.item_code = d.item_code;
                    r.item_id = d.name;
                    r.customer = d.end_customer;
                    r.billing_based_on = d.billing_based_on;

                    if(d.billing_method_details != "Monthly"){
                        r.billing_amt = billing_amt/nor;
                        r.billing = billing/nor;
                       
                        
                    }
                    r.offering = d.offering;
                    r.basis = "Date";

                    if(d.billing_method_details == "Monthly"){
                        if ((i+1) == nor){
                            r.date = d.end_date;
                            r.billing_amt = billing_amt/nor;
                            r.billing = billing/nor;
                         
                        }
                        else{
                            r.date = moment(date).endOf('month').format('YYYY-MM-DD');
                            r.billing_amt = billing_amt/nor;
                            r.billing = billing/nor;
                        }
                    }


                    else{
                        r.date = frappe.datetime.add_days(frappe.datetime.add_months(date,noi),-1);
                    }


                    date= frappe.datetime.add_days(frappe.datetime.add_months(date,noi), -1);
                    date = frappe.datetime.add_days(date, 1);
                }
            }
            
            
            cur_frm.refresh_field("billing_methods");
        });
    },

    //Create Invoice
    create_invoice: function(frm) {
        let selected = cur_frm.fields_dict.billing_methods.grid.get_selected_children();
        console.log(selected)
        let selected_rt = cur_frm.fields_dict.si_return_details.grid.get_selected_children();
        if(selected.length === 0 && !frm.doc.show_return_details){
            frappe.throw("Select One Or Multiple Row In The Billing Table ")
        }
        if (frm.doc.show_return_details && selected_rt.length > 0) {
            var rt_msg = "";
            var is_valid = 1;
            selected_rt.forEach((ele) => {
                if (ele.is_invoiced) {
                    rt_msg += `<b>Row ${ele.idx}</b> - already invoiced<br><hr>`;
                    is_valid = 0;
                }
            }) 
            if (rt_msg) {
                frappe.throw(rt_msg);
            }
            if (is_valid == 1) {
                frappe.call({
                    method: "go1_pulse.api.create_invoice",
                    freeze: true,
                    args: {
                        source_name: frm.doc.name,
                        sales_return_details: selected_rt,
                    },
                    callback: function(res) {
                        if (!res.exc && res.message != "No Data") {
                            frappe.model.sync(res.message);
                            frappe.set_route("Form", res.message.doctype, res.message.name);
                        }
                    },
                });
            }
        }
        if (selected.length === 0) {
           
            if (frm.doc.show_return_details) {
                if (selected_rt.length == 0) {
                    frappe.show_alert("Select One or Multiple row")
                }
            }
        } else {
            let msg = "";
            selected.forEach((ele) => {
                if (ele.is_billed) {
                    msg += `<b>Row ${ele.idx}</b> - already billed<br><hr>`
                }
            }) 
            if (msg) {
                frappe.throw(msg);
            } frappe.call({
                method: "go1_pulse.api.create_invoice",
                args: {
                    source_name: frm.doc.name,
                    datas: selected,
                    sales_return_details: frm.doc.sales_return_details,
                },
                callback: function(res) {
                    if (!res.exc && res.message != "No Data") {
                        frappe.model.sync(res.message);
                        frappe.set_route("Form", res.message.doctype, res.message.name);
                    }
                },
            });
        }
    },

    before_submit: function(frm) {
        cur_frm.set_currency_labels(["custom_billed_amount"], frm.doc.currency, "items");
        if (cur_frm.doc.billing_methods) {
            cur_frm.doc.billing_methods.forEach((row) => {
                if (row.basis == "Date" && row.billing_milestone) {
                    row.billing_milestone = "";
                }
                if (row.basis == "Activity" && !row.billing_milestone) {
                    frappe.throw(`Billing milestone Can not be empty at <b>row - ${row.idx}</b> `);
                }
            });
        }
        let flag = 0;
        if (cur_frm.doc.items) {
            frm.doc.items.forEach((d) => {
                if (["Equal revenue over the contract period", "100% revenue on delivery, irrespective of billing time"].includes(d.revenue_method)) {
                    flag = 1;
                }
            });
            if (flag && frm.doc.billing_methods.length == 0) {
                frappe.throw("Table Billing Methods Can not be Empty");
            }
        }
    }
    
});



//Sales Order Item
frappe.ui.form.on('Sales Order Item', {
	"offering":function(frm, cdt, cdn){
		update_offering_hsn(frm, cdt, cdn);
	},

    actual_start_date: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if(row.actual_start_date){
            let end_date = frappe.datetime.add_days(frappe.datetime.add_months(row.actual_start_date,12), -1);
            frappe.model.set_value(cdt, cdn, "end_date", end_date);
        }
    },
    start_date: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        console.log(row)
        if(!row.actual_start_date){
            let end_date = frappe.datetime.add_days(frappe.datetime.add_months(row.start_date,12), -1);
            frappe.model.set_value(cdt, cdn, "end_date", end_date);
        }
        
        if(!row.revenue_recognised_until && row.actual_start_date){
            let start_date = frappe.datetime.add_days(row.revenue_recognised_until, 1);
            frappe.model.set_value(cdt, cdn, "actual_start_date", "");
        }
    },




    revenue_recognised_until: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if(moment(row.revenue_recognised_until).isBefore(moment(row.actual_start_date))){
            frappe.model.set_value(cdt, cdn, "revenue_recognised_until", "");
        }
        if(row.revenue_recognised_until){
            let start_date = frappe.datetime.add_days(row.revenue_recognised_until, 1);
            frappe.model.set_value(cdt, cdn, "start_date", start_date);
        }
    },



    billing_method_details: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "no_of_process","");


        if(row.billing_method_details.toLowerCase() == "multiple"){
           frappe.model.set_value(cdt, cdn, "no_of_process",2); 
        }


        
    },


    
    billing_method: function(frm, cdt, cdn){
        frappe.model.set_value(cdt, cdn, "billing_method_details","");
    }



});



var update_offering_hsn =  function(frm, cdt, cdn){
    var child = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, "project","");

    if ((child.offering) && (child.item_code)){
        frappe.call({
                        method: "go1_pulse.api.check_installed_app",
                        args: {"app_name":"india_compliance"},
                        callback:function(r){
                            if(r.message.status=="Success"){
                                frappe.db.get_value("Offering", child.offering, ["custom_hsnsac"]).then(function(value) {
                                if (value.message.custom_hsnsac){
                                    var hsn_code =  value.message.custom_hsnsac
                                    console.log(hsn_code)
                                    frappe.model.set_value(cdt, cdn, "gst_hsn_code",  hsn_code);
                                }
                                else{
                                    frappe.db.get_value("Item", child.item_code, ["gst_hsn_code"]).then(function(value) { 
                                        if (value.message.gst_hsn_code){
                                            var hsn_code =  value.message.gst_hsn_code
                                            frappe.model.set_value(cdt, cdn, "gst_hsn_code",  hsn_code);
                                        }

                                    });
                                }
                            });
                            }
                            
                        }
         })        
        frm.refresh_field('items');
    }



    // if(child.is_common_project){
    //     frappe.call({
    //         method:"go1_pulse.api.get_common_project",
    //         args: {offering: child.offering || "", lob:child.line_of_business || "", mandate:child.mandate || "",  cost_center: child.cost_center || ""},
    //         callback: function(res){
    //             if(res.message){
    //                 console.log(res.message)
    //                 frappe.model.set_value(cdt, cdn, "project",res.message);
    //             }
    //             else{
    //                 frappe.msgprint("Common project could not be found");
    //             }
    //         },
    //     });
    // }

      

}