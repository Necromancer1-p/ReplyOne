import re
import json
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock-ai")

app = FastAPI(title="Mock AI Inference Service")

class InferRequest(BaseModel):
    system_prompt: str
    user_message: str
    max_tokens: int = Field(default=256)
    temperature: float = Field(default=0.7)

class InferResponse(BaseModel):
    intent: str
    confidence: float
    suggested_reply: str

@app.post("/infer", response_model=InferResponse)
def infer(req: InferRequest):
    logger.info(f"Received inference request: {req.user_message}")
    
    msg_lower = req.user_message.lower()
    
    # Simple rule-based intent classification
    if any(k in msg_lower for k in ["complain", "bad", "angry", "worst", "broken", "defect", "hate", "terrible", "delay"]):
        intent = "complaint"
        confidence = 0.98
        reply = "I am very sorry to hear about your experience. Let me connect you to a human agent immediately to get this resolved."
    elif any(k in msg_lower for k in ["order", "status", "track", "delivery", "where is my"]):
        intent = "order_status"
        confidence = 0.92
        reply = "I'd be happy to check your order status. Could you please share your Order ID?"
    elif any(k in msg_lower for k in ["return", "exchange", "refund", "replace"]):
        intent = "return_request"
        confidence = 0.88
        reply = "Sure! You can request a return or exchange within 14 days of delivery. Would you like me to guide you through the process?"
    elif any(k in msg_lower for k in ["price", "how much", "cost", "rate", "inr", "price of"]):
        intent = "price_inquiry"
        confidence = 0.95
        reply = "Let me check the pricing for you. Could you specify which item you are interested in?"
    elif any(k in msg_lower for k in ["avail", "stock", "size", "color", "in stock", "have"]):
        intent = "availability"
        confidence = 0.85
        reply = "I'm checking the stock for that. Which size or color are you looking for?"
    elif any(k in msg_lower for k in ["hi", "hello", "hey", "greetings"]):
        intent = "greeting"
        confidence = 0.99
        reply = "Hello! Welcome to our support. How can I help you today?"
    elif any(k in msg_lower for k in ["thank", "thanks", "nice", "great", "awesome"]):
        intent = "compliment"
        confidence = 0.97
        reply = "You're very welcome! Let me know if there's anything else I can do for you."
    else:
        intent = "general_inquiry"
        confidence = 0.75
        reply = "Thanks for reaching out! Let me check that information for you. Can you tell me more?"

    # Try to parse the business details from system prompt to give a more realistic reply
    # System prompt structure is: static context (KB, hours, name, tone)
    # Let's search for FAQs or products in the system prompt
    try:
        # Check if the message contains a product name that matches something in the system prompt
        # Product entries can be parsed from system prompt
        # (e.g. searching for names of products)
        products = re.findall(r"Product:\s*([^\n,]+)(?:,\s*Price:\s*([^\n]+))?", req.system_prompt)
        for prod_name, price in products:
            if prod_name.strip().lower() in msg_lower:
                if intent == "price_inquiry":
                    reply = f"The price of {prod_name.strip()} is {price.strip()}."
                elif intent == "availability":
                    reply = f"Yes, {prod_name.strip()} is in stock and available for purchase!"
                break
                
        # Also check for FAQs
        faqs = re.findall(r"Q:\s*([^\n?]+)\s*\??\s*A:\s*([^\n]+)", req.system_prompt)
        for q, a in faqs:
            # simple keyword overlap
            q_words = set(re.findall(r"\w+", q.lower()))
            msg_words = set(re.findall(r"\w+", msg_lower))
            overlap = q_words.intersection(msg_words)
            if len(overlap) >= 3 or (len(overlap) / len(q_words) > 0.6 if q_words else False):
                reply = a.strip()
                intent = "faq"
                confidence = 0.96
                break
    except Exception as e:
        logger.error(f"Error parsing system prompt for custom reply: {e}")

    # Simulated AI response delay
    import time
    time.sleep(0.5)

    return InferResponse(
        intent=intent,
        confidence=confidence,
        suggested_reply=reply
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8008, reload=True)
