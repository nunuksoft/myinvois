import frappe


def execute():
    """
    Create General TIN customers and suppliers for Malaysia e-invoicing system.
    These are used when actual customers/suppliers don't have TIN numbers.
    """
    
    # General TIN Customers (for Sales Invoices)
    general_tin_customers = [
        {
            "name": "EI00000000010",
            "customer_name": "General Public (E-Invoice)",
            "customer_group": "Individual",
            "territory": "Malaysia",
            "custom_customer_tin_number": "EI00000000010",
            "description": "General Public TIN - Used for local individuals providing only NRIC, consolidated e-invoices, and consolidated self-billed e-invoices for suppliers"
        },
        {
            "name": "EI00000000020",
            "customer_name": "Foreign Buyer/Shipping Recipient (E-Invoice)",
            "customer_group": "Individual",
            "territory": "Malaysia",
            "custom_customer_tin_number": "EI00000000020",
            "description": "Foreign Buyer or Foreign Shipping Recipient TIN - Used for non-Malaysian individuals with passport, MyPR, MyKas, foreign buyers without TIN, and foreign shipping recipients without TIN"
        },
        {
            "name": "EI00000000040",
            "customer_name": "Government or Government Authorities",
            "customer_group": "Individual",
            "territory": "Malaysia",
            "custom_customer_tin_number": "EI00000000040",
            "description": "Buyer TIN Government or Government Authorities - Used for transactions involving government, state governments, statutory or local authorities, and exempt institutions not assigned a TIN"
        }
    ]
    
    # General TIN Supplier (for Purchase Invoices)
    general_tin_supplier = {
        "name": "EI00000000030",
        "supplier_name": "Foreign Supplier (E-Invoice)",
        "supplier_group": "Services",
        "supplier_type": "Individual",
        "custom_customer_tin_number": "EI00000000030",
        "description": "Foreign Supplier TIN - Used for individual foreign suppliers in self-billed e-invoices and import transactions with foreign suppliers without TIN"
    }
    
    # Create General TIN Customers
    for customer_data in general_tin_customers:
        # Check if customer already exists
        customer_name = customer_data["customer_name"]
        customer_id = customer_data["name"]
        
        if not frappe.db.exists("Customer", customer_name):
            try:
                # Verify customer_group exists, use default if not
                customer_group = customer_data["customer_group"]
                if not frappe.db.exists("Customer Group", customer_group):
                    customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Individual"
                
                # Verify territory exists, use default if not
                territory = customer_data["territory"]
                if not frappe.db.exists("Territory", territory):
                    territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
                
                # Create customer
                customer = frappe.get_doc({
                    "doctype": "Customer",
                    "name": customer_data["name"],
                    "customer_name": customer_name,
                    "customer_group": customer_group,
                    "territory": territory,
                    "custom_customer_tin_number": customer_data["custom_customer_tin_number"],
                    "customer_type": "Individual",
                    "disabled": 0
                })
                
                # Add description if available
                if customer_data.get("description"):
                    customer.description = customer_data["description"]
                
                customer.insert(ignore_permissions=True)
                frappe.db.commit()
                
                print(f"✅ Created General TIN Customer: {customer_name} with TIN {customer_data['custom_customer_tin_number']}")
                
            except Exception as e:
                frappe.log_error(
                    title=f"Error creating General TIN Customer: {customer_name}",
                    message=f"Failed to create customer {customer_name}: {str(e)}"
                )
                frappe.db.rollback()
        else:
            # Update existing customer if TIN number is missing or incorrect
            customer = frappe.get_doc("Customer", customer_id)
            needs_update = False
            if customer.custom_customer_tin_number != customer_data["custom_customer_tin_number"]:
                customer.db_set("custom_customer_tin_number", customer_data["custom_customer_tin_number"], commit=False)
                needs_update = True
            if customer_data.get("description") and customer.description != customer_data["description"]:
                customer.db_set("description", customer_data["description"], commit=False)
                needs_update = True
            if needs_update:
                frappe.db.commit()
                print(f"✅ Updated General TIN Customer: {customer_name}")
            else:
                print(f"ℹ️  General TIN Customer already exists with correct data: {customer_name}")
    
    # Create General TIN Supplier (EI00000000030)
    supplier_id = general_tin_supplier["name"]
    supplier_name = general_tin_supplier["supplier_name"]

    if not frappe.db.exists("Supplier", supplier_name):
        try:
            # Verify supplier_group exists, use default if not
            supplier_group = general_tin_supplier["supplier_group"]
            if not frappe.db.exists("Supplier Group", supplier_group):
                supplier_group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups"
            
            # Create supplier
            supplier = frappe.get_doc({
                "doctype": "Supplier",
                "name": supplier_id,
                "supplier_name": supplier_name,
                "supplier_group": supplier_group,
                "supplier_type": general_tin_supplier.get("supplier_type", "Individual"),
                "custom_customer_tin_number": general_tin_supplier["custom_customer_tin_number"],
                "disabled": 0
            })
            
            # Add description if available
            if general_tin_supplier.get("description"):
                supplier.description = general_tin_supplier["description"]
            
            supplier.insert(ignore_permissions=True)
            frappe.db.commit()
            
            print(f"✅ Created General TIN Supplier: {supplier_name} with TIN {general_tin_supplier['custom_customer_tin_number']}")
            
        except Exception as e:
            frappe.log_error(
                title=f"Error creating General TIN Supplier: {supplier_name}",
                message=f"Failed to create supplier {supplier_name}: {str(e)}"
            )
            frappe.db.rollback()
    else:
        # Update existing supplier if TIN number is missing or incorrect
        supplier = frappe.get_doc("Supplier", supplier_name)
        needs_update = False
        if supplier.custom_customer_tin_number != general_tin_supplier["custom_customer_tin_number"]:
            supplier.db_set("custom_customer_tin_number", general_tin_supplier["custom_customer_tin_number"], commit=False)
            needs_update = True
        if general_tin_supplier.get("description") and supplier.description != general_tin_supplier["description"]:
            supplier.db_set("description", general_tin_supplier["description"], commit=False)
            needs_update = True
        if needs_update:
            frappe.db.commit()
            print(f"✅ Updated General TIN Supplier: {supplier_name}")
        else:
            print(f"ℹ️  General TIN Supplier already exists with correct data: {supplier_name}")

