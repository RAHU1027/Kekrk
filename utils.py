import time
import random
import requests
import braintree

# Braintree Sandbox Gateway Setup
gateway = braintree.BraintreeGateway(
    braintree.Configuration(
        braintree.Environment.Sandbox,
        merchant_id="21552435",
        public_key="Elevenyts", 
        private_key="5b108bd2fdd31c0c34bc65f24a5216a0"
    )
)

def luhn_checksum(card_number):
    digits = [int(x) for x in card_number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(divmod(d * 2, 10))
    return checksum % 10 == 0

def get_bin_details(card_num):
    clean_bin = str(card_num).strip().replace(" ", "")[:6]
    default_info = {
        "issuer": "N/A",
        "info": "N/A - N/A - N/A",
        "country": "N/A 🏳️",
        "country_flag": "🏳️"
    }
    try:
        response = requests.get(f"https://lookup.binlist.net/{clean_bin}", headers={'Accept-Version': '3'}, timeout=4)
        if response.status_code == 200:
            data = response.json()
            country_code = data.get('country', {}).get('alpha2', '')
            country_name = data.get('country', {}).get('name', 'N/A')
            
            flag = ""
            if country_code:
                flag = "".join(chr(127397 + ord(c)) for c in country_code.upper())
            
            scheme = data.get('scheme', 'N/A').upper()
            card_type = data.get('type', 'N/A').upper()
            brand = data.get('brand', 'N/A').upper()
            
            default_info["issuer"] = data.get('bank', {}).get('name', 'N/A').upper()
            default_info["info"] = f"{scheme} - {card_type} - {brand}"
            default_info["country"] = f"{country_name} {flag}".strip()
            default_info["country_flag"] = flag if flag else "🏳️"
    except Exception:
        pass
    return default_info

def generate_cards_logic(bin_number, amount=10):
    bin_str = str(bin_number).strip().replace(" ", "")
    # Agar numeric characters ke alawa 'x' ya 'X' daala ho toh replace karein
    bin_str = bin_str.lower().replace("x", "")
    
    generated_cards = []
    for _ in range(amount):
        card = bin_str
        while len(card) < 15:
            card += str(random.randint(0, 9))
        for i in range(10):
            test_card = card + str(i)
            if luhn_checksum(test_card):
                generated_cards.append(test_card)
                break
    return generated_cards

def check_card_with_braintree(card_num, month, year, cvv):
    try:
        result = gateway.transaction.sale({
            "amount": "1.00",
            "credit_card": {
                "number": card_num,
                "expiration_month": month,
                "expiration_year": year,
                "cvv": cvv
            },
            "options": {"submit_for_settlement": False}
        })
        if result.is_success:
            return "APPROVED ✅", "Status: CHARGED SUCCESS"
        elif result.transaction:
            return "DECLINED ❌", f"{result.transaction.processor_response_text}"
        else:
            return "DECLINED ❌", f"{result.message}"
    except Exception as e:
        if "public_key" in str(e).lower() or "public" in str(e).lower():
            return "DECLINED ❌", "Invalid API Key provided: Public"
        return "ERROR ⚠️", "Gateway Error"
