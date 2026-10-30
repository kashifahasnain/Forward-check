from modules.claim_extractor import extract_claims
import json

sample_message = """
URGENT!

Government is giving FREE LAPTOPS
to all college students under a new scheme!

No registration fee.
Only for college students.
Limited time offer.

Register before midnight today!

Share this message with at least 10 friends
so everyone can benefit.

Don't miss this opportunity!
"""

result = extract_claims(sample_message)

print(json.dumps(result, indent=2, ensure_ascii=False))