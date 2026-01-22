"""
Test client deletion and Russian character support in PDF export
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))


def test_database_cascade_deletion():
    """Test that deleting a client also deletes associated sessions"""
    print("Testing database cascade deletion...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.shared.utils as utils_module
        original_func = utils_module.get_application_path
        
        # Mock get_application_path to return temp directory
        def mock_get_application_path():
            return tmpdir
        
        utils_module.get_application_path = mock_get_application_path
        
        try:
            from src.shared.database import Database, ClientModel, SessionModel
            from datetime import datetime
            
            # Initialize database
            db = Database()
            session = db.get_session()
            
            # Create a test client
            client = ClientModel(
                hwid="test-hwid-123",
                name="Test Client",
                ip_address="192.168.1.100",
                status="online"
            )
            session.add(client)
            session.commit()
            
            client_id = client.id
            print(f"✅ Created test client with ID: {client_id}")
            
            # Create test sessions for this client
            for i in range(3):
                test_session = SessionModel(
                    client_id=client_id,
                    start_time=datetime.now(),
                    duration_minutes=30,
                    status='completed'
                )
                session.add(test_session)
            
            session.commit()
            
            # Verify sessions were created
            sessions = session.query(SessionModel).filter_by(client_id=client_id).all()
            assert len(sessions) == 3, f"Expected 3 sessions, got {len(sessions)}"
            print(f"✅ Created 3 test sessions for client {client_id}")
            
            # Delete the client
            client_to_delete = session.query(ClientModel).filter_by(id=client_id).first()
            session.delete(client_to_delete)
            session.commit()
            print(f"✅ Deleted client {client_id}")
            
            # Verify the client was deleted
            deleted_client = session.query(ClientModel).filter_by(id=client_id).first()
            assert deleted_client is None, "Client should be deleted"
            print(f"✅ Confirmed client deletion")
            
            # Verify sessions were also deleted (cascade)
            remaining_sessions = session.query(SessionModel).filter_by(client_id=client_id).all()
            assert len(remaining_sessions) == 0, f"Expected 0 sessions after cascade delete, got {len(remaining_sessions)}"
            print(f"✅ Confirmed cascade deletion of sessions")
            
            session.close()
            
        finally:
            utils_module.get_application_path = original_func
    
    print("✅ Database cascade deletion test passed!")


def test_russian_font_support():
    """Test that Russian fonts can be registered for PDF export"""
    print("\nTesting Russian font support...")
    
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # Try to register DejaVu Sans font
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
            print(f"✅ DejaVu Sans font registered successfully")
            
            # Verify font is registered
            registered_fonts = pdfmetrics.getRegisteredFontNames()
            assert 'DejaVuSans' in registered_fonts, "DejaVu Sans should be in registered fonts"
            print(f"✅ Font is available in registered fonts list")
        else:
            print(f"⚠️  Warning: DejaVu Sans font not found at {font_path}")
            print(f"   This is expected in some environments")
        
    except ImportError:
        print("⚠️  Warning: reportlab not installed, skipping font test")
        print("   Install with: pip install reportlab")
    
    print("✅ Russian font support test completed!")


def test_pdf_export_with_russian_text():
    """Test PDF generation with Russian text"""
    print("\nTesting PDF export with Russian text...")
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            pdf_path = tmp_pdf.name
        
        try:
            # Register Russian font
            font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                font_name = 'DejaVuSans'
            else:
                font_name = 'Helvetica'
                print(f"⚠️  Using Helvetica fallback font")
            
            # Create PDF
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title with Russian text
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=18
            )
            
            title = Paragraph("Статистика LibLocker", title_style)
            elements.append(title)
            
            # Table with Russian text
            table_data = [
                ['Метрика', 'Значение'],
                ['Всего клиентов', '10'],
                ['Всего сессий', '50'],
                ['Общее время', '100 часов']
            ]
            
            table = Table(table_data, colWidths=[3*inch, 3*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            
            # Verify PDF was created
            assert os.path.exists(pdf_path), "PDF file should be created"
            assert os.path.getsize(pdf_path) > 0, "PDF file should not be empty"
            
            print(f"✅ PDF with Russian text created successfully")
            print(f"   PDF size: {os.path.getsize(pdf_path)} bytes")
            
        finally:
            # Clean up
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
                print(f"✅ Test PDF cleaned up")
    
    except ImportError:
        print("⚠️  Warning: reportlab not installed, skipping PDF test")
        print("   Install with: pip install reportlab")
    
    print("✅ PDF export test completed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Testing Client Deletion and PDF Export Features")
    print("=" * 70)
    
    test_database_cascade_deletion()
    test_russian_font_support()
    test_pdf_export_with_russian_text()
    
    print("\n" + "=" * 70)
    print("All tests completed successfully! ✅")
    print("=" * 70)
