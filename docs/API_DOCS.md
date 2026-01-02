API Documentation
Base URLs

Thin Forwarder (User-facing): https://prepsphere-thin-forwarder.onrender.com
Heavy Backend (Internal): http://your-ec2-ip:8000

Endpoints

1. Chat Endpoint
   Thin Forwarder:
   POST /chat
   Heavy Backend:
   POST /chat
   Request
   json{
   "question": "What are the main themes in the novel?"
   }
   Headers:
   Content-Type: application/json
   Authorization: Bearer <FORWARDER_TOKEN> // Only for heavy backend
   Response
   json{
   "answer": "The main themes include...",
   "context": [
   {
   "source": "book_1.txt",
   "excerpt": "..."
   }
   ]
   }
   Status Codes
   CodeMeaning200Success401Missing/invalid token403Invalid token400Invalid request format500Server error

Usage Examples
Using cURL
bashcurl -X POST "https://prepsphere-thin-forwarder.onrender.com/chat" \
 -H "Content-Type: application/json" \
 -d '{"question": "Explain photosynthesis"}'
Using Python
pythonimport requests

url = "https://prepsphere-thin-forwarder.onrender.com/chat"
payload = {"question": "What is AI?"}

response = requests.post(url, json=payload)
print(response.json())
Using JavaScript
javascriptconst url = "https://prepsphere-thin-forwarder.onrender.com/chat";
const payload = { question: "What is machine learning?" };

fetch(url, {
method: "POST",
headers: { "Content-Type": "application/json" },
body: JSON.stringify(payload)
})
.then(res => res.json())
.then(data => console.log(data));

Rate Limiting

No strict rate limits
Render free tier may experience slowdowns
First request takes 2-3s (cold start)
Subsequent requests: 3-5s (including Gemini API)

Authentication
Thin Forwarder → Heavy Backend
Uses bearer token authentication:
Authorization: Bearer <FORWARDER_TOKEN>
Set FORWARDER_TOKEN in both .env files (same value).

Error Handling
Example Error Response
json{
"detail": "Invalid token"
}
Common Errors
ErrorCauseSolution401 UnauthorizedMissing tokenAdd Authorization header403 ForbiddenWrong tokenCheck FORWARDER_TOKEN400 Bad RequestWrong JSON formatCheck request payload500 Server ErrorGemini/Pinecone issueCheck EC2 logs

Best Practices

Always use HTTPS for thin forwarder
Rotate tokens periodically
Monitor response times - if >10s, check EC2 resources
Cache results client-side when possible
Implement retry logic for network resilience
