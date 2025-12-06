from db_service import (
    get_customer_by_phone,
    insert_customer,
    get_substitutes_by_salt,
    create_order,
    update_order_payment,
    update_order_status,
    get_order,
    insert_payment,
    get_payment_status,
    insert_prescription_request,
    get_medicine_fuzzy,
    insert_order_item, 
   
)
from datetime import datetime, timedelta
import payment_gateway
from whatsapp_sender import send_whatsapp_message
from pdf_services import generate_invoice_pdf



class BillingEngine:
    def __init__(self):
        self.step = "greet"
        self.customer = None

        # Current medicine 
        self.medicine = None          
        self.quantity = None
        self.cart = []

        # Order details
        self.order_id = None
        self.payment_id = None
        self.address = None
        self.payment_mode = None

        # Totals
        self._last_total_amount = 0.0        # grand total (incl. delivery)
        self._delivery_charge = 0.0          # delivery charge only

    
    # amount inluding for delivery
   
    def _is_tamil_nadu(self, address: str) -> bool:
        addr = (address or "").lower()
        return "tamil nadu" in addr or "tamilnadu" in addr or " tn" in addr

    def _get_delivery_charge(self, address: str) -> int:
        """
        Delivery charge:
        - Tamil Nadu / Kerala / Andhra Pradesh → ₹50
        - Others → ₹60
        """
        addr = (address or "").lower()
        if (
            "tamil nadu" in addr
            or "tamilnadu" in addr
            or "kerala" in addr
            or "andhra pradesh" in addr
            or "andhrapradesh" in addr
            or "andhra" in addr
        ):
            return 50
        return 60

    def _cart_subtotal(self) -> float:
        return sum(item["line_total"] for item in self.cart)

    def _build_cart_summary_and_ask_confirm(self) -> str:
        """
        Build summary of ALL non-Rx medicines in cart
        and ask user to confirm order before address.
        Includes expiry date per medicine.
        """
        if not self.cart:
            return "Your cart is empty. Please enter a medicine name to start."

        lines = []
        lines.append("Here is your order summary:\n")

        for idx, item in enumerate(self.cart, start=1):
            lines.append(
                f"{idx}. {item['name']} – {item['quantity']} strips × ₹{item['price']} "
                f"(Expiry: {item['expiry_date']}) = ₹{item['line_total']}"
            )

        subtotal = self._cart_subtotal()
        self._last_total_amount = float(subtotal)  # without delivery yet

        lines.append(f"\nSubtotal (without delivery): ₹{subtotal}")
        lines.append("Delivery charges will be added based on your state.")
        lines.append("\nCan we confirm this order and proceed to address? (yes/no)")

        return "\n".join(lines)

    # -------------------------------
    # Flow methods
    # -------------------------------
    def greet_user(self):
        self.step = "collect_customer"
        return (
            "Hello! Welcome to Medingen"
            "   Medingen Saves you Health and Wealth "
            " Kindly enter your name, phone number, and email ID to proceed."
        )

    def save_customer(self, name, phone, email):
        """
        Save or reuse customer based on phone.
        After this, ALWAYS go to ask_medicine and explicitly ask for medicine name.
        """
        record = get_customer_by_phone(phone)
        if record:
            # Existing customer
            self.customer = record
            self.step = "ask_medicine"
            return (
                f"Hello {record[1]}! How may I help you place your order?\n"
                f"Kindly enter the medicine name."
            )
        else:
            # New customer
            insert_customer(name, phone, email)
            self.customer = get_customer_by_phone(phone)
            self.step = "ask_medicine"
            return (
                "Your details have been saved. "
                "How may I help you place your order?\n"
                "Kindly enter the medicine name."
            )

    def lookup_medicine(self, med_name: str):
        """
        Step: ask_medicine
        Uses fuzzy search to find a medicine and then:
        - If expired   → inform user
        - If Rx needed → save prescription request, send WhatsApp, go to prescription_wait
        - Else         → proceed to quantity flow (non-Rx, will be added to cart)
        """
        med_name = med_name.strip()
        med = get_medicine_fuzzy(med_name)

        if not med:
            return "This medicine is not available."
        self.medicine = med
        (
            med_id,
            name,
            salt_name,
            price,
            no_of_tablets,
            stock,
            prescription_required,
            expiry_str,
        ) = med

        # Expiry check
        expiry_date = datetime.fromisoformat(expiry_str).date()
        today = datetime.now().date()
        if expiry_date < today:
            return f"{name} is expired and cannot be sold."

        #  CASE-1: Prescription required
        if str(prescription_required).lower() == "yes":
            # 1) Save prescription request in DB
            if self.customer is not None:
                insert_prescription_request(
                    customer_name=self.customer[1],
                    customer_phone=self.customer[2],
                    medicine_name=name,
                )

                # 2) Send WhatsApp message to support team
                support_number = "918438644780"  
                msg = (
                    "The user requested a medicine that requires a prescription.\n"
                    "Please call or WhatsApp them.\n\n"
                    "User details:\n"
                    f"Name: {self.customer[1]}\n"
                    f"Phone: {self.customer[2]}\n"
                    f"Medicine: {name}"
                )
                try:
                    send_whatsapp_message(
                        to_number=support_number,
                        message=msg,
                        chrome_profile_path=r"C:\\Users\\djeev\\medingen_agent\\selenium_profile",
                        chrome_profile_dir="Default",
                        dry_run=False,  
                    )
                except Exception as e:
                    # Fail 
                    print(f"[WARN] WhatsApp send failed: {e}")

            # 3) Move to prescription_wait state and ask user if they want another medicine
            self.step = "prescription_wait"
            return (
                f"{name} requires a valid prescription.\n"
                "Our Medingen pharmacist will get back to you within 15 mins.\n\n"
                "Do you need any other medicine? (yes/no)"
            )

        # If NO prescription required
        # Stock check
        if stock <= 0:
            substitutes = get_substitutes_by_salt(salt_name)
            if substitutes:
                subs = ", ".join([s[1] for s in substitutes])
                return f"{name} is out of stock.\nAvailable substitutes: {subs}"
            else:
                return "No substitutes available for this medicine."

        # Move to quantity state
        self.step = "ask_quantity"
        # Show ONLY these three details as per your requirement
        return (
            f"Medicine: {name}\n"
            f"Price per strip: ₹{price}\n"
            f"Tablets per strip: {no_of_tablets}\n\n"
            f"How many strips would you like to order?"
        )

    def handle_prescription_wait(self, answer: str):
        """
        State: prescription_wait
        The user already requested an Rx medicine.
        We asked: "Do you need any other medicine? (yes/no)"
        """
        ans = answer.strip().lower()

        if ans in ("yes", "y"):
            self.step = "ask_medicine"
            return "Okay. Please enter the medicine name."

        if ans in ("no", "n"):
            # If cart has NON-Rx items, go to cart confirmation
            if self.cart:
                self.step = "confirm_order"
                return self._build_cart_summary_and_ask_confirm()

            # No cart items 
            self.step = "stop"
            return "Thank you for contacting Medingen. Have a great day!"

        # for unclear answer
        return "Please reply with 'yes' or 'no'."

    def handle_quantity(self, qty):
        """
        State: ask_quantity
        User responded with number of strips for CURRENT non-Rx medicine.
        We add it to cart and ask if they want more medicines.
        """
        try:
            self.quantity = int(str(qty).strip())
            if self.quantity <= 0:
                return "Quantity must be a positive number. Please enter again."
        except ValueError:
            return "Please enter a valid number for strips."

        (
            med_id,
            name,
            salt_name,
            price,
            no_of_tablets,
            stock,
            prescription_required,
            expiry_str,
        ) = self.medicine

        # Basic sanity:
        if self.quantity > stock:
            return f"Only {stock} strips are available for {name}. Please enter a lower quantity."

        total_tablets = self.quantity * no_of_tablets
        days_needed = total_tablets
        today = datetime.now().date()
        expiry_date = datetime.fromisoformat(expiry_str).date()

        # Expiry safety check based on course duration
        if expiry_date < today + timedelta(days=days_needed):
            self.step = "stop"
            return (
                f" Warning: You are ordering {self.quantity} strips ({total_tablets} tablets).\n"
                f"This medicine will expire on {expiry_date}.\n"
                f"But it will take around {days_needed} days to complete this course.\n\n"
                f"Therefore, the medicine will expire **before you can finish taking it**.\n"
                f"Please reduce the quantity or consult your doctor."
            )

        #  Add this item to cart
        line_total = price * self.quantity
        self.cart.append(
            {
                "medicine_id": med_id,
                "name": name,
                "salt_name": salt_name,
                "price": price,
                "no_of_tablets": no_of_tablets,
                "quantity": self.quantity,
                "line_total": line_total,
                "expiry_date": expiry_date.isoformat(),
            }
        )

        subtotal = self._cart_subtotal()
        self._last_total_amount = float(subtotal)  # still without delivery

        # After adding, ask if they need any other medicine
        self.step = "add_more"
        return (
            f"{self.quantity} strips of {name} added to your cart.\n"
            f"Current subtotal (without delivery): ₹{subtotal}.\n\n"
            "Do you need any other medicine? (yes/no)"
        )

    def handle_add_more(self, answer: str):
        """
        State: add_more
        We just added a NON-Rx medicine to cart and asked:
        'Do you need any other medicine? (yes/no)'
        """
        ans = answer.strip().lower()

        if ans in ("yes", "y"):
            self.step = "ask_medicine"
            return "Okay. Please enter the medicine name."

        if ans in ("no", "n"):
            if not self.cart:
                self.step = "stop"
                return "Your cart is empty. Thank you for contacting Medingen."
            # Move to order confirmation
            self.step = "confirm_order"
            return self._build_cart_summary_and_ask_confirm()

        return "Please reply with 'yes' or 'no'."

    def confirm_order(self, answer):
        """
        State: confirm_order
        Used for confirming the WHOLE cart (non-Rx items).
        """
        if answer.strip().lower() != "yes":
            self.step = "stop"
            return "Order cancelled."

        if not self.cart:
            self.step = "stop"
            return "Your cart is empty. Order cancelled."

        self.step = "get_address"
        return "Please enter your delivery address (door no, street, city, state, pincode)."

    def save_address(self, address):
        """
        Save address, compute delivery charge + final total,
        then move to choose_payment.
        """
        self.address = address

        subtotal = self._cart_subtotal()
        delivery_charge = self._get_delivery_charge(address)
        self._delivery_charge = float(delivery_charge)
        grand_total = subtotal + delivery_charge
        self._last_total_amount = float(grand_total)

        self.step = "choose_payment"

        if self._is_tamil_nadu(address):
            return (
                f"Address saved.\n"
                f"Order subtotal: ₹{subtotal}\n"
                f"Delivery charge: ₹{delivery_charge}\n"
                f"Grand total: ₹{grand_total}\n\n"
                "Since you are in Tamil Nadu, COD is available.\n\n"
                "Choose payment method:\n"
                "1. COD\n"
                "2. Online Payment\n\n"
                
                
            )
        else:
            return (
                f"Address saved.\n"
                f"Order subtotal: ₹{subtotal}\n"
                f"Delivery charge: ₹{delivery_charge}\n"
                f"Grand total: ₹{grand_total}\n\n"
                "COD not available for your state.\n"
                "If you still choose COD, our Medingen pharmacist will contact you to confirm your order.\n\n"
                "Choose payment method:\n"
                "1. COD (pharmacist will call you)\n"
                "2. Online Payment"
            )
    def _save_order_items(self,order_id):
        for item in self.cart:
            insert_order_item(
            order_id=order_id,
            medicine_id=item["medicine_id"],
            quantity=item["quantity"],
            price=item["price"],
            line_total=item["line_total"],
            expiry_date=item["expiry_date"],
        )

    def handle_payment(self, method):
        """
        State: choose_payment
        Handles COD / Online, including special COD rule for non-Tamil Nadu.
        """
        method = str(method).strip()

        if not self.cart:
            self.step = "stop"
            return "Your cart is empty. Cannot place order."

        cust_id = self.customer[0]
        total_amount = self._last_total_amount or self._cart_subtotal()
        address = self.address or ""

        # Helper: flatten medicine info for WhatsApp messages
        def _cart_medicine_summary():
            parts = []
            for item in self.cart:
                parts.append(f"{item['name']} x {item['quantity']} strips")
            return "; ".join(parts)

        # COD FLOW
        if method == "1":
            # If NOT Tamil Nadu → send WhatsApp & stop
            if not self._is_tamil_nadu(address):
                first_med = self.cart[0]
                med_id = first_med["medicine_id"]
                total_quantity = sum(item["quantity"] for item in self.cart)
                self.order_id = create_order(
                    cust_id,
                    med_id,
                    total_quantity,
                    total_amount,
                    address,
                )
                self._save_order_items(self.order_id)
                #insert payment_mode
                self.payment_id = insert_payment(self.order_id, "pending")
                self.payment_mode = "COD"
                #update in DB : 
                update_order_payment(self.order_id, "COD", "pending")
                update_order_status(self.order_id, "pending")
                #notify pharmacist
                support_number = "918438644780"
                msg = (
                    "COD request from NON-Tamil Nadu state.\n"
                    "Please call or WhatsApp the customer.\n\n"
                    f"Customer Name: {self.customer[1]}\n"
                    f"Phone: {self.customer[2]}\n"
                    f"Address: {address}\n"
                    f"Medicines: {_cart_medicine_summary()}\n"
                    f"Total Amount (incl. delivery): ₹{total_amount}"
                )
                try:
                    send_whatsapp_message(
                        to_number=support_number,
                        message=msg,
                        chrome_profile_path=r"C:\\Users\\djeev\\medingen_agent\\selenium_profile",
                        chrome_profile_dir="Default",
                        dry_run=False,
                    )
                except Exception as e:
                    print(f"[WARN] COD WhatsApp send failed: {e}")

                self.step = "stop"
                return (
                    "COD is not available for your state.\n"
                    "Our Medingen pharmacist will get back to you within 15 mins."
                )

            # COD allowed (Tamil Nadu)
            first_med = self.cart[0]
            med_id = first_med["medicine_id"]
            total_quantity = sum(item["quantity"] for item in self.cart)

            self.order_id = create_order(
                cust_id,
                med_id,
                total_quantity,
                total_amount,
                address,
            )
            self._save_order_items(self.order_id)
            self.payment_id = insert_payment(self.order_id, "cod_pending")
            self.payment_mode = "COD"
            update_order_payment(self.order_id, "COD", "pending")
            update_order_status(self.order_id, "confirmed")
            self.step = "generate_bill"
            order_msg = "Order placed successfully using COD.\n\n"
            bill_msg = self.generate_bill()
            return order_msg + bill_msg
            

        #  ONLINE PAYMENT (method "2" or anything else)
        first_med = self.cart[0]
        med_id = first_med["medicine_id"]
        total_quantity = sum(item["quantity"] for item in self.cart)

        # 1) Create internal order (status = pending)
        self.order_id = create_order(
            cust_id,
            med_id,
            total_quantity,
            total_amount,
            address,
        )
        self._save_order_items(self.order_id)
        # 2) Insert initiated payment row
        self.payment_id = insert_payment(self.order_id, "initiated")
        self.payment_mode = "Online"

        # 3) Create payment link via payment_gateway
        cust_name = self.customer[1]
        cust_phone = self.customer[2]
        cust_email = self.customer[3]
        link = payment_gateway.create_payment_link(
            total_amount_rupees=total_amount,
            customer_name=cust_name,
            customer_phone=cust_phone,
            customer_email=cust_email,
            internal_order_id=self.order_id,
        )

        self.step = "wait_payment"
        return (
            f"Please complete your payment using the link below:\n{link['short_url']}\n\n"
            "After payment is complete, wait a few seconds and then reply 'payment done'."
        )

    def verify_payment(self):
        """
        State: wait_payment
        Only used for Online payment flow.
        """
        status_row = get_payment_status(self.order_id)
        status = status_row[0] if status_row and isinstance(status_row, tuple) else status_row

        if status is None:
            return "Payment not received yet. Please wait a few seconds and try again."

        if str(status).lower() in ("success", "captured", "paid"):
            update_order_payment(self.order_id, "Online", "success")
            update_order_status(self.order_id, "confirmed")
            self.step = "generate_bill"
            return "Payment verified successfully. Generating your bill..."
        else:
            return f"Payment status: {status}. Kindly retry if failed."

    def generate_bill(self):
        """
        State: generate_bill
        Uses self.cart for multi-item bill.
        """
        order = get_order(self.order_id)
        cust = self.customer

        subtotal = self._cart_subtotal()
        delivery = self._delivery_charge
        total = self._last_total_amount or (subtotal + delivery)
        pdf_path = None
        try:
            pdf_path = generate_invoice_pdf(
                order=order,
                customer=cust,
                cart=self.cart,
                subtotal=subtotal,
                delivery=delivery,
                total=total,
            )
            
        except Exception as e:
            # If PDF fails, continue with text bill
            print(f"[WARN] Failed to generate PDF invoice: {e}")
        # Generate text bill
        self.step = "bill_delivery"
        if pdf_path:
             return f"Your bill has been generated. PDF saved at: {pdf_path}"
        return "Your bill has been generated."
