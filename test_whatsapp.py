from whatsapp_sender import send_whatsapp_message

send_whatsapp_message(
    to_number="8438644780",      
    message="Testing WhatsApp message from Selenium profile!",
    chrome_profile_path=r"C:\Users\djeev\medingen_agent\selenium_profile",
    chrome_profile_dir="Default",
    dry_run=False,
    visible=True
)
