from crewai.tools import tool
from billing_engine import BillingEngine

# Single persistent engine instance
engine = BillingEngine()


@tool("BillingTool")
def billing_tool(user_input: str) -> str:
    """
    Routes the user input into the correct BillingEngine step.
    Handles:
    - greet
    - collect_customer
    - ask_medicine
    - prescription_wait
    - ask_quantity
    - add_more
    - confirm_order
    - get_address
    - choose_payment
    - wait_payment
    - generate_bill
    """
    step = engine.step.lower().strip()

    try:
        #  GREET
        if step == "greet":
            return engine.greet_user()

        #  COLLECT CUSTOMER DETAILS
        elif step == "collect_customer":
            raw = user_input.strip()
            cleaned = raw.replace("{", "").replace("}", "")

            # Split by comma OR space
            if "," in cleaned:
                parts = [p.strip() for p in cleaned.split(",")]
            else:
                parts = cleaned.split()

            if len(parts) < 2:
                return "Please enter your name and phone number."

            name = parts[0].strip().title()
            phone_raw = parts[1].strip()
            phone = "".join(c for c in phone_raw if c.isdigit())

            email = parts[2].strip() if len(parts) >= 3 else ""

            if len(phone) != 10:
                return "Phone number must be 10 digits. Try again."

            return engine.save_customer(name, phone, email)

        #  ASK MEDICINE NAME
        elif step == "ask_medicine":
            return engine.lookup_medicine(user_input)

        # PRESCRIPTION WAIT (yes/no)
        elif step == "prescription_wait":
            return engine.handle_prescription_wait(user_input)

        #  ASK QUANTITY for non-Rx medicine
        elif step == "ask_quantity":
             return engine.handle_quantity(user_input)

        #  ADD MORE MEDICINES? (yes/no)
        elif step == "add_more":
            return engine.handle_add_more(user_input)

        #  CONFIRM CART SUMMARY
        elif step == "confirm_order":
            return engine.confirm_order(user_input)

        #  COLLECT ADDRESS
        elif step == "get_address":
            return engine.save_address(user_input)

        #  PAYMENT METHOD (COD / Online)
        elif step == "choose_payment":
            raw = user_input.strip().lower()

            # 🔹 Normalize COD inputs
            if raw in ("1", "cod", "cash on delivery", "cash", "cod payment"):
                return engine.handle_payment("1")

            # 🔹 Normalize Online payment inputs
            if raw in ("2", "online", "online payment", "upi", "card"):
                return engine.handle_payment("2")

            # Anything else → ask again
            return (
                "Invalid choice.\n"
                "Please type:\n"
                "1 for COD\n"
                "2 for Online Payment"
            )

        #  ONLINE PAYMENT – waiting for "payment done"
        elif step == "wait_payment":
            return engine.verify_payment()

        # BILL GENERATION
        elif step == "generate_bill":
            return engine.generate_bill()
        
        elif step == "bill_delivery":
            return "Your bill has been generated. If you want to start a new order, type 'hi'."


        # STOP OR UNKNOWN STEP
        else:
            return "Workflow ended. If you want to start again, type 'hi'."

    except Exception as e:
        return f"Error: {str(e)}"
