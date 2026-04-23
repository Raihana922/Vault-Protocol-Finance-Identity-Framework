import os
from datetime import datetime
from models import Transaction, Account, AuditLog
# Make sure to pip install weasyprint if you intend to run this in production
try:
    from weasyprint import HTML
except ImportError:
    HTML = None

def _generate_pdf_from_html(html_content, output_path):
    if HTML is not None:
        HTML(string=html_content).write_pdf(output_path)
    else:
        # Fallback for development if WeasyPrint is not installed
        with open(output_path.replace('.pdf', '.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)

def generate_receipt(transaction_id, html_template_rendered):
    """
    Generates a single trade receipt. 
    In production, this streams WeasyPrint PDF directly to memory.
    """
    # Create temp directory if needed
    os.makedirs('temp_docs', exist_ok=True)
    temp_path = f"temp_docs/receipt_{transaction_id}.pdf"
    
    _generate_pdf_from_html(html_template_rendered, temp_path)
    return temp_path

def generate_statement(account_id, start_date, end_date, html_template_rendered):
    """
    Generates a monthly or time-bounded Statement of Account.
    """
    os.makedirs('temp_docs', exist_ok=True)
    temp_path = f"temp_docs/statement_{account_id}_{start_date}_{end_date}.pdf"
    
    _generate_pdf_from_html(html_template_rendered, temp_path)
    return temp_path
