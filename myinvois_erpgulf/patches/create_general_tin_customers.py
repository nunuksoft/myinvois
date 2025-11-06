import frappe


def execute():
	"""
	Create General TIN customers and suppliers for Malaysia e-invoicing system.
	These are used when actual customers/suppliers don't have TIN numbers.
	"""
	
	# General TIN Customers (for Sales Invoices)
	general_tin_customers = [
		{
			"customer_name": "EI000000000010 - General Public's TIN",
			"customer_group": "Individual",
			"territory": "Malaysia",
			"custom_customer_tin_number": "EI000000000010",
			"description": "General Public's TIN - Used for local individuals providing only NRIC, consolidated e-invoices, and consolidated self-billed e-invoices for suppliers"
		},
		{
			"customer_name": "EI000000000020 - Foreign Buyer's / Foreign Shipping Recipient's TIN",
			"customer_group": "Individual",
			"territory": "Malaysia",
			"custom_customer_tin_number": "EI000000000020",
			"description": "Foreign Buyer's / Foreign Shipping Recipient's TIN - Used for non-Malaysian individuals (passport, MyPR, MyKas), foreign buyers without TIN, and foreign shipping recipients without TIN"
		},
		{
			"customer_name": "EI000000000040 - Buyer's TIN (Government or Government Authorities)",
			"customer_group": "Individual",
			"territory": "Malaysia",
			"custom_customer_tin_number": "EI000000000040",
			"description": "Buyer's TIN (Government or Government Authorities) - Used for transactions involving government, state governments, statutory or local authorities, and exempt institutions not assigned a TIN"
		}
	]
	
	# General TIN Supplier (for Purchase Invoices)
	general_tin_supplier = {
		"supplier_name": "EI000000000030 - Foreign Supplier's TIN",
		"supplier_group": "Services",
		"custom_customer_tin_number": "EI000000000030",
		"description": "Foreign Supplier's TIN - Used for individual foreign suppliers in self-billed e-invoices and import transactions with foreign suppliers without TIN"
	}
	
	# Create General TIN Customers
	for customer_data in general_tin_customers:
		# Check if customer already exists
		customer_name = customer_data["customer_name"]
		if not frappe.db.exists("Customer", customer_name):
			try:
				# Create customer
				customer = frappe.get_doc({
					"doctype": "Customer",
					"customer_name": customer_name,
					"customer_group": customer_data["customer_group"],
					"territory": customer_data["territory"],
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
			customer = frappe.get_doc("Customer", customer_name)
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
	
	# Create General TIN Supplier (EI000000000030)
	supplier_name = general_tin_supplier["supplier_name"]
	if not frappe.db.exists("Supplier", supplier_name):
		try:
			# Create supplier
			supplier = frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": supplier_name,
				"supplier_group": general_tin_supplier["supplier_group"],
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

