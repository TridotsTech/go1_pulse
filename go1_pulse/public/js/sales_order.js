frappe.ui.form.on('Sales Order', {
	// onload: function(frm) {
    // },
    // validate:function(frm){
    // }

});

frappe.ui.form.on('Sales Order Item', {
	"offering":function(frm, cdt, cdn){
		update_offering_hsn(frm, cdt, cdn);
	}
});



var update_offering_hsn =  function(frm, cdt, cdn){
    var child = locals[cdt][cdn];
    if ((child.offering) && (child.item_code)){
        frappe.call({
                        method: "contetra_customisations.api.check_installed_app",
                        args: {"app_name":"india_compliance"},
                        callback:function(r){
                            if(r.message.status=="Success"){
                                frappe.db.get_value("Offering", child.offering, ["custom_hsnac"]).then(function(value) {
                                if (value.message.custom_hsnsac){
                                    var hsn_code =  value.message.custom_hsnsac
                                    // console.log("@@@@@hsn_code@@@@@!!!!",hsn_code)
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
        // console.log("@@@@@1111@@@@@!!!!")
        
        frm.refresh_field('items');
    }
}