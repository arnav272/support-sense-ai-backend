from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database setup
def init_db():
    conn = sqlite3.connect('support_tickets.db')
    c = conn.cursor()
    
    # Drop table if exists to recreate with new schema
    c.execute('DROP TABLE IF EXISTS tickets')
    
    c.execute('''
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            source TEXT DEFAULT 'web',
            priority TEXT DEFAULT 'medium',
            category TEXT DEFAULT 'General',
            status TEXT DEFAULT 'new',
            assigned_to TEXT DEFAULT '',
            customer_rating INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample data
    sample_tickets = [
        ("I'm really angry! The app keeps crashing every time I try to login.", "email", "high", "Bug", "new", "", 0),
        ("How do I reset my password? I can't access my account.", "web", "medium", "Access Issue", "new", "", 0),
        ("I love the new update! The dark mode is amazing.", "twitter", "low", "Feedback", "resolved", "", 5),
        ("Need urgent help - payment was deducted but service not activated", "email", "high", "Billing", "in-progress", "Sarah", 0)
    ]
    
    c.executemany('INSERT INTO tickets (text, source, priority, category, status, assigned_to, customer_rating) VALUES (?, ?, ?, ?, ?, ?, ?)', sample_tickets)
    conn.commit()
    conn.close()

# AI analysis (simple keyword-based)
def analyze_ticket(text):
    text_lower = text.lower()
    
    # Priority detection
    if any(word in text_lower for word in ['angry', 'urgent', 'emergency', 'broken', 'not working']):
        priority = 'high'
    elif any(word in text_lower for word in ['help', 'issue', 'problem']):
        priority = 'medium'
    else:
        priority = 'low'
    
    # Category detection
    if any(word in text_lower for word in ['password', 'login', 'access']):
        category = 'Access Issue'
    elif any(word in text_lower for word in ['bug', 'crash', 'broken', 'not working']):
        category = 'Bug'
    elif any(word in text_lower for word in ['refund', 'payment', 'billing']):
        category = 'Billing'
    elif any(word in text_lower for word in ['feature', 'suggestion']):
        category = 'Feature Request'
    else:
        category = 'General'
    
    return {'priority': priority, 'category': category}

# AI Response Suggestions
def generate_ai_response(ticket_text):
    """Generate AI response suggestions based on ticket content"""
    text_lower = ticket_text.lower()
    
    # Simple rule-based AI (for hackathon - can be replaced with real AI API)
    if any(word in text_lower for word in ['crash', 'broken', 'not working']):
        suggestions = [
            "I understand you're experiencing technical issues. Let's troubleshoot this together.",
            "I apologize for the technical difficulties. Our team is looking into this urgently.",
            "Thank you for reporting this issue. Can you tell me what device you're using?"
        ]
    elif any(word in text_lower for word in ['password', 'login', 'access']):
        suggestions = [
            "I can help you reset your password. Please check your email for a reset link.",
            "Let's get you back into your account. I'll send password reset instructions.",
            "For security, I'll help you regain access to your account securely."
        ]
    elif any(word in text_lower for word in ['refund', 'payment', 'billing']):
        suggestions = [
            "I'll check your payment status and help with any billing concerns.",
            "Let me review your account and assist with the payment issue.",
            "I understand your billing concern. Let me look into this for you."
        ]
    else:
        suggestions = [
            "Thank you for reaching out. How can I assist you today?",
            "I'm here to help! Could you provide more details about your concern?",
            "Thanks for contacting support. Let me know how I can help you."
        ]
    
    return random.choice(suggestions)

# API Routes
@app.route('/')
def home():
    return jsonify({'message': 'SupportSense AI API is running! 🚀'})

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy'})

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    conn = sqlite3.connect('support_tickets.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM tickets ORDER BY CASE priority WHEN "high" THEN 1 WHEN "medium" THEN 2 WHEN "low" THEN 3 END, created_at DESC')
    tickets = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(tickets)

@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    data = request.json
    text = data.get('text', '')
    source = data.get('source', 'web')
    
    # Analyze with AI
    analysis = analyze_ticket(text)
    
    conn = sqlite3.connect('support_tickets.db')
    c = conn.cursor()
    c.execute('INSERT INTO tickets (text, source, priority, category) VALUES (?, ?, ?, ?)',
              (text, source, analysis['priority'], analysis['category']))
    ticket_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': ticket_id, **analysis, 'status': 'new'})

@app.route('/api/tickets/<int:ticket_id>', methods=['PATCH'])
def update_ticket(ticket_id):
    data = request.json
    print(f"Updating ticket {ticket_id} with data: {data}")
    
    conn = sqlite3.connect('support_tickets.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    updates = []
    values = []
    
    if 'status' in data:
        updates.append('status = ?')
        values.append(data['status'])
    
    if 'assigned_to' in data:
        updates.append('assigned_to = ?')
        values.append(data['assigned_to'])
    
    if 'customer_rating' in data:
        updates.append('customer_rating = ?')
        values.append(data['customer_rating'])
    
    if updates:
        values.append(ticket_id)
        query = f'UPDATE tickets SET {", ".join(updates)} WHERE id = ?'
        print(f"Executing query: {query} with values: {values}")
        c.execute(query, values)
        conn.commit()
    
    # Verify the update by fetching the updated ticket
    c.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    row = c.fetchone()
    if row:
        updated_ticket = dict(row)
        print(f"Updated ticket: {updated_ticket}")
        conn.close()
        return jsonify({'message': 'Ticket updated successfully', 'ticket': updated_ticket})
    else:
        conn.close()
        return jsonify({'error': 'Ticket not found'}), 404

# New AI API Endpoints
@app.route('/api/ai/suggest-response', methods=['POST'])
def suggest_response():
    data = request.json
    ticket_text = data.get('text', '')
    
    ai_response = generate_ai_response(ticket_text)
    return jsonify({'suggestion': ai_response})

@app.route('/api/ai/analyze-priority', methods=['POST'])
def analyze_priority():
    data = request.json
    ticket_text = data.get('text', '')
    
    # Enhanced priority analysis
    text_lower = ticket_text.lower()
    urgency_words = len([word for word in ['urgent', 'emergency', 'immediately', 'asap'] if word in text_lower])
    anger_words = len([word for word in ['angry', 'furious', 'frustrated', 'disappointed'] if word in text_lower])
    
    if urgency_words > 0 or anger_words > 1:
        priority = 'high'
        reason = 'Contains urgent/anger language'
    elif 'help' in text_lower or 'issue' in text_lower:
        priority = 'medium'
        reason = 'General help request'
    else:
        priority = 'low' 
        reason = 'Standard inquiry'
    
    return jsonify({'priority': priority, 'reason': reason})

# Initialize database
init_db()

if __name__ == '__main__':
    app.run(debug=True, port=8001)